# Local addition: grants /usr/bin/bwrap permission to create unprivileged
# user namespaces, which Ubuntu 24.04 blocks by default for unconfined
# processes (kernel.apparmor_restrict_unprivileged_userns=1). Scoped to
# this one binary only -- the system-wide sysctl is left untouched.
# bwrap is Codex's own internal sandboxing tool; without this, Codex's
# "workspace-write" sandbox mode fails at startup ("bwrap: loopback:
# Operation not permitted") for any caller, confirmed live in Chat
# Captain's master-mode capability (tools/chat-captain/codex_provider.py).
abi <abi/4.0>,
include <tunables/global>

profile bwrap-codex /usr/bin/bwrap flags=(unconfined) {
  userns,
}
