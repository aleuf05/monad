# Minimal `M^up` apparatus report

## Representation boundary

`Inst(M)` is a JSON-shaped mapping with exactly six keys: `x`, `o`, `s`,
`e`, `a`, and `c`. Each key maps to a typed object. The boundary parser
`instance_from_dict` is the only supported entry into the internal model;
it rejects missing/extra keys, wrong shapes, empty identifiers, duplicate
members, malformed edges, and cross-component references that do not resolve.

Internally, `XOSEACInstance` is immutable and contains `X`, `O`, `S`, `E`,
`A`, and `C` records. `WellFormedInst` is implemented by `validate_instance`:
all E endpoints must be in S, the initial state must be in S, terminal states
must be in S, and E must not contain duplicates.

## Lifted types and mutations

`Lifted[T]` carries a typed immutable value plus its source component. The
aliases `XUp`, `OUp`, `SUp`, `EUp`, `AUp`, and `CUp` are the six lifted types
used by `LiftedInstance`. `M^up` currently accepts exactly two typed
mutations: `AddState` changes S and `AddEdge` changes E. The other four lifted
components are carried through unchanged.

`apply_lift` validates the input, applies exactly one mutation, constructs the
successor, validates it again, and returns the preserved `M` plus either `M'`
or a rejection with no successor.

## Provenance

Every result includes an ordered trace containing the accepted boundary and
before digest, typed request, mutation event, successor validation and after
digest, and the changed component. Rejections retain the boundary/request
events and append the exact invariant failure. Canonical JSON plus SHA-256
digests make the before/after states reconstructable and tamper-evident; the
full state is still available through `to_dict()`.

## Formalism strengthened or interpreted

1. XOSEAC was not previously executable as a schema, so each letter was
   given a minimal concrete type: X identity, O labels, S state names, E
   labelled directed edges, A action names, and C initial/terminal state
   constraints.
2. `WellFormedInst` was made explicit as both shape validation and
   cross-component referential integrity. In particular, E cannot mention a
   state that S does not contain.
3. “Typed modification” was interpreted as a closed mutation sum with one
   operation for S and one for E. No generic dictionary patch is accepted.
4. “Complete provenance” was interpreted as ordered causal events plus full
before/after canonical digests and reconstructable before/after states. No
   productivity, optimization, or self-application claim is made.

## Audit findings

The executable behavior is slightly narrower than the prose above in two
places:

1. Top-level component keys are exact, but nested component mappings are not
   exact-key validated. For example, an extra key inside `s` is ignored. The
   accepted boundary is therefore strict about the six components and their
   required fields, not closed over every nested mapping key.
2. `XUp` through `CUp` are Python generic aliases over `Lifted[T]`; they give
   static type information but are not distinct runtime nominal classes.
   Runtime mutation dispatch is closed by `isinstance` checks for `AddState`
   and `AddEdge`, and unsupported mutation objects are rejected.

The post-successor validator is executable and was adversarially exercised:
if successor construction produces an E endpoint absent from S, the result is
rejected and no successor is emitted. The result preserves both the original
instance and the successor when accepted, while rejection preserves the
original instance and the rejection trace.
