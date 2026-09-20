# PSA-03A operational definition

For this apparatus, self-application means:

1. The target supplied to the operative lift is generated from the running
   `tools.xoseac_lift.lift` module, not hand-authored as an arbitrary
   XOSEAC-shaped value.
2. The target carries the SHA-256 digest of that live implementation and a
   structural description derived from the operative mutation and trace
   machinery. `is_self_representation` must verify both.
3. The operative lift is invoked on that verified target.
4. A legal change to the self-representation changes an observable result of
   a later execution that runs using the changed representation.

This definition establishes literal self-application as an executable
relationship between the implementation, its generated representation, and a
later run. It does not establish improvement, productivity, or any claim
about Productive Self-Application.
