use axum::body::{to_bytes, Body};
use axum::http::{Request, StatusCode};
use fleetcore::history_api::{
    history_v2_router, HistoryPage, HistoryQuery, HistoryStoreError, SequencedVesselEvent,
    VesselEventHistoryStore,
};
use fleetcore::vessel::VesselEvent;
use serde_json::Value;
use std::sync::{Arc, Mutex};
use tower::ServiceExt;

struct RecordingStore {
    result: Result<HistoryPage, HistoryStoreError>,
    queries: Mutex<Vec<HistoryQuery>>,
}

impl VesselEventHistoryStore for RecordingStore {
    fn query(&self, query: &HistoryQuery) -> Result<HistoryPage, HistoryStoreError> {
        self.queries.lock().unwrap().push(query.clone());
        self.result.clone()
    }
}

fn event(sequence: u64, world: &str, mission: Option<&str>, kind: &str) -> SequencedVesselEvent {
    let event = match kind {
        "holding" => VesselEvent::Holding {
            vessel_id: "vessel.monad".into(),
            tick: sequence,
            sim_time: "2026-01-01T00:00:00Z".into(),
        },
        _ => VesselEvent::RouteCompleted {
            vessel_id: "vessel.monad".into(),
            route_id: 7,
            tick: sequence,
            sim_time: "2026-01-01T00:00:00Z".into(),
        },
    };
    SequencedVesselEvent {
        sequence,
        world_id: world.into(),
        mission_scope: mission.map(str::to_string),
        event,
    }
}

async fn request(store: Arc<RecordingStore>, uri: &str) -> (StatusCode, Value) {
    let response = history_v2_router(store)
        .oneshot(Request::builder().uri(uri).body(Body::empty()).unwrap())
        .await
        .unwrap();
    let status = response.status();
    let bytes = to_bytes(response.into_body(), usize::MAX).await.unwrap();
    let body = serde_json::from_slice(&bytes)
        .unwrap_or_else(|_| Value::String(String::from_utf8_lossy(&bytes).into_owned()));
    (status, body)
}

#[tokio::test]
async fn bounded_filters_are_forwarded_and_page_is_deterministically_ordered() {
    let store = Arc::new(RecordingStore {
        result: Ok(HistoryPage {
            oldest_available_sequence: Some(10),
            newest_available_sequence: Some(30),
            events: vec![
                event(21, "monad.local", Some("mission.alpha"), "holding"),
                event(25, "monad.local", Some("mission.alpha"), "holding"),
            ],
            next_cursor: Some(25),
        }),
        queries: Mutex::new(vec![]),
    });
    let (status, body) = request(store.clone(), "/v2/vessel-events?after_sequence=20&limit=2&event_type=holding&world_id=monad.local&mission_scope=mission.alpha").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["events"][0]["sequence"], 21);
    assert_eq!(body["events"][1]["sequence"], 25);
    assert_eq!(body["next_cursor"], 25);
    let query = &store.queries.lock().unwrap()[0];
    assert_eq!(query.after_sequence, Some(20));
    assert_eq!(query.limit, 2);
    assert_eq!(query.world_id.as_deref(), Some("monad.local"));
    assert_eq!(query.mission_scope.as_deref(), Some("mission.alpha"));
}

#[tokio::test]
async fn default_and_maximum_page_limits_are_enforced() {
    let store = Arc::new(RecordingStore {
        result: Ok(HistoryPage {
            oldest_available_sequence: None,
            newest_available_sequence: None,
            events: vec![],
            next_cursor: None,
        }),
        queries: Mutex::new(vec![]),
    });
    assert_eq!(
        request(store.clone(), "/v2/vessel-events").await.0,
        StatusCode::OK
    );
    assert_eq!(store.queries.lock().unwrap()[0].limit, 50);
    assert_eq!(
        request(store.clone(), "/v2/vessel-events?limit=0").await.0,
        StatusCode::BAD_REQUEST
    );
    assert_eq!(
        request(store, "/v2/vessel-events?limit=201").await.0,
        StatusCode::BAD_REQUEST
    );
}

#[tokio::test]
async fn gaps_are_explicit_and_include_available_range() {
    let store = Arc::new(RecordingStore {
        result: Err(HistoryStoreError::Gap {
            requested_after: 4,
            oldest_available: 10,
            newest_available: 30,
        }),
        queries: Mutex::new(vec![]),
    });
    let (status, body) = request(store, "/v2/vessel-events?after_sequence=4").await;
    assert_eq!(status, StatusCode::GONE);
    assert_eq!(body["error"], "history_gap");
    assert_eq!(body["oldest_available_sequence"], 10);
    assert_eq!(body["newest_available_sequence"], 30);
}

#[tokio::test]
async fn semantic_search_and_unknown_parameters_are_rejected() {
    let store = Arc::new(RecordingStore {
        result: Ok(HistoryPage {
            oldest_available_sequence: None,
            newest_available_sequence: None,
            events: vec![],
            next_cursor: None,
        }),
        queries: Mutex::new(vec![]),
    });
    let unknown = request(store.clone(), "/v2/vessel-events?search=reactor").await;
    assert_eq!(unknown.0, StatusCode::BAD_REQUEST);
    assert_eq!(unknown.1["error"], "invalid_request");
    let malformed = request(store, "/v2/vessel-events?limit=not-a-number").await;
    assert_eq!(malformed.0, StatusCode::BAD_REQUEST);
    assert_eq!(malformed.1["error"], "invalid_request");
}

#[tokio::test]
async fn store_contract_violations_fail_closed() {
    let store = Arc::new(RecordingStore {
        result: Ok(HistoryPage {
            oldest_available_sequence: Some(1),
            newest_available_sequence: Some(9),
            events: vec![
                event(9, "monad.local", None, "holding"),
                event(8, "monad.local", None, "holding"),
            ],
            next_cursor: Some(8),
        }),
        queries: Mutex::new(vec![]),
    });
    let (status, body) = request(store, "/v2/vessel-events").await;
    assert_eq!(status, StatusCode::SERVICE_UNAVAILABLE);
    assert_eq!(body["error"], "history_unavailable");
}

#[tokio::test]
async fn route_is_read_only() {
    let store = Arc::new(RecordingStore {
        result: Ok(HistoryPage {
            oldest_available_sequence: None,
            newest_available_sequence: None,
            events: vec![],
            next_cursor: None,
        }),
        queries: Mutex::new(vec![]),
    });
    let response = history_v2_router(store)
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/v2/vessel-events")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::METHOD_NOT_ALLOWED);
}
