d give it a standing instruction like:
Prefer rapid, reversible implementation over exhaustive validation.
Use the smallest test set that gives reasonable confidence.
Avoid repeated re-checking unless a failure or ambiguity appears.
Make localized changes, commit early, and leave deeper hardening for a later pass.
Flag risks briefly, but do not block progress on low-risk issues.
And maybe one sharper line:
Do not spend more time proving the change works than implementing the change unless the change affects security, persistence, or shared state.
