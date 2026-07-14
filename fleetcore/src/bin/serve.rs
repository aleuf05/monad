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
// Mutation is default-deny. HTTP and WebSocket share bearer-token
// authentication, then apply a distinct command authorization check.
use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::http::header::{ACCESS_CONTROL_ALLOW_ORIGIN, AUTHORIZATION, COOKIE, ORIGIN, SET_COOKIE};
use axum::http::{HeaderMap, StatusCode};
use axum::response::IntoResponse;
use axum::routing::{get, post};
use axum::{Json, Router};
use fleetcore::command::Command;
use fleetcore::persistence::{
    append_event, ensure_dirs, load_seed, load_world, save_checkpoint, save_world, write_snapshot,
    StorePaths,
};
use fleetcore::snapshot::{snapshot, WorldSnapshot};
use fleetcore::world::World;
use futures_util::{SinkExt, StreamExt};
use rand::{rngs::OsRng, RngCore};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::env;
use std::sync::Arc;
use std::time::{Duration, Instant};
use subtle::ConstantTimeEq;
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
const SESSION_COOKIE: &str = "__Host-fleetcore_session";
const SESSION_TTL_SECONDS: u64 = 300;

#[derive(Clone)]
struct AppState {
    world: Arc<Mutex<World>>,
    paths: Arc<StorePaths>,
    tx: broadcast::Sender<String>,
    auth: AuthPolicy,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Principal {
    Observer,
    Commander,
}

#[derive(Clone, Default)]
struct AuthPolicy {
    command_token_hash: Option<[u8; 32]>,
    observer_token_hash: Option<[u8; 32]>,
    browser_origins: Arc<HashSet<String>>,
    sessions: Arc<std::sync::Mutex<HashMap<[u8; 32], Session>>>,
}

#[derive(Clone, Copy)]
struct Session {
    principal: Principal,
    expires_at: Instant,
}

impl AuthPolicy {
    fn authenticate(&self, presented: Option<&str>) -> Option<Principal> {
        let presented = hash_secret(presented?);
        if self
            .command_token_hash
            .is_some_and(|expected| secret_hash_eq(&expected, &presented))
        {
            Some(Principal::Commander)
        } else if self
            .observer_token_hash
            .is_some_and(|expected| secret_hash_eq(&expected, &presented))
        {
            Some(Principal::Observer)
        } else {
            None
        }
    }

    fn authorize_command(&self, principal: Option<Principal>) -> bool {
        principal == Some(Principal::Commander)
    }

    fn origin_allowed(&self, headers: &HeaderMap) -> bool {
        let values: Vec<_> = headers.get_all(ORIGIN).iter().collect();
        values.len() == 1
            && values[0]
                .to_str()
                .ok()
                .is_some_and(|o| self.browser_origins.contains(o))
    }

    fn create_session(&self, principal: Principal) -> String {
        let mut raw = [0u8; 32];
        OsRng.fill_bytes(&mut raw);
        let encoded = hex(&raw);
        let key = hash_secret(&encoded);
        self.sessions.lock().expect("session lock").insert(
            key,
            Session {
                principal,
                expires_at: Instant::now() + Duration::from_secs(SESSION_TTL_SECONDS),
            },
        );
        encoded
    }

    fn cookie_principal(&self, headers: &HeaderMap) -> Option<Principal> {
        let cookie = cookie_value(headers, SESSION_COOKIE)?;
        let key = hash_secret(cookie);
        let mut sessions = self.sessions.lock().ok()?;
        sessions.retain(|_, s| s.expires_at > Instant::now());
        sessions.get(&key).map(|s| s.principal)
    }
}

fn hash_secret(secret: &str) -> [u8; 32] {
    Sha256::digest(secret.as_bytes()).into()
}
fn secret_hash_eq(a: &[u8; 32], b: &[u8; 32]) -> bool {
    bool::from(a.ct_eq(b))
}
fn hex(raw: &[u8]) -> String {
    raw.iter().map(|b| format!("{b:02x}")).collect()
}

#[derive(Serialize)]
#[serde(tag = "type", rename_all = "kebab-case")]
enum ServerMessage<'a> {
    Connected { command_authority: bool },
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
    let command_token = take_option(&mut args, "--command-token").map(Arc::from);
    let observer_token = take_option(&mut args, "--observer-token").map(Arc::from);
    let browser_origins = take_options(&mut args, "--browser-origin")
        .into_iter()
        .collect::<HashSet<_>>();
    let auth = auth_policy(
        command_token.as_deref(),
        observer_token.as_deref(),
        browser_origins,
    )?;

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
        auth,
    };

    spawn_tick_loop(state.clone(), tick_ms);

    let app = build_router(state.clone());

    let listener = tokio::net::TcpListener::bind((bind_host, port))
        .await
        .map_err(|err| format!("failed to bind {bind_host}:{port}: {err}"))?;
    println!(
        "fleetcore live server listening: ws://{bind_host}:{port}/ws  http://{bind_host}:{port}/snapshot  http://{bind_host}:{port}/command"
    );
    if state.auth.command_token_hash.is_some() {
        println!("fleetcore-serve: command mutations require the configured command token");
    } else {
        println!("fleetcore-serve: no command token configured; all external mutations denied");
    }
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .map_err(|err| err.to_string())
}

fn auth_policy(
    command: Option<&str>,
    observer: Option<&str>,
    origins: HashSet<String>,
) -> Result<AuthPolicy, String> {
    if command.is_some() && command == observer {
        return Err("--command-token and --observer-token must differ".to_string());
    }
    Ok(AuthPolicy {
        command_token_hash: command.map(hash_secret),
        observer_token_hash: observer.map(hash_secret),
        browser_origins: Arc::new(origins),
        sessions: Arc::default(),
    })
}

fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/snapshot", get(get_snapshot))
        .route("/command", post(post_command).options(reject_preflight))
        .route(
            "/auth/session",
            post(create_browser_session).options(reject_preflight),
        )
        .route("/ws", get(ws_handler))
        .with_state(state)
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

/// Read + write JSON-over-HTTP path for operator commands (see Sprint.md's
/// "Write endpoint(s): accept operator commands"), independent of the
/// WebSocket transport. Requires `Authorization: Bearer <command-token>`.
async fn post_command(
    State(state): State<AppState>,
    headers: HeaderMap,
    body: String,
) -> impl IntoResponse {
    let principal = command_principal(&state.auth, &headers);
    if headers.contains_key(ORIGIN) && !state.auth.origin_allowed(&headers) {
        return (
            StatusCode::FORBIDDEN,
            Json(serde_json::json!({ "error": "browser origin is not allowed" })),
        );
    }
    if principal.is_none() {
        return (
            StatusCode::UNAUTHORIZED,
            Json(serde_json::json!({ "error": "missing or invalid command token" })),
        );
    }
    if !state.auth.authorize_command(principal) {
        return (
            StatusCode::FORBIDDEN,
            Json(serde_json::json!({ "error": "authenticated caller lacks command authority" })),
        );
    }
    let command: Command = match serde_json::from_str(&body) {
        Ok(command) => command,
        Err(err) => {
            return (
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({ "error": format!("invalid command: {err}") })),
            );
        }
    };
    match apply_and_broadcast(&state, command).await {
        Ok(snap) => (
            StatusCode::OK,
            Json(serde_json::to_value(snap).unwrap_or_default()),
        ),
        Err(err) => (
            StatusCode::UNPROCESSABLE_ENTITY,
            Json(serde_json::json!({ "error": err })),
        ),
    }
}

fn bearer_token(headers: &HeaderMap) -> Option<&str> {
    let values: Vec<_> = headers.get_all(AUTHORIZATION).iter().collect();
    if values.len() != 1 {
        return None;
    }
    values[0]
        .to_str()
        .ok()
        .and_then(|value| value.strip_prefix("Bearer "))
        .filter(|v| !v.is_empty())
}

fn cookie_value<'a>(headers: &'a HeaderMap, name: &str) -> Option<&'a str> {
    let mut found = None;
    for header in headers.get_all(COOKIE).iter() {
        let raw = header.to_str().ok()?;
        for part in raw.split(';') {
            let (key, value) = part.trim().split_once('=')?;
            if key == name {
                if found.is_some() || value.is_empty() {
                    return None;
                }
                found = Some(value);
            }
        }
    }
    found
}

fn command_principal(auth: &AuthPolicy, headers: &HeaderMap) -> Option<Principal> {
    if headers.contains_key(ORIGIN) {
        if !auth.origin_allowed(headers) {
            return None;
        }
        auth.cookie_principal(headers)
    } else {
        auth.authenticate(bearer_token(headers))
    }
}

async fn create_browser_session(
    State(state): State<AppState>,
    headers: HeaderMap,
) -> impl IntoResponse {
    if !state.auth.origin_allowed(&headers) {
        return (
            StatusCode::FORBIDDEN,
            HeaderMap::new(),
            Json(serde_json::json!({"error":"browser origin is not allowed"})),
        );
    }
    let principal = state.auth.authenticate(bearer_token(&headers));
    if principal.is_none() {
        return (
            StatusCode::UNAUTHORIZED,
            HeaderMap::new(),
            Json(serde_json::json!({"error":"missing or invalid command token"})),
        );
    }
    if !state.auth.authorize_command(principal) {
        return (
            StatusCode::FORBIDDEN,
            HeaderMap::new(),
            Json(serde_json::json!({"error":"authenticated caller lacks command authority"})),
        );
    }
    let session = state
        .auth
        .create_session(principal.expect("checked principal"));
    let mut response_headers = HeaderMap::new();
    response_headers.insert(SET_COOKIE,format!("{SESSION_COOKIE}={session}; Path=/; Max-Age={SESSION_TTL_SECONDS}; HttpOnly; Secure; SameSite=Strict").parse().expect("cookie header"));
    (
        StatusCode::OK,
        response_headers,
        Json(serde_json::json!({"expires_in":SESSION_TTL_SECONDS})),
    )
}

async fn reject_preflight() -> impl IntoResponse {
    (
        StatusCode::FORBIDDEN,
        Json(serde_json::json!({"error":"cross-origin mutation is disabled"})),
    )
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    headers: HeaderMap,
    State(state): State<AppState>,
) -> impl IntoResponse {
    let principal = command_principal(&state.auth, &headers);
    ws.on_upgrade(move |socket| handle_socket(socket, state, principal))
}

async fn handle_socket(socket: WebSocket, state: AppState, principal: Option<Principal>) {
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
            command_authority: state.auth.authorize_command(principal),
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
                handle_client_message(&recv_state, &text, principal, &direct_tx).await;
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
    principal: Option<Principal>,
    reply: &mpsc::UnboundedSender<String>,
) {
    if principal.is_none() {
        send_error(
            reply,
            "unauthenticated connection: reconnect with a valid bearer token".to_string(),
        );
        return;
    }
    if !state.auth.authorize_command(principal) {
        send_error(
            reply,
            "authenticated caller lacks command authority".to_string(),
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
    let mut world = state.world.lock().await;
    let event = world.apply_command(command)?;
    if let Err(err) = append_event(&state.paths, &event) {
        eprintln!("fleetcore-serve: failed to append event: {err}");
    }
    if let Err(err) = save_world(&state.paths, &world) {
        eprintln!("fleetcore-serve: failed to save world: {err}");
    }
    let snap = snapshot(&world);
    if let Ok(json) = serde_json::to_string(&ServerMessage::Snapshot { snapshot: &snap }) {
        let _ = state.tx.send(json);
    }
    Ok(snap)
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

fn take_options(args: &mut Vec<String>, name: &str) -> Vec<String> {
    let mut values = Vec::new();
    while let Some(value) = take_option(args, name) {
        values.push(value);
    }
    values
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
mod auth_tests {
    use super::*;
    use fleetcore::persistence::{load_seed, save_checkpoint, save_world, write_snapshot};
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio_tungstenite::{
        connect_async,
        tungstenite::{client::IntoClientRequest, Message as WsMessage},
    };

    fn policy() -> AuthPolicy {
        AuthPolicy {
            command_token_hash: Some(hash_secret("command-secret")),
            observer_token_hash: Some(hash_secret("observer-secret")),
            browser_origins: Arc::new(HashSet::from(["https://bridge.example".to_string()])),
            sessions: Arc::default(),
        }
    }

    async fn scratch_state(root: &Path) -> AppState {
        let seed = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json");
        let paths = StorePaths::new(root, seed);
        let world = load_seed(&paths).expect("load seed");
        save_world(&paths, &world).expect("save baseline world");
        save_checkpoint(&paths, &world).expect("save baseline checkpoint");
        write_snapshot(&paths, &world, None).expect("save baseline snapshot");
        let (tx, _rx) = broadcast::channel(8);
        AppState {
            world: Arc::new(Mutex::new(world)),
            paths: Arc::new(paths),
            tx,
            auth: policy(),
        }
    }

    async fn raw_http(addr: std::net::SocketAddr, request: &str) -> String {
        let mut stream = tokio::net::TcpStream::connect(addr)
            .await
            .expect("connect router");
        stream
            .write_all(request.as_bytes())
            .await
            .expect("write request");
        let mut response = Vec::new();
        stream
            .read_to_end(&mut response)
            .await
            .expect("read response");
        String::from_utf8(response).expect("http utf8")
    }

    fn scratch_dir() -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos();
        env::temp_dir().join(format!("fleetcore-auth-{}-{nonce}", std::process::id()))
    }

    fn files_under(root: &Path) -> Vec<(PathBuf, Vec<u8>)> {
        fn visit(root: &Path, current: &Path, files: &mut Vec<(PathBuf, Vec<u8>)>) {
            for entry in fs::read_dir(current).expect("read scratch tree") {
                let path = entry.expect("directory entry").path();
                if path.is_dir() {
                    visit(root, &path, files);
                } else {
                    files.push((
                        path.strip_prefix(root)
                            .expect("relative path")
                            .to_path_buf(),
                        fs::read(path).expect("read scratch file"),
                    ));
                }
            }
        }
        let mut files = Vec::new();
        visit(root, root, &mut files);
        files.sort_by(|left, right| left.0.cmp(&right.0));
        files
    }

    #[test]
    fn authentication_and_authorization_are_separate_and_default_deny() {
        let policy = policy();
        assert_eq!(policy.authenticate(None), None);
        assert_eq!(policy.authenticate(Some("wrong")), None);
        let observer = policy.authenticate(Some("observer-secret"));
        assert_eq!(observer, Some(Principal::Observer));
        assert!(!policy.authorize_command(observer));
        assert!(policy.authorize_command(policy.authenticate(Some("command-secret"))));
        assert!(!AuthPolicy::default().authorize_command(None));
        assert!(auth_policy(Some("same"), Some("same"), HashSet::new()).is_err());
    }

    #[test]
    fn bearer_auth_is_shared_and_query_tokens_are_not_accepted() {
        let mut headers = HeaderMap::new();
        assert_eq!(bearer_token(&headers), None);
        headers.insert(AUTHORIZATION, "Basic abc".parse().expect("header"));
        assert_eq!(bearer_token(&headers), None);
        headers.insert(
            AUTHORIZATION,
            "Bearer command-secret".parse().expect("header"),
        );
        assert_eq!(bearer_token(&headers), Some("command-secret"));
        headers.append(
            AUTHORIZATION,
            "Bearer command-secret".parse().expect("header"),
        );
        assert_eq!(bearer_token(&headers), None);
        // Both post_command and ws_handler call this same extractor. There is
        // deliberately no WebSocket query-token parser for secrets to leak to
        // logs, browser history, or referrers.
    }

    #[test]
    fn sessions_expire_and_duplicate_cookies_fail_closed() {
        let p = policy();
        let raw = "abc";
        p.sessions.lock().expect("lock").insert(
            hash_secret(raw),
            Session {
                principal: Principal::Commander,
                expires_at: Instant::now() - Duration::from_secs(1),
            },
        );
        let mut h = HeaderMap::new();
        h.insert(
            COOKIE,
            format!("{SESSION_COOKIE}={raw}").parse().expect("cookie"),
        );
        assert_eq!(p.cookie_principal(&h), None);
        h.insert(
            COOKIE,
            format!("{SESSION_COOKIE}=one; {SESSION_COOKIE}=two")
                .parse()
                .expect("cookie"),
        );
        assert_eq!(p.cookie_principal(&h), None);
    }

    #[tokio::test]
    async fn real_router_session_origin_cors_and_websocket_authority() {
        let root = scratch_dir();
        let state = scratch_state(&root).await;
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind");
        let addr = listener.local_addr().expect("addr");
        let server = tokio::spawn(async move {
            axum::serve(listener, build_router(state))
                .await
                .expect("serve")
        });

        let get = raw_http(
            addr,
            "GET /snapshot HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
        )
        .await;
        assert!(get.starts_with("HTTP/1.1 200"));
        assert!(get
            .to_ascii_lowercase()
            .contains("access-control-allow-origin: *"));
        let preflight=raw_http(addr,"OPTIONS /command HTTP/1.1\r\nHost: localhost\r\nOrigin: https://bridge.example\r\nConnection: close\r\n\r\n").await;
        assert!(preflight.starts_with("HTTP/1.1 403"));
        assert!(!preflight
            .to_ascii_lowercase()
            .contains("access-control-allow-origin"));
        let cross=raw_http(addr,"POST /auth/session HTTP/1.1\r\nHost: localhost\r\nOrigin: https://evil.example\r\nAuthorization: Bearer command-secret\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").await;
        assert!(cross.starts_with("HTTP/1.1 403"));
        let observer_session=raw_http(addr,"POST /auth/session HTTP/1.1\r\nHost: localhost\r\nOrigin: https://bridge.example\r\nAuthorization: Bearer observer-secret\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").await;
        assert!(observer_session.starts_with("HTTP/1.1 403"));
        let multiple_origin=raw_http(addr,"POST /auth/session HTTP/1.1\r\nHost: localhost\r\nOrigin: https://bridge.example\r\nOrigin: https://bridge.example\r\nAuthorization: Bearer command-secret\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").await;
        assert!(multiple_origin.starts_with("HTTP/1.1 403"));
        let duplicate=raw_http(addr,"POST /command HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer command-secret\r\nAuthorization: Bearer command-secret\r\nContent-Length: 22\r\nConnection: close\r\n\r\n{\"type\":\"pause-clock\"}").await;
        assert!(duplicate.starts_with("HTTP/1.1 401"));
        let session=raw_http(addr,"POST /auth/session HTTP/1.1\r\nHost: localhost\r\nOrigin: https://bridge.example\r\nAuthorization: Bearer command-secret\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").await;
        assert!(session.starts_with("HTTP/1.1 200"));
        let cookie = session
            .lines()
            .find(|l| l.to_ascii_lowercase().starts_with("set-cookie:"))
            .expect("set cookie")
            .split_once(':')
            .expect("colon")
            .1
            .trim()
            .split(';')
            .next()
            .expect("cookie pair")
            .to_string();
        assert!(session.contains("HttpOnly"));
        assert!(session.contains("Secure"));
        assert!(session.contains("SameSite=Strict"));

        let mut request = format!("ws://{addr}/ws")
            .into_client_request()
            .expect("ws request");
        request
            .headers_mut()
            .insert(ORIGIN, "https://bridge.example".parse().expect("origin"));
        request
            .headers_mut()
            .insert(COOKIE, cookie.parse().expect("cookie"));
        let (mut ws, _) = connect_async(request).await.expect("session websocket");
        let connected = ws
            .next()
            .await
            .expect("connected")
            .expect("frame")
            .into_text()
            .expect("text");
        assert!(connected.contains("\"command_authority\":true"));
        ws.send(WsMessage::Text(r#"{"type":"pause-clock"}"#.into()))
            .await
            .expect("send command");

        let mut observer = format!("ws://{addr}/ws")
            .into_client_request()
            .expect("ws request");
        observer.headers_mut().insert(
            AUTHORIZATION,
            "Bearer observer-secret".parse().expect("bearer"),
        );
        let (mut observer, _) = connect_async(observer).await.expect("observer websocket");
        let connected = observer
            .next()
            .await
            .expect("connected")
            .expect("frame")
            .into_text()
            .expect("text");
        assert!(connected.contains("\"command_authority\":false"));
        server.abort();
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[tokio::test]
    async fn rejected_callers_cannot_mutate_world_events_or_checkpoints() {
        let root = scratch_dir();
        let state = scratch_state(&root).await;
        let before_files = files_under(&root);
        let before_world =
            serde_json::to_vec(&*state.world.lock().await).expect("serialize baseline");
        let attempts = [
            (None, None, StatusCode::UNAUTHORIZED, "anonymous"),
            (
                Some("invalid"),
                state.auth.authenticate(Some("invalid")),
                StatusCode::UNAUTHORIZED,
                "invalid",
            ),
            (
                Some("observer-secret"),
                state.auth.authenticate(Some("observer-secret")),
                StatusCode::FORBIDDEN,
                "insufficient",
            ),
        ];
        for (token, principal, expected_status, label) in attempts {
            let mut headers = HeaderMap::new();
            if let Some(token) = token {
                headers.insert(
                    AUTHORIZATION,
                    format!("Bearer {token}").parse().expect("auth header"),
                );
            }
            let response = post_command(
                State(state.clone()),
                headers,
                r#"{"type":"pause-clock"}"#.to_string(),
            )
            .await
            .into_response();
            assert_eq!(response.status(), expected_status, "{label} HTTP status");

            let (reply, mut replies) = mpsc::unbounded_channel();
            handle_client_message(&state, r#"{"type":"pause-clock"}"#, principal, &reply).await;
            let response = replies.try_recv().expect("targeted rejection");
            assert!(response.contains("error"), "{label}: {response}");
            assert_eq!(
                serde_json::to_vec(&*state.world.lock().await).expect("serialize world"),
                before_world,
                "{label} changed in-memory world"
            );
            assert_eq!(
                files_under(&root),
                before_files,
                "{label} changed persistence"
            );
        }
        fs::remove_dir_all(root).expect("remove scratch state");
    }
}
