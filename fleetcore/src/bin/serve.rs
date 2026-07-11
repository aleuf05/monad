// FleetCore live server: wraps the deterministic World/Command engine (see
// ../world.rs, ../command.rs) in a real-time process. Browsers connect over
// WebSocket at /ws, receive a snapshot on connect plus a fresh snapshot after
// every tick or applied command, and can push Commands back over the same
// socket using the existing tagged Command JSON shape (e.g.
// {"type":"pause-clock"}). GET /snapshot exposes the same data as plain JSON
// for curl/debugging without opening a socket.
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::http::header::ACCESS_CONTROL_ALLOW_ORIGIN;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::{Json, Router};
use fleetcore::command::Command;
use fleetcore::persistence::{
    append_event, ensure_dirs, load_seed, load_world, save_checkpoint, save_world, write_snapshot,
    StorePaths,
};
use fleetcore::snapshot::{snapshot, WorldSnapshot};
use fleetcore::world::World;
use futures_util::{SinkExt, StreamExt};
use serde::Serialize;
use std::env;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{broadcast, Mutex};

const DEFAULT_STATE_DIR: &str = "data/fleetcore";
const DEFAULT_SEED_PATH: &str = "fleetcore/data/seed-world.json";
const DEFAULT_PORT: u16 = 4771;
const DEFAULT_TICK_MS: u64 = 1000;
const CHECKPOINT_EVERY_TICKS: u64 = 60;
// Loopback-only by default: this server has no authentication, so anyone who
// can open the WebSocket can issue commands (including pausing the world for
// every connected client). Binding 0.0.0.0 would make that reachable from
// outside the host the moment any firewall/NAT in front of it allows the
// port through. The intended public path is a same-host reverse proxy (e.g.
// Caddy) terminating TLS and forwarding to this loopback address -- use
// --bind-all only once that's actually in place and the exposure is a
// deliberate, reviewed decision, not a default.
const DEFAULT_BIND_HOST: &str = "127.0.0.1";

#[derive(Clone)]
struct AppState {
    world: Arc<Mutex<World>>,
    paths: Arc<StorePaths>,
    tx: broadcast::Sender<String>,
}

#[derive(Serialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
enum ServerMessage<'a> {
    Snapshot { snapshot: &'a WorldSnapshot },
    Error { message: String },
}

#[tokio::main]
async fn main() {
    if let Err(error) = run().await {
        eprintln!("fleetcore-serve: {error}");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), String> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    let state_dir =
        take_option(&mut args, "--state-dir").unwrap_or_else(|| DEFAULT_STATE_DIR.to_string());
    let seed_path =
        take_option(&mut args, "--seed").unwrap_or_else(|| DEFAULT_SEED_PATH.to_string());
    let port: u16 = match take_option(&mut args, "--port") {
        Some(value) => value.parse().map_err(|_| "invalid --port".to_string())?,
        None => DEFAULT_PORT,
    };
    let tick_ms: u64 = match take_option(&mut args, "--tick-ms") {
        Some(value) => value.parse().map_err(|_| "invalid --tick-ms".to_string())?,
        None => DEFAULT_TICK_MS,
    };
    let bind_all = take_flag(&mut args, "--bind-all");
    let bind_host = if bind_all {
        "0.0.0.0"
    } else {
        DEFAULT_BIND_HOST
    };

    let paths = StorePaths::new(state_dir, seed_path);
    ensure_dirs(&paths)?;
    let world = match load_world(&paths) {
        Ok(world) => world,
        Err(_) => {
            let seed = load_seed(&paths)?;
            save_world(&paths, &seed)?;
            save_checkpoint(&paths, &seed)?;
            seed
        }
    };
    write_snapshot(&paths, &world, None)?;

    let (tx, _rx) = broadcast::channel::<String>(64);
    let state = AppState {
        world: Arc::new(Mutex::new(world)),
        paths: Arc::new(paths),
        tx,
    };

    spawn_tick_loop(state.clone(), tick_ms);

    let app = Router::new()
        .route("/snapshot", get(get_snapshot))
        .route("/ws", get(ws_handler))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind((bind_host, port))
        .await
        .map_err(|err| format!("failed to bind {bind_host}:{port}: {err}"))?;
    println!(
        "fleetcore live server listening: ws://{bind_host}:{port}/ws  http://{bind_host}:{port}/snapshot"
    );
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .map_err(|err| err.to_string())
}

async fn shutdown_signal() {
    let _ = tokio::signal::ctrl_c().await;
    println!("fleetcore-serve: shutting down");
}

fn spawn_tick_loop(state: AppState, tick_ms: u64) {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_millis(tick_ms));
        let mut ticks_since_checkpoint: u64 = 0;
        loop {
            interval.tick().await;
            let mut world = state.world.lock().await;
            if !world.clock.is_running() {
                continue;
            }
            match world.apply_command(Command::Step { ticks: 1 }) {
                Ok(event) => {
                    if let Err(err) = append_event(&state.paths, &event) {
                        eprintln!("fleetcore-serve: failed to append tick event: {err}");
                    }
                    if let Err(err) = save_world(&state.paths, &world) {
                        eprintln!("fleetcore-serve: failed to save world: {err}");
                    }
                    ticks_since_checkpoint += 1;
                    if ticks_since_checkpoint >= CHECKPOINT_EVERY_TICKS {
                        ticks_since_checkpoint = 0;
                        let _ = save_checkpoint(&state.paths, &world);
                        let _ = write_snapshot(&state.paths, &world, None);
                    }
                    broadcast_snapshot(&state, &world);
                }
                Err(err) => eprintln!("fleetcore-serve: tick failed: {err}"),
            }
        }
    });
}

async fn get_snapshot(State(state): State<AppState>) -> impl IntoResponse {
    let world = state.world.lock().await;
    let snap = snapshot(&world);
    ([(ACCESS_CONTROL_ALLOW_ORIGIN, "*")], Json(snap))
}

async fn ws_handler(ws: WebSocketUpgrade, State(state): State<AppState>) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: AppState) {
    let (mut sender, mut receiver) = socket.split();
    let mut rx = state.tx.subscribe();

    {
        let world = state.world.lock().await;
        let snap = snapshot(&world);
        if let Ok(json) = serde_json::to_string(&ServerMessage::Snapshot { snapshot: &snap }) {
            let _ = sender.send(Message::Text(json)).await;
        }
    }

    let mut send_task = tokio::spawn(async move {
        while let Ok(json) = rx.recv().await {
            if sender.send(Message::Text(json)).await.is_err() {
                break;
            }
        }
    });

    let recv_state = state.clone();
    let mut recv_task = tokio::spawn(async move {
        while let Some(Ok(message)) = receiver.next().await {
            if let Message::Text(text) = message {
                handle_client_message(&recv_state, &text).await;
            }
        }
    });

    tokio::select! {
        _ = &mut send_task => recv_task.abort(),
        _ = &mut recv_task => send_task.abort(),
    }
}

async fn handle_client_message(state: &AppState, text: &str) {
    let command: Command = match serde_json::from_str(text) {
        Ok(command) => command,
        Err(err) => {
            eprintln!("fleetcore-serve: invalid command from client: {err}");
            send_error(state, format!("invalid command: {err}"));
            return;
        }
    };
    let mut world = state.world.lock().await;
    match world.apply_command(command) {
        Ok(event) => {
            if let Err(err) = append_event(&state.paths, &event) {
                eprintln!("fleetcore-serve: failed to append event: {err}");
            }
            if let Err(err) = save_world(&state.paths, &world) {
                eprintln!("fleetcore-serve: failed to save world: {err}");
            }
            broadcast_snapshot(state, &world);
        }
        Err(err) => {
            eprintln!("fleetcore-serve: command rejected: {err}");
            send_error(state, err);
        }
    }
}

fn send_error(state: &AppState, message: String) {
    if let Ok(json) = serde_json::to_string(&ServerMessage::Error { message }) {
        let _ = state.tx.send(json);
    }
}

fn broadcast_snapshot(state: &AppState, world: &World) {
    let snap = snapshot(world);
    if let Ok(json) = serde_json::to_string(&ServerMessage::Snapshot { snapshot: &snap }) {
        let _ = state.tx.send(json);
    }
}

fn take_option(args: &mut Vec<String>, name: &str) -> Option<String> {
    if let Some(index) = args.iter().position(|arg| arg == name) {
        args.remove(index);
        if index < args.len() {
            Some(args.remove(index))
        } else {
            None
        }
    } else {
        None
    }
}

fn take_flag(args: &mut Vec<String>, name: &str) -> bool {
    if let Some(index) = args.iter().position(|arg| arg == name) {
        args.remove(index);
        true
    } else {
        false
    }
}
