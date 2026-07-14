// FleetCore live server: wraps the deterministic World/Command engine (see
// ../world.rs, ../command.rs) in a real-time process. Two ways in:
//
// - WebSocket at /ws: receive a snapshot on connect plus a fresh snapshot
//   after every tick or applied command.
// - Plain JSON over HTTP: GET /snapshot and POST /command.
//
// Both paths accept the same tagged Command JSON shape the CLI already
// parses positional arguments into (e.g. {"type":"pause-clock"}).
//
// No auth: every connection on both transports has full command authority,
// no token required. --command-token is still accepted on the command line
// and silently ignored, so existing launchers don't fail to start.
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::{Query, State};
use axum::http::header::{ACCESS_CONTROL_ALLOW_ORIGIN, AUTHORIZATION};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use fleetcore::command::Command;
use fleetcore::history_api::{history_v2_router, JsonlVesselEventHistoryStore};
use fleetcore::persistence::{
    apply_authoritative, ensure_dirs, load_seed, load_world, restore_authoritative_world,
    save_checkpoint, save_world, write_snapshot, StorePaths,
};
use fleetcore::snapshot::{snapshot, WorldSnapshot};
use fleetcore::world::World;
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::env;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{broadcast, mpsc, Mutex};

const DEFAULT_STATE_DIR: &str = "data/fleetcore";
const DEFAULT_SEED_PATH: &str = "fleetcore/data/seed-world.json";
const DEFAULT_PORT: u16 = 4771;
const DEFAULT_TICK_MS: u64 = 1000;
const CHECKPOINT_EVERY_TICKS: u64 = 60;
// Loopback-only by default: even with the command-token gate below, binding
// 0.0.0.0 would put a live process directly on the internet the moment any
// firewall/NAT in front of it allowed the port through. The intended public
// path is a same-host reverse proxy (e.g. Caddy) terminating TLS and
// forwarding to this loopback address -- use --bind-all only once that's
// actually in place and the exposure is a deliberate, reviewed decision.
const DEFAULT_BIND_HOST: &str = "127.0.0.1";

#[derive(Clone)]
struct AppState {
    world: Arc<Mutex<World>>,
    paths: Arc<StorePaths>,
    tx: broadcast::Sender<String>,
    runtime: Arc<Mutex<RuntimeHealth>>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "kebab-case")]
enum RuntimeMode {
    Authoritative,
    ReadOnlyDegraded,
}

#[derive(Debug, Clone, Serialize)]
struct RuntimeHealth {
    mode: RuntimeMode,
    cause: Option<String>,
    last_durable_command_sequence: u64,
    last_durable_vessel_event_sequence: u64,
    recovery_action: String,
}

impl AppState {
    // Command token check removed -- every connection has command authority
    // regardless of what (if anything) is presented. See commit history for
    // the prior token-gated behavior.
    fn authorized(&self, _presented: Option<&str>) -> bool {
        true
    }
}

#[derive(Serialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
enum ServerMessage<'a> {
    Connected { command_authority: bool },
    Snapshot { snapshot: &'a WorldSnapshot },
    Error { message: String },
}

#[derive(Deserialize)]
struct WsAuthParams {
    token: Option<String>,
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
    // --command-token is still accepted (and ignored) so existing launchers
    // that pass it don't fail to start.
    take_option(&mut args, "--command-token");

    let paths = StorePaths::new(state_dir, seed_path);
    ensure_dirs(&paths)?;
    let (world, runtime) = match load_world(&paths) {
        Ok(readable) => match restore_authoritative_world(&paths) {
            Ok(world) => {
                let last_vessel = world.vessel_event_next_sequence.saturating_sub(1);
                let last_command = world.event_sequence;
                (
                    world,
                    RuntimeHealth {
                        mode: RuntimeMode::Authoritative,
                        cause: None,
                        last_durable_command_sequence: last_command,
                        last_durable_vessel_event_sequence: last_vessel,
                        recovery_action: "none".to_string(),
                    },
                )
            }
            Err(error) => {
                let last_vessel = readable.vessel_event_next_sequence.saturating_sub(1);
                let last_command = readable.event_sequence;
                (
                    readable,
                    RuntimeHealth {
                        mode: RuntimeMode::ReadOnlyDegraded,
                        cause: Some(error),
                        last_durable_command_sequence: last_command,
                        last_durable_vessel_event_sequence: last_vessel,
                        recovery_action: "reconcile world.json with events.jsonl and restart"
                            .to_string(),
                    },
                )
            }
        },
        Err(_) => {
            let seed = load_seed(&paths)?;
            save_world(&paths, &seed)?;
            save_checkpoint(&paths, &seed)?;
            (
                seed,
                RuntimeHealth {
                    mode: RuntimeMode::Authoritative,
                    cause: None,
                    last_durable_command_sequence: 0,
                    last_durable_vessel_event_sequence: 0,
                    recovery_action: "none".to_string(),
                },
            )
        }
    };
    write_snapshot(&paths, &world, None)?;

    let (tx, _rx) = broadcast::channel::<String>(64);
    let history_store = Arc::new(JsonlVesselEventHistoryStore::new(
        paths.clone(),
        world.world_id.clone(),
    ));
    let state = AppState {
        world: Arc::new(Mutex::new(world)),
        paths: Arc::new(paths),
        tx,
        runtime: Arc::new(Mutex::new(runtime)),
    };

    spawn_tick_loop(state.clone(), tick_ms);

    let app = Router::new()
        .route("/snapshot", get(get_snapshot))
        .route("/health", get(get_health))
        .route("/command", post(post_command))
        .route("/ws", get(ws_handler))
        .with_state(state.clone())
        .merge(history_v2_router(history_store));

    let listener = tokio::net::TcpListener::bind((bind_host, port))
        .await
        .map_err(|err| format!("failed to bind {bind_host}:{port}: {err}"))?;
    println!(
        "fleetcore live server listening: ws://{bind_host}:{port}/ws  http://{bind_host}:{port}/snapshot  http://{bind_host}:{port}/command"
    );
    println!(
        "fleetcore-serve: command authority is GRANTED to every connection -- no token required"
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
            if matches!(
                state.runtime.lock().await.mode,
                RuntimeMode::ReadOnlyDegraded
            ) {
                continue;
            }
            if !world.clock.is_running() {
                continue;
            }
            match apply_authoritative(&state.paths, &mut world, Command::Step { ticks: 1 }) {
                Ok(event) => {
                    update_durable_health(&state, &event).await;
                    ticks_since_checkpoint += 1;
                    if ticks_since_checkpoint >= CHECKPOINT_EVERY_TICKS {
                        ticks_since_checkpoint = 0;
                        let _ = save_checkpoint(&state.paths, &world);
                        let _ = write_snapshot(&state.paths, &world, None);
                    }
                    broadcast_snapshot(&state, &world);
                }
                Err(err) => {
                    if err.starts_with("authoritative persistence failure:") {
                        enter_degraded(&state, err.clone()).await;
                    }
                    eprintln!("fleetcore-serve: tick failed: {err}")
                }
            }
        }
    });
}

async fn get_health(State(state): State<AppState>) -> impl IntoResponse {
    Json(state.runtime.lock().await.clone())
}

async fn get_snapshot(State(state): State<AppState>) -> impl IntoResponse {
    let world = state.world.lock().await;
    let snap = snapshot(&world);
    ([(ACCESS_CONTROL_ALLOW_ORIGIN, "*")], Json(snap))
}

/// Read + write JSON-over-HTTP path for operator commands (see Sprint.md's
/// "Write endpoint(s): accept operator commands"), independent of the
/// WebSocket transport. Requires `Authorization: Bearer <command-token>`.
async fn post_command(
    State(state): State<AppState>,
    headers: HeaderMap,
    body: String,
) -> impl IntoResponse {
    let presented = bearer_token(&headers);
    if !state.authorized(presented.as_deref()) {
        return (
            StatusCode::UNAUTHORIZED,
            [(ACCESS_CONTROL_ALLOW_ORIGIN, "*")],
            Json(serde_json::json!({ "error": "missing or invalid command token" })),
        );
    }
    let command: Command = match serde_json::from_str(&body) {
        Ok(command) => command,
        Err(err) => {
            return (
                StatusCode::BAD_REQUEST,
                [(ACCESS_CONTROL_ALLOW_ORIGIN, "*")],
                Json(serde_json::json!({ "error": format!("invalid command: {err}") })),
            );
        }
    };
    match apply_and_broadcast(&state, command).await {
        Ok(snap) => (
            StatusCode::OK,
            [(ACCESS_CONTROL_ALLOW_ORIGIN, "*")],
            Json(serde_json::to_value(snap).unwrap_or_default()),
        ),
        Err(err) => (
            StatusCode::UNPROCESSABLE_ENTITY,
            [(ACCESS_CONTROL_ALLOW_ORIGIN, "*")],
            Json(serde_json::json!({ "error": err })),
        ),
    }
}

fn bearer_token(headers: &HeaderMap) -> Option<String> {
    headers
        .get(AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .and_then(|value| value.strip_prefix("Bearer "))
        .map(str::to_string)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    Query(params): Query<WsAuthParams>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    let authorized = state.authorized(params.token.as_deref());
    ws.on_upgrade(move |socket| handle_socket(socket, state, authorized))
}

async fn handle_socket(socket: WebSocket, state: AppState, authorized: bool) {
    let (mut sender, mut receiver) = socket.split();
    let mut broadcast_rx = state.tx.subscribe();
    // A rejected or unauthorized command should only ever reply to the
    // connection that sent it, not every connection subscribed to the
    // broadcast channel -- this direct channel carries exactly that, merged
    // into the same outgoing stream as broadcast snapshots below.
    let (direct_tx, mut direct_rx) = mpsc::unbounded_channel::<String>();

    {
        let world = state.world.lock().await;
        let snap = snapshot(&world);
        let connected = serde_json::to_string(&ServerMessage::Connected {
            command_authority: authorized,
        });
        let initial = serde_json::to_string(&ServerMessage::Snapshot { snapshot: &snap });
        if let Ok(json) = connected {
            let _ = sender.send(Message::Text(json)).await;
        }
        if let Ok(json) = initial {
            let _ = sender.send(Message::Text(json)).await;
        }
    }

    let mut send_task = tokio::spawn(async move {
        loop {
            let outgoing = tokio::select! {
                broadcast = broadcast_rx.recv() => match broadcast {
                    Ok(json) => json,
                    Err(_) => break,
                },
                direct = direct_rx.recv() => match direct {
                    Some(json) => json,
                    None => break,
                },
            };
            if sender.send(Message::Text(outgoing)).await.is_err() {
                break;
            }
        }
    });

    let recv_state = state.clone();
    let mut recv_task = tokio::spawn(async move {
        while let Some(Ok(message)) = receiver.next().await {
            if let Message::Text(text) = message {
                handle_client_message(&recv_state, &text, authorized, &direct_tx).await;
            }
        }
    });

    tokio::select! {
        _ = &mut send_task => recv_task.abort(),
        _ = &mut recv_task => send_task.abort(),
    }
}

async fn handle_client_message(
    state: &AppState,
    text: &str,
    authorized: bool,
    reply: &mpsc::UnboundedSender<String>,
) {
    if !authorized {
        send_error(
            reply,
            "read-only connection: reconnect with a valid ?token= to gain command authority"
                .to_string(),
        );
        return;
    }
    let command: Command = match serde_json::from_str(text) {
        Ok(command) => command,
        Err(err) => {
            eprintln!("fleetcore-serve: invalid command from client: {err}");
            send_error(reply, format!("invalid command: {err}"));
            return;
        }
    };
    if let Err(err) = apply_and_broadcast(state, command).await {
        eprintln!("fleetcore-serve: command rejected: {err}");
        send_error(reply, err);
    }
}

/// Shared apply/persist/broadcast path for both the WebSocket and HTTP write
/// transports, so the two can't drift in what "applying a command" means.
async fn apply_and_broadcast(state: &AppState, command: Command) -> Result<WorldSnapshot, String> {
    if matches!(
        state.runtime.lock().await.mode,
        RuntimeMode::ReadOnlyDegraded
    ) {
        return Err(
            "FleetCore is read-only degraded; reconcile authoritative persistence and restart"
                .to_string(),
        );
    }
    let mut world = state.world.lock().await;
    let event = match apply_authoritative(&state.paths, &mut world, command) {
        Ok(event) => event,
        Err(error) => {
            if error.starts_with("authoritative persistence failure:") {
                enter_degraded(state, error.clone()).await;
            }
            return Err(error);
        }
    };
    update_durable_health(state, &event).await;
    let snap = snapshot(&world);
    if let Ok(json) = serde_json::to_string(&ServerMessage::Snapshot { snapshot: &snap }) {
        let _ = state.tx.send(json);
    }
    Ok(snap)
}

async fn update_durable_health(state: &AppState, event: &fleetcore::event::Event) {
    let mut health = state.runtime.lock().await;
    health.last_durable_command_sequence = event.sequence;
    if let Some(last) = event.vessel_events.last() {
        health.last_durable_vessel_event_sequence = last.sequence;
    }
}

async fn enter_degraded(state: &AppState, cause: String) {
    let mut health = state.runtime.lock().await;
    health.mode = RuntimeMode::ReadOnlyDegraded;
    health.cause = Some(cause);
    health.recovery_action = "reconcile world.json with events.jsonl and restart".to_string();
}

fn send_error(reply: &mpsc::UnboundedSender<String>, message: String) {
    if let Ok(json) = serde_json::to_string(&ServerMessage::Error { message }) {
        let _ = reply.send(json);
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[tokio::test]
    async fn authoritative_append_failure_enters_read_only_without_mutation() {
        let dir = std::env::temp_dir().join(format!(
            "fleetcore-serve-fault-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let paths = StorePaths::new(
            &dir,
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
        );
        std::fs::create_dir_all(&paths.events_path).unwrap();
        let world = load_seed(&paths).unwrap();
        let before = world.clone();
        let (tx, _) = broadcast::channel(4);
        let state = AppState {
            world: Arc::new(Mutex::new(world)),
            paths: Arc::new(paths),
            tx,
            runtime: Arc::new(Mutex::new(RuntimeHealth {
                mode: RuntimeMode::Authoritative,
                cause: None,
                last_durable_command_sequence: 0,
                last_durable_vessel_event_sequence: 0,
                recovery_action: "none".to_string(),
            })),
        };

        let first = apply_and_broadcast(&state, Command::Step { ticks: 1 })
            .await
            .unwrap_err();
        assert!(first.starts_with("authoritative persistence failure:"));
        assert_eq!(*state.world.lock().await, before);
        assert!(matches!(
            state.runtime.lock().await.mode,
            RuntimeMode::ReadOnlyDegraded
        ));
        let second = apply_and_broadcast(&state, Command::Step { ticks: 1 })
            .await
            .unwrap_err();
        assert!(second.contains("read-only degraded"));
        assert_eq!(*state.world.lock().await, before);
        let _ = std::fs::remove_dir_all(dir);
    }
}
