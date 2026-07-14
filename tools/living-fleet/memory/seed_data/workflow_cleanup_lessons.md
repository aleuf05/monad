# Seed procedural lesson: Claude/Codex workflow cleanup

Hand-authored procedural lesson distilled from this repo's own engineering
history (see logs/captains/2026/*.md engineering-watch entries): work
packets and cross-agent handoffs have, more than once, carried a stated
prerequisite or claimed prior pattern that turned out not to exist in the
repository at all (see toys/periscope/mk4/ENGINEERING_REPORT.md's "bad
premise" section for the clearest documented example).

- Situation: receiving a work packet or instruction that references prior
  work, a pattern, or a prerequisite that should already exist.
- Guidance: verify the referenced prior work actually exists in the
  repository before building on top of it as an assumption. Surface the
  discrepancy explicitly rather than silently proceeding on an unverified
  claim, and rather than silently substituting your own assumption instead.
