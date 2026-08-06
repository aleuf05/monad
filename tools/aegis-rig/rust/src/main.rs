//! Aegis rigging core — the maths, in Rust.
//!
//! Admiral's ruling, 2026-08-05: Rust for the maths, Python only where
//! performance is not critical. This binary is the whole hot path — union-find
//! over the index buffer, skeleton fitting, and per-shell weight solving.
//! Python keeps glTF parsing and writing, which is I/O-shaped and measured in
//! milliseconds regardless of language.
//!
//! Protocol is a length-prefixed binary pipe rather than a JSON one, because
//! handing 4.45M vertices across as JSON text would put the cost back into
//! the parsing we came here to avoid.
//!
//! stdin:  "ARIG" | u32 version | u32 vertices | u32 indices | u32 joints
//!         | f32 adjacency_factor
//!         | f32[vertices*3] positions | u32[indices] index buffer
//! stdout: u32 json_len | json | u16[vertices*4] joint ids | f32[vertices*4] weights

mod deform;

use std::io::{self, Read, Write};

const MAGIC: &[u8; 4] = b"ARIG";
const DEFORM_MAGIC: &[u8; 4] = b"ADEF";
const VERSION: u32 = 1;

/// A shell shorter than this many bone spans is bound rigidly to one joint.
/// Mirrors RIGID_SPAN_FACTOR in solver.py; the two implementations are held
/// to the same number by test_parity.py.
const RIGID_SPAN_FACTOR: f64 = 1.0;

struct Input {
    positions: Vec<[f64; 3]>,
    indices: Vec<u32>,
    joint_count: usize,
    /// Shell-grouping radius, as a fraction of bone_span. 0 disables
    /// grouping and reproduces the v0.1 per-shell solver exactly.
    adjacency_factor: f64,
    /// Spine axis chosen by the caller, or u32::MAX to pick by extent.
    /// Python decides this by mass distribution; the Rust core used to pick
    /// by bounding-box extent regardless, which threaded a robot's spine
    /// through its shoulders and ignored the caller entirely.
    forced_axis: Option<usize>,
}

fn parse_input(raw: &[u8]) -> io::Result<Input> {
    if raw.len() < 28 || &raw[0..4] != MAGIC {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "bad magic"));
    }
    let u32_at = |o: usize| -> u32 {
        u32::from_le_bytes([raw[o], raw[o + 1], raw[o + 2], raw[o + 3]])
    };
    if u32_at(4) != VERSION {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "bad version"));
    }
    let vertex_count = u32_at(8) as usize;
    let index_count = u32_at(12) as usize;
    let joint_count = u32_at(16) as usize;
    let adjacency_factor = f32::from_le_bytes([raw[20], raw[21], raw[22], raw[23]]) as f64;
    let axis_field = u32_at(24);
    let forced_axis = if axis_field < 3 { Some(axis_field as usize) } else { None };

    let mut offset = 28;
    let mut positions = Vec::with_capacity(vertex_count);
    for _ in 0..vertex_count {
        let mut p = [0f64; 3];
        for slot in p.iter_mut() {
            *slot = f32::from_le_bytes([
                raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3],
            ]) as f64;
            offset += 4;
        }
        positions.push(p);
    }
    let mut indices = Vec::with_capacity(index_count);
    for _ in 0..index_count {
        indices.push(u32::from_le_bytes([
            raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3],
        ]));
        offset += 4;
    }
    Ok(Input { positions, indices, joint_count, adjacency_factor, forced_axis })
}

/// Union-find with path halving and union by size. Same shells the Python
/// inspector finds, an order of magnitude faster on a real corpus.
fn connected_components(indices: &[u32], vertex_count: usize) -> (Vec<u32>, usize) {
    let mut parent: Vec<u32> = (0..vertex_count as u32).collect();
    let mut size: Vec<u32> = vec![1; vertex_count];

    fn find(parent: &mut [u32], mut x: u32) -> u32 {
        while parent[x as usize] != x {
            let grand = parent[parent[x as usize] as usize];
            parent[x as usize] = grand; // path halving
            x = grand;
        }
        x
    }

    let union = |parent: &mut Vec<u32>, size: &mut Vec<u32>, a: u32, b: u32| {
        let (mut ra, mut rb) = (find(parent, a), find(parent, b));
        if ra == rb {
            return;
        }
        if size[ra as usize] < size[rb as usize] {
            std::mem::swap(&mut ra, &mut rb);
        }
        parent[rb as usize] = ra;
        size[ra as usize] += size[rb as usize];
    };

    for tri in indices.chunks_exact(3) {
        union(&mut parent, &mut size, tri[0], tri[1]);
        union(&mut parent, &mut size, tri[0], tri[2]);
    }

    // Dense relabelling, in first-seen order, so labels match Python's.
    let mut dense = vec![u32::MAX; vertex_count];
    let mut labels = vec![0u32; vertex_count];
    let mut next = 0u32;
    for v in 0..vertex_count {
        let root = find(&mut parent, v as u32) as usize;
        if dense[root] == u32::MAX {
            dense[root] = next;
            next += 1;
        }
        labels[v] = dense[root];
    }
    (labels, next as usize)
}

struct Skeleton {
    axis: usize,
    joints: Vec<[f64; 3]>,
    bone_span: f64,
    axis_min: f64,
    axis_max: f64,
}

fn solve_skeleton(positions: &[[f64; 3]], joint_count: usize,
                  forced_axis: Option<usize>) -> Result<Skeleton, String> {
    if joint_count < 2 {
        return Err("a chain needs at least two joints".into());
    }
    let mut lo = [f64::INFINITY; 3];
    let mut hi = [f64::NEG_INFINITY; 3];
    for p in positions {
        for i in 0..3 {
            lo[i] = lo[i].min(p[i]);
            hi[i] = hi[i].max(p[i]);
        }
    }
    let extent = [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]];
    let mut axis = 0;
    for i in 1..3 {
        if extent[i] > extent[axis] {
            axis = i;
        }
    }
    if let Some(forced) = forced_axis {
        axis = forced;   // caller measured mass; extent is only the fallback
    }
    if extent[axis] <= 0.0 {
        return Err("degenerate geometry — zero extent on every axis".into());
    }

    let step = extent[axis] / joint_count as f64;
    let mut sums = vec![[0f64; 3]; joint_count];
    let mut counts = vec![0usize; joint_count];
    for p in positions {
        let mut slot = ((p[axis] - lo[axis]) / step) as isize;
        slot = slot.clamp(0, joint_count as isize - 1);
        let slot = slot as usize;
        for i in 0..3 {
            sums[slot][i] += p[i];
        }
        counts[slot] += 1;
    }

    let mut joints = Vec::with_capacity(joint_count);
    for j in 0..joint_count {
        let centre = lo[axis] + step * (j as f64 + 0.5);
        let mut point = if counts[j] > 0 {
            let n = counts[j] as f64;
            [sums[j][0] / n, sums[j][1] / n, sums[j][2] / n]
        } else {
            [(lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, (lo[2] + hi[2]) / 2.0]
        };
        point[axis] = centre;
        joints.push(point);
    }

    Ok(Skeleton { axis, joints, bone_span: step, axis_min: lo[axis], axis_max: hi[axis] })
}

/// Axis-aligned bounds per shell.
fn shell_aabbs(positions: &[[f64; 3]], labels: &[u32], shell_count: usize)
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

/// Merge shells that sit within `epsilon` of each other into rigid groups.
///
/// The collision the deformation probe measures comes from two shells that
/// physically touch being bound to *different* joints and then rotating
/// apart. Grouping neighbours and binding the group as a unit removes the
/// relative motion, which removes the interpenetration at its source rather
/// than resolving it afterwards.
///
/// O(S^2) box tests. 4,676 shells is ~11M comparisons of three floats, which
/// is nothing next to the per-vertex work already happening.
fn group_shells(boxes: &[([f64; 3], [f64; 3])], epsilon: f64) -> (Vec<u32>, usize) {
    let n = boxes.len();
    let mut parent: Vec<u32> = (0..n as u32).collect();

    fn find(parent: &mut [u32], mut x: u32) -> u32 {
        while parent[x as usize] != x {
            let grand = parent[parent[x as usize] as usize];
            parent[x as usize] = grand;
            x = grand;
        }
        x
    }

    let near = |a: &([f64; 3], [f64; 3]), b: &([f64; 3], [f64; 3])| -> bool {
        (0..3).all(|i| a.0[i] - epsilon <= b.1[i] && b.0[i] - epsilon <= a.1[i])
    };

    for a in 0..n {
        for b in (a + 1)..n {
            if near(&boxes[a], &boxes[b]) {
                let (ra, rb) = (find(&mut parent, a as u32), find(&mut parent, b as u32));
                if ra != rb {
                    parent[rb as usize] = ra;
                }
            }
        }
    }

    let mut dense = vec![u32::MAX; n];
    let mut group_of = vec![0u32; n];
    let mut next = 0u32;
    for s in 0..n {
        let root = find(&mut parent, s as u32) as usize;
        if dense[root] == u32::MAX {
            dense[root] = next;
            next += 1;
        }
        group_of[s] = dense[root];
    }
    (group_of, next as usize)
}

struct Skinning {
    joint_ids: Vec<u16>,
    weights: Vec<f32>,
    group_count: usize,
    rigid_shells: usize,
    blended_shells: usize,
    rigid_vertices: usize,
    blended_vertices: usize,
    max_weight_error: f64,
    unweighted: usize,
}

fn solve_weights(
    positions: &[[f64; 3]],
    labels: &[u32],
    shell_count: usize,
    skeleton: &Skeleton,
    adjacency_factor: f64,
) -> Skinning {
    let axis = skeleton.axis;
    let joint_axis: Vec<f64> = skeleton.joints.iter().map(|j| j[axis]).collect();
    let rigid_threshold = skeleton.bone_span * RIGID_SPAN_FACTOR;

    // Group touching shells first. Binding a *group* as a unit is what stops
    // neighbouring parts being handed to different joints and swung into each
    // other. A factor of 0 disables grouping and reproduces the v0.1 solver
    // exactly, which is how the parity and regression tests pin the old
    // behaviour while the new one is tuned.
    let (group_of_shell, group_count) = if adjacency_factor > 0.0 {
        let boxes = shell_aabbs(positions, labels, shell_count);
        group_shells(&boxes, skeleton.bone_span * adjacency_factor)
    } else {
        ((0..shell_count as u32).collect(), shell_count)
    };
    let group_of_vertex = |v: usize| group_of_shell[labels[v] as usize] as usize;

    // Bucket vertices by group in one pass rather than a map of vectors.
    let mut lo = vec![f64::INFINITY; group_count];
    let mut hi = vec![f64::NEG_INFINITY; group_count];
    let mut sum = vec![0f64; group_count];
    let mut count = vec![0usize; group_count];
    for (v, p) in positions.iter().enumerate() {
        let s = group_of_vertex(v);
        let t = p[axis];
        lo[s] = lo[s].min(t);
        hi[s] = hi[s].max(t);
        sum[s] += t;
        count[s] += 1;
    }
    let shell_count = group_count;

    // Per shell: rigid (one bone, weight 1.0) or blended. This is the
    // anti-bleed rule — a shell too short to contain a blend never gets one.
    let mut shell_rigid = vec![false; shell_count];
    let mut shell_joint = vec![0u16; shell_count];
    let (mut rigid_shells, mut blended_shells) = (0, 0);
    let (mut rigid_vertices, mut blended_vertices) = (0, 0);
    for s in 0..shell_count {
        if hi[s] - lo[s] < rigid_threshold {
            let centre = sum[s] / count[s] as f64;
            let mut best = 0usize;
            let mut best_d = f64::INFINITY;
            for (j, a) in joint_axis.iter().enumerate() {
                let d = (a - centre).abs();
                if d < best_d {
                    best_d = d;
                    best = j;
                }
            }
            shell_rigid[s] = true;
            shell_joint[s] = best as u16;
            rigid_shells += 1;
            rigid_vertices += count[s];
        } else {
            blended_shells += 1;
            blended_vertices += count[s];
        }
    }

    let n = positions.len();
    let mut joint_ids = vec![0u16; n * 4];
    let mut weights = vec![0f32; n * 4];
    for (v, p) in positions.iter().enumerate() {
        let s = group_of_vertex(v);
        if shell_rigid[s] {
            joint_ids[4 * v] = shell_joint[s];
            weights[4 * v] = 1.0;
            continue;
        }
        let t = p[axis];
        let mut upper = 0usize;
        while upper < joint_axis.len() && joint_axis[upper] < t {
            upper += 1;
        }
        if upper == 0 {
            joint_ids[4 * v] = 0;
            weights[4 * v] = 1.0;
            continue;
        }
        if upper >= joint_axis.len() {
            joint_ids[4 * v] = (joint_axis.len() - 1) as u16;
            weights[4 * v] = 1.0;
            continue;
        }
        let (a, b) = (upper - 1, upper);
        let gap = joint_axis[b] - joint_axis[a];
        let frac = if gap <= 0.0 { 0.0 } else { ((t - joint_axis[a]) / gap).clamp(0.0, 1.0) };
        joint_ids[4 * v] = a as u16;
        joint_ids[4 * v + 1] = b as u16;
        let total = (1.0 - frac) + frac;
        weights[4 * v] = ((1.0 - frac) / total) as f32;
        weights[4 * v + 1] = (frac / total) as f32;
    }

    let mut max_error = 0f64;
    let mut unweighted = 0usize;
    for v in 0..n {
        let total = weights[4 * v] as f64
            + weights[4 * v + 1] as f64
            + weights[4 * v + 2] as f64
            + weights[4 * v + 3] as f64;
        if total == 0.0 {
            unweighted += 1;
        }
        max_error = max_error.max((total - 1.0).abs());
    }

    Skinning {
        joint_ids,
        weights,
        group_count,
        rigid_shells,
        blended_shells,
        rigid_vertices,
        blended_vertices,
        max_weight_error: max_error,
        unweighted,
    }
}

fn emit(json: String, joint_ids: &[u16], weights: &[f32]) -> io::Result<()> {
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());
    out.write_all(&(json.len() as u32).to_le_bytes())?;
    out.write_all(json.as_bytes())?;
    for id in joint_ids {
        out.write_all(&id.to_le_bytes())?;
    }
    for w in weights {
        out.write_all(&w.to_le_bytes())?;
    }
    out.flush()
}

fn fail(message: &str) -> ! {
    let json = format!("{{\"ok\":false,\"error\":\"{}\"}}", message.replace('"', "'"));
    let _ = emit(json, &[], &[]);
    std::process::exit(1);
}

/// ADEF layout, after the 4-byte magic:
///   u32 version | u32 vertices | u32 indices | u32 joints | u32 poses
///   f32[v*3] rest positions | u32[i] index buffer
///   u16[v*4] joint ids | f32[v*4] weights
///   f32[poses*joints*16] skinning matrices, column-major
fn run_deform(raw: &[u8]) -> ! {
    let u32_at = |o: usize| u32::from_le_bytes([raw[o], raw[o + 1], raw[o + 2], raw[o + 3]]);
    if raw.len() < 24 || u32_at(4) != VERSION {
        fail("bad deform header");
    }
    let (vertices, index_count) = (u32_at(8) as usize, u32_at(12) as usize);
    let (joints, poses) = (u32_at(16) as usize, u32_at(20) as usize);

    let mut offset = 24;
    let mut positions = Vec::with_capacity(vertices);
    for _ in 0..vertices {
        let mut p = [0f64; 3];
        for slot in p.iter_mut() {
            *slot = f32::from_le_bytes([
                raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3],
            ]) as f64;
            offset += 4;
        }
        positions.push(p);
    }
    let mut indices = Vec::with_capacity(index_count);
    for _ in 0..index_count {
        indices.push(u32::from_le_bytes([
            raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3],
        ]));
        offset += 4;
    }
    let mut joint_ids = Vec::with_capacity(vertices * 4);
    for _ in 0..vertices * 4 {
        joint_ids.push(u16::from_le_bytes([raw[offset], raw[offset + 1]]));
        offset += 2;
    }
    let mut weights = Vec::with_capacity(vertices * 4);
    for _ in 0..vertices * 4 {
        weights.push(f32::from_le_bytes([
            raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3],
        ]));
        offset += 4;
    }
    let mut pose_mats = Vec::with_capacity(poses);
    for _ in 0..poses {
        let mut mats = Vec::with_capacity(joints);
        for _ in 0..joints {
            let mut m = [0f64; 16];
            for slot in m.iter_mut() {
                *slot = f32::from_le_bytes([
                    raw[offset], raw[offset + 1], raw[offset + 2], raw[offset + 3],
                ]) as f64;
                offset += 4;
            }
            mats.push(m);
        }
        pose_mats.push(mats);
    }

    let (labels, shell_count) = connected_components(&indices, vertices);
    let input = deform::DeformInput {
        positions, indices, joint_ids, weights, poses: pose_mats, labels, shell_count,
    };
    let reports = deform::probe(&input);

    let rows: Vec<String> = reports
        .iter()
        .map(|r| {
            format!(
                "{{\"collapsed\":{},\"inverted\":{},\"torn\":{},\"max_stretch\":{},\
\"mean_stretch\":{},\"max_displacement\":{},\"clipping_pairs\":{},\"deep_clipping\":{},\"hotspots\":[{}]}}",
                r.collapsed, r.inverted, r.torn, r.max_stretch,
                r.mean_stretch, r.max_displacement, r.clipping_pairs, r.deep_clipping,
                r.hotspots.iter()
                    .map(|h| format!("{{\"x\":{},\"y\":{},\"z\":{},\"joint\":{}}}",
                                     h.x, h.y, h.z, h.joint))
                    .collect::<Vec<_>>().join(",")
            )
        })
        .collect();
    let json = format!(
        "{{\"ok\":true,\"engine\":\"rust\",\"shells\":{},\"triangles\":{},\"poses\":[{}]}}",
        shell_count,
        input.indices.len() / 3,
        rows.join(",")
    );
    let _ = emit(json, &[], &[]);
    std::process::exit(0);
}

fn main() {
    let mut raw = Vec::new();
    if io::stdin().read_to_end(&mut raw).is_err() {
        fail("cannot read stdin");
    }
    if raw.len() >= 4 && &raw[0..4] == DEFORM_MAGIC {
        run_deform(&raw);
    }
    let input = match parse_input(&raw) {
        Ok(input) => input,
        Err(error) => fail(&error.to_string()),
    };
    if input.positions.is_empty() {
        fail("no vertices");
    }

    let (labels, shell_count) = connected_components(&input.indices, input.positions.len());
    let skeleton = match solve_skeleton(&input.positions, input.joint_count,
                                        input.forced_axis) {
        Ok(skeleton) => skeleton,
        Err(error) => fail(&error),
    };
    let skin = solve_weights(&input.positions, &labels, shell_count, &skeleton, input.adjacency_factor);

    let joints: Vec<String> = skeleton
        .joints
        .iter()
        .map(|j| format!("[{},{},{}]", j[0], j[1], j[2]))
        .collect();
    let json = format!(
        "{{\"ok\":true,\"engine\":\"rust\",\"axis\":{},\"axis_min\":{},\"axis_max\":{},\
\"bone_span\":{},\"joints\":[{}],\"shells\":{},\"groups\":{},\"rigid_shells\":{},\"blended_shells\":{},\
\"rigid_vertices\":{},\"blended_vertices\":{},\"max_weight_error\":{},\"unweighted_vertices\":{}}}",
        skeleton.axis,
        skeleton.axis_min,
        skeleton.axis_max,
        skeleton.bone_span,
        joints.join(","),
        shell_count,
        skin.group_count,
        skin.rigid_shells,
        skin.blended_shells,
        skin.rigid_vertices,
        skin.blended_vertices,
        skin.max_weight_error,
        skin.unweighted,
    );

    if let Err(error) = emit(json, &skin.joint_ids, &skin.weights) {
        eprintln!("aegis-rig-core: {error}");
        std::process::exit(1);
    }
}
