//! Deformation probe — Packet Beta Module 3, the clipping-and-pinching test.
//!
//! A rig that passes AUTHORIZE is *valid*: weights sum to 1.0, no shell is
//! split across bones. That says nothing about whether it deforms *well*.
//! This module poses the rig and measures what breaks.
//!
//! Four failure modes, each a real artifact a rigger looks for:
//!
//! - **Pinching** — a triangle collapses toward zero area as bones pull its
//!   vertices together. The classic candy-wrapper symptom.
//! - **Inversion** — a triangle's normal flips. The surface has turned inside
//!   out; worse than pinching because it renders as a hole.
//! - **Stretch** — an edge grows far beyond its rest length. Tearing.
//! - **Clipping** — two shells that were disjoint in the rest pose now
//!   overlap. On this corpus that is *the* risk: 374 rigid shells rotating
//!   about a chain will drive into each other long before any single shell
//!   deforms badly.
//!
//! Python builds the pose matrices — a handful of 4x4s, where performance is
//! irrelevant — and this does the per-vertex and per-triangle work.

/// A triangle below this fraction of its rest area counts as pinched.
const COLLAPSE_RATIO: f64 = 0.25;
/// An edge above this multiple of its rest length counts as torn.
const STRETCH_LIMIT: f64 = 2.0;
/// Overlap beyond this fraction of the smaller part's volume is real
/// interpenetration rather than two parts legitimately closing on each other.
const DEEP_OVERLAP: f64 = 0.5;

pub struct DeformInput {
    pub positions: Vec<[f64; 3]>,
    pub indices: Vec<u32>,
    pub joint_ids: Vec<u16>,
    pub weights: Vec<f32>,
    /// Per pose, per joint: the 4x4 skinning matrix, column-major.
    pub poses: Vec<Vec<[f64; 16]>>,
    pub labels: Vec<u32>,
    pub shell_count: usize,
}

pub struct PoseReport {
    pub collapsed: usize,
    pub inverted: usize,
    pub torn: usize,
    pub max_stretch: f64,
    pub mean_stretch: f64,
    pub max_displacement: f64,
    /// Pairs whose boxes newly touch — includes legitimate articulation.
    pub clipping_pairs: usize,
    /// Pairs genuinely interpenetrating. This is the defect count.
    pub deep_clipping: usize,
}

fn apply(m: &[f64; 16], p: &[f64; 3]) -> [f64; 3] {
    [
        m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
        m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
        m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14],
    ]
}

fn cross(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
}

fn sub(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

fn dot(a: [f64; 3], b: [f64; 3]) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

fn norm(a: [f64; 3]) -> f64 {
    dot(a, a).sqrt()
}

/// Linear blend skinning. Packet Beta names LBS vs dual-quaternion as the
/// real axis of choice; with at most two influences and no twist in the rest
/// pose, LBS is what the solver's output actually implies, so it is what the
/// probe measures. When a twisting joint appears, this is the function that
/// has to grow a second implementation.
fn skin(input: &DeformInput, pose: &[[f64; 16]]) -> Vec<[f64; 3]> {
    let mut out = Vec::with_capacity(input.positions.len());
    for (v, p) in input.positions.iter().enumerate() {
        let mut acc = [0f64; 3];
        for k in 0..4 {
            let w = input.weights[4 * v + k] as f64;
            if w == 0.0 {
                continue;
            }
            let j = input.joint_ids[4 * v + k] as usize;
            if j >= pose.len() {
                continue;
            }
            let moved = apply(&pose[j], p);
            acc[0] += w * moved[0];
            acc[1] += w * moved[1];
            acc[2] += w * moved[2];
        }
        out.push(acc);
    }
    out
}

fn shell_boxes(positions: &[[f64; 3]], labels: &[u32], shell_count: usize)
    -> Vec<([f64; 3], [f64; 3])> {
    let mut boxes = vec![([f64::INFINITY; 3], [f64::NEG_INFINITY; 3]); shell_count];
    for (v, p) in positions.iter().enumerate() {
        let s = labels[v] as usize;
        for i in 0..3 {
            boxes[s].0[i] = boxes[s].0[i].min(p[i]);
            boxes[s].1[i] = boxes[s].1[i].max(p[i]);
        }
    }
    boxes
}

fn overlaps(a: &([f64; 3], [f64; 3]), b: &([f64; 3], [f64; 3])) -> bool {
    (0..3).all(|i| a.0[i] <= b.1[i] && b.0[i] <= a.1[i])
}

fn overlap_volume(a: &([f64; 3], [f64; 3]), b: &([f64; 3], [f64; 3])) -> f64 {
    let mut v = 1.0;
    for i in 0..3 {
        let d = a.1[i].min(b.1[i]) - a.0[i].max(b.0[i]);
        if d <= 0.0 {
            return 0.0;
        }
        v *= d;
    }
    v
}

fn box_volume(a: &([f64; 3], [f64; 3])) -> f64 {
    (0..3).map(|i| (a.1[i] - a.0[i]).max(0.0)).product()
}

/// Shells that were apart in the rest pose and interpenetrate now, **graded
/// by how deeply**.
///
/// Counting any new box overlap was the first version of this and it was
/// wrong in a way worth recording: on a bending articulated model, adjacent
/// parts legitimately approach each other as a joint closes. Measured on
/// gasket at 45 degrees, 341 pairs "collided" but the median overlap was 8%
/// of the smaller part's volume — that is articulation, not clipping. Only
/// 29 pairs exceeded 50%.
///
/// So the number that means something is the deep count. `touching` is kept
/// because it is a useful denominator, not because it is a defect count.
fn clipping(rest: &[[f64; 3]], posed: &[[f64; 3]], labels: &[u32], shell_count: usize)
    -> (usize, usize) {
    if shell_count < 2 {
        return (0, 0);
    }
    let rest_boxes = shell_boxes(rest, labels, shell_count);
    let posed_boxes = shell_boxes(posed, labels, shell_count);
    let (mut touching, mut deep) = (0, 0);
    for a in 0..shell_count {
        for b in (a + 1)..shell_count {
            if !overlaps(&posed_boxes[a], &posed_boxes[b])
                || overlaps(&rest_boxes[a], &rest_boxes[b])
            {
                continue;
            }
            touching += 1;
            let smaller = box_volume(&posed_boxes[a]).min(box_volume(&posed_boxes[b]));
            if smaller > 0.0
                && overlap_volume(&posed_boxes[a], &posed_boxes[b]) / smaller > DEEP_OVERLAP
            {
                deep += 1;
            }
        }
    }
    (touching, deep)
}

pub fn probe(input: &DeformInput) -> Vec<PoseReport> {
    let rest = &input.positions;
    let mut reports = Vec::new();

    for pose in &input.poses {
        let posed = skin(input, pose);

        let (mut collapsed, mut inverted, mut torn) = (0usize, 0usize, 0usize);
        let (mut max_stretch, mut stretch_sum) = (0f64, 0f64);
        let mut edges = 0usize;

        for tri in input.indices.chunks_exact(3) {
            let (a, b, c) = (tri[0] as usize, tri[1] as usize, tri[2] as usize);
            if a >= rest.len() || b >= rest.len() || c >= rest.len() {
                continue;
            }
            let nr = cross(sub(rest[b], rest[a]), sub(rest[c], rest[a]));
            let np = cross(sub(posed[b], posed[a]), sub(posed[c], posed[a]));
            let (ar, ap) = (norm(nr), norm(np));

            if ar > 0.0 {
                if ap / ar < COLLAPSE_RATIO {
                    collapsed += 1;
                }
                if dot(nr, np) < 0.0 {
                    inverted += 1;
                }
            }

            for (x, y) in [(a, b), (b, c), (c, a)] {
                let lr = norm(sub(rest[y], rest[x]));
                if lr <= 0.0 {
                    continue;
                }
                let ratio = norm(sub(posed[y], posed[x])) / lr;
                if ratio > STRETCH_LIMIT {
                    torn += 1;
                }
                max_stretch = max_stretch.max(ratio);
                stretch_sum += ratio;
                edges += 1;
            }
        }

        let mut max_displacement = 0f64;
        for v in 0..rest.len() {
            max_displacement = max_displacement.max(norm(sub(posed[v], rest[v])));
        }

        let clip = clipping(rest, &posed, &input.labels, input.shell_count);
        reports.push(PoseReport {
            collapsed,
            inverted,
            torn,
            max_stretch,
            mean_stretch: if edges > 0 { stretch_sum / edges as f64 } else { 0.0 },
            max_displacement,
            clipping_pairs: clip.0,
            deep_clipping: clip.1,
        });
    }

    reports
}
