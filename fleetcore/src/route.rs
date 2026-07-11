use crate::vessel::{normalize_degrees, normalize_longitude, quantize, Position};

const EARTH_RADIUS_METERS: f64 = 6_371_000.0;

pub fn distance_meters(start: Position, end: Position) -> f64 {
    let lat_delta = (end.lat - start.lat).to_radians();
    let lng_delta = (end.lng - start.lng).to_radians();
    let start_lat = start.lat.to_radians();
    let end_lat = end.lat.to_radians();
    let haversine = (lat_delta / 2.0).sin().powi(2)
        + start_lat.cos() * end_lat.cos() * (lng_delta / 2.0).sin().powi(2);
    EARTH_RADIUS_METERS * 2.0 * haversine.sqrt().atan2((1.0 - haversine).sqrt())
}

pub fn bearing_degrees(start: Position, end: Position) -> f64 {
    let start_lat = start.lat.to_radians();
    let end_lat = end.lat.to_radians();
    let lng_delta = (end.lng - start.lng).to_radians();
    let y = lng_delta.sin() * end_lat.cos();
    let x = start_lat.cos() * end_lat.sin() - start_lat.sin() * end_lat.cos() * lng_delta.cos();
    normalize_degrees(y.atan2(x).to_degrees())
}

pub fn point_at_distance(start: Position, bearing_degrees: f64, distance_meters: f64) -> Position {
    let angular_distance = distance_meters / EARTH_RADIUS_METERS;
    let bearing = bearing_degrees.to_radians();
    let start_lat = start.lat.to_radians();
    let start_lng = start.lng.to_radians();
    let end_lat = (start_lat.sin() * angular_distance.cos()
        + start_lat.cos() * angular_distance.sin() * bearing.cos())
    .asin();
    let end_lng = start_lng
        + (bearing.sin() * angular_distance.sin() * start_lat.cos())
            .atan2(angular_distance.cos() - start_lat.sin() * end_lat.sin());
    Position {
        lat: quantize(end_lat.to_degrees().clamp(-90.0, 90.0)),
        lng: quantize(normalize_longitude(end_lng.to_degrees())),
    }
}
