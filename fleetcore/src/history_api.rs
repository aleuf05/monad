//! Bounded, read-only VesselEvent history API contract.
//!
//! Storage is deliberately abstract: the durable Slice A implementation can
//! implement `VesselEventHistoryStore` without this API depending on its file
//! layout, compaction strategy, or in-memory representation.

use crate::persistence::{read_events, StorePaths};
use crate::vessel::VesselEvent;
use axum::extract::rejection::QueryRejection;
use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

pub const DEFAULT_PAGE_LIMIT: usize = 50;
pub const MAX_PAGE_LIMIT: usize = 200;
pub const DEFAULT_OPERATIONAL_TAIL_LIMIT: usize = 2_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OperationalTailConfig {
    pub limit: usize,
}

impl Default for OperationalTailConfig {
    fn default() -> Self {
        Self {
            limit: DEFAULT_OPERATIONAL_TAIL_LIMIT,
        }
    }
}

impl OperationalTailConfig {
    pub fn new(limit: usize) -> Result<Self, HistoryStoreError> {
        if limit == 0 {
            return Err(HistoryStoreError::InvalidRequest(
                "operational vessel-event tail limit must be greater than zero".to_string(),
            ));
        }
        Ok(Self { limit })
    }
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum VesselEventType {
    WaypointReached,
    RouteReplaced,
    RouteCompleted,
    Holding,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct SequencedVesselEvent {
    pub sequence: u64,
    pub world_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mission_scope: Option<String>,
    #[serde(flatten)]
    pub event: VesselEvent,
}

impl SequencedVesselEvent {
    pub fn event_type(&self) -> VesselEventType {
        match self.event {
            VesselEvent::WaypointReached { .. } => VesselEventType::WaypointReached,
            VesselEvent::RouteReplaced { .. } => VesselEventType::RouteReplaced,
            VesselEvent::RouteCompleted { .. } => VesselEventType::RouteCompleted,
            VesselEvent::Holding { .. } => VesselEventType::Holding,
        }
    }
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct HistoryQueryParams {
    /// Exclusive cursor. Omit to begin at the oldest retained matching event.
    pub after_sequence: Option<u64>,
    pub limit: Option<usize>,
    pub event_type: Option<VesselEventType>,
    pub world_id: Option<String>,
    pub mission_scope: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HistoryQuery {
    pub after_sequence: Option<u64>,
    pub limit: usize,
    pub event_type: Option<VesselEventType>,
    pub world_id: Option<String>,
    pub mission_scope: Option<String>,
}

impl TryFrom<HistoryQueryParams> for HistoryQuery {
    type Error = HistoryStoreError;

    fn try_from(params: HistoryQueryParams) -> Result<Self, Self::Error> {
        let limit = params.limit.unwrap_or(DEFAULT_PAGE_LIMIT);
        if !(1..=MAX_PAGE_LIMIT).contains(&limit) {
            return Err(HistoryStoreError::InvalidRequest(format!(
                "limit must be between 1 and {MAX_PAGE_LIMIT}"
            )));
        }
        if params.world_id.as_deref() == Some("") || params.mission_scope.as_deref() == Some("") {
            return Err(HistoryStoreError::InvalidRequest(
                "world_id and mission_scope must not be empty".to_string(),
            ));
        }
        Ok(Self {
            after_sequence: params.after_sequence,
            limit,
            event_type: params.event_type,
            world_id: params.world_id,
            mission_scope: params.mission_scope,
        })
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct HistoryPage {
    pub oldest_available_sequence: Option<u64>,
    pub newest_available_sequence: Option<u64>,
    pub events: Vec<SequencedVesselEvent>,
    /// Sequence of the final returned event. Omitted when there is no next page.
    pub next_cursor: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HistoryStoreError {
    InvalidRequest(String),
    Gap {
        requested_after: u64,
        oldest_available: u64,
        newest_available: u64,
    },
    Unavailable(String),
}

pub trait VesselEventHistoryStore: Send + Sync + 'static {
    /// Return events in strictly increasing sequence order, after the exclusive
    /// cursor, with all supplied scopes applied and no more than `query.limit`.
    fn query(&self, query: &HistoryQuery) -> Result<HistoryPage, HistoryStoreError>;
}

/// Read-only view over Slice A's authoritative V2 command envelopes.
pub struct JsonlVesselEventHistoryStore {
    paths: StorePaths,
    world_id: String,
}

impl JsonlVesselEventHistoryStore {
    pub fn new(paths: StorePaths, world_id: String) -> Self {
        Self { paths, world_id }
    }
}

impl VesselEventHistoryStore for JsonlVesselEventHistoryStore {
    fn query(&self, query: &HistoryQuery) -> Result<HistoryPage, HistoryStoreError> {
        if query.mission_scope.is_some() {
            return Err(HistoryStoreError::InvalidRequest(
                "mission_scope attribution is unavailable in authoritative vessel-event history"
                    .to_string(),
            ));
        }
        if query
            .world_id
            .as_ref()
            .is_some_and(|requested| requested != &self.world_id)
        {
            return Err(HistoryStoreError::InvalidRequest(format!(
                "unknown world_id '{}'",
                query.world_id.as_deref().unwrap_or_default()
            )));
        }
        let records = read_events(&self.paths).map_err(HistoryStoreError::Unavailable)?;
        let all = records
            .into_iter()
            .flat_map(|envelope| envelope.vessel_events)
            .map(|record| SequencedVesselEvent {
                sequence: record.sequence,
                world_id: self.world_id.clone(),
                mission_scope: None,
                event: record.event,
            })
            .collect::<Vec<_>>();
        if all
            .windows(2)
            .any(|pair| pair[0].sequence >= pair[1].sequence)
        {
            return Err(HistoryStoreError::Unavailable(
                "authoritative vessel-event sequence is duplicate or unordered".to_string(),
            ));
        }
        let oldest = all.first().map(|event| event.sequence);
        let newest = all.last().map(|event| event.sequence);
        if let (Some(cursor), Some(oldest), Some(newest)) = (query.after_sequence, oldest, newest) {
            if cursor.saturating_add(1) < oldest {
                return Err(HistoryStoreError::Gap {
                    requested_after: cursor,
                    oldest_available: oldest,
                    newest_available: newest,
                });
            }
        }
        let matching = all
            .into_iter()
            .filter(|event| {
                query
                    .after_sequence
                    .is_none_or(|cursor| event.sequence > cursor)
                    && query
                        .event_type
                        .is_none_or(|kind| event.event_type() == kind)
            })
            .collect::<Vec<_>>();
        let has_more = matching.len() > query.limit;
        let events = matching.into_iter().take(query.limit).collect::<Vec<_>>();
        let next_cursor = has_more.then(|| events.last().expect("non-empty limited page").sequence);
        Ok(HistoryPage {
            oldest_available_sequence: oldest,
            newest_available_sequence: newest,
            events,
            next_cursor,
        })
    }
}

#[derive(Clone)]
pub struct HistoryApiState {
    pub store: Arc<dyn VesselEventHistoryStore>,
}

pub fn history_v2_router(store: Arc<dyn VesselEventHistoryStore>) -> Router {
    Router::new()
        .route("/v2/vessel-events", get(get_vessel_events))
        .with_state(HistoryApiState { store })
}

async fn get_vessel_events(
    State(state): State<HistoryApiState>,
    params: Result<Query<HistoryQueryParams>, QueryRejection>,
) -> Result<Json<HistoryPage>, HistoryApiError> {
    let Query(params) = params
        .map_err(|error| HistoryApiError(HistoryStoreError::InvalidRequest(error.body_text())))?;
    let query = HistoryQuery::try_from(params).map_err(HistoryApiError)?;
    let page = state.store.query(&query).map_err(HistoryApiError)?;
    validate_page(&query, &page).map_err(HistoryApiError)?;
    Ok(Json(page))
}

fn validate_page(query: &HistoryQuery, page: &HistoryPage) -> Result<(), HistoryStoreError> {
    if page.events.len() > query.limit {
        return Err(HistoryStoreError::Unavailable(
            "history store exceeded requested page limit".to_string(),
        ));
    }
    if page
        .events
        .windows(2)
        .any(|pair| pair[0].sequence >= pair[1].sequence)
    {
        return Err(HistoryStoreError::Unavailable(
            "history store returned non-deterministic sequence order".to_string(),
        ));
    }
    if page.next_cursor
        != page
            .events
            .last()
            .map(|event| event.sequence)
            .filter(|_| page.next_cursor.is_some())
    {
        return Err(HistoryStoreError::Unavailable(
            "history store returned an invalid next cursor".to_string(),
        ));
    }
    if page.events.iter().any(|event| {
        page.oldest_available_sequence
            .is_some_and(|oldest| event.sequence < oldest)
            || page
                .newest_available_sequence
                .is_some_and(|newest| event.sequence > newest)
    }) {
        return Err(HistoryStoreError::Unavailable(
            "history store returned an event outside its available range".to_string(),
        ));
    }
    if page.events.iter().any(|event| {
        query
            .after_sequence
            .is_some_and(|cursor| event.sequence <= cursor)
            || query
                .event_type
                .is_some_and(|kind| event.event_type() != kind)
            || query
                .world_id
                .as_ref()
                .is_some_and(|id| &event.world_id != id)
            || query
                .mission_scope
                .as_ref()
                .is_some_and(|scope| event.mission_scope.as_ref() != Some(scope))
    }) {
        return Err(HistoryStoreError::Unavailable(
            "history store returned an event outside the requested range or scope".to_string(),
        ));
    }
    Ok(())
}

struct HistoryApiError(HistoryStoreError);

#[derive(Serialize)]
struct ErrorBody {
    error: &'static str,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    requested_after: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    oldest_available_sequence: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    newest_available_sequence: Option<u64>,
}

impl IntoResponse for HistoryApiError {
    fn into_response(self) -> Response {
        let (status, body) = match self.0 {
            HistoryStoreError::InvalidRequest(message) => (
                StatusCode::BAD_REQUEST,
                ErrorBody {
                    error: "invalid_request",
                    message,
                    requested_after: None,
                    oldest_available_sequence: None,
                    newest_available_sequence: None,
                },
            ),
            HistoryStoreError::Gap {
                requested_after,
                oldest_available,
                newest_available,
            } => (
                StatusCode::GONE,
                ErrorBody {
                    error: "history_gap",
                    message: "requested cursor predates retained history".to_string(),
                    requested_after: Some(requested_after),
                    oldest_available_sequence: Some(oldest_available),
                    newest_available_sequence: Some(newest_available),
                },
            ),
            HistoryStoreError::Unavailable(message) => (
                StatusCode::SERVICE_UNAVAILABLE,
                ErrorBody {
                    error: "history_unavailable",
                    message,
                    requested_after: None,
                    oldest_available_sequence: None,
                    newest_available_sequence: None,
                },
            ),
        };
        (status, Json(body)).into_response()
    }
}
