# Shared engineering task queue

Protocol: see [`AGENTS.md`](../../AGENTS.md) at the repo root. Non-privileged,
git-only tasks only — nothing requiring `sudo` (that stays in `cmd.sh` /
`commissioning-handoff.md`).

## WEB-IA-01: Monad web UX information-architecture sprint

Status: claimed:claude@2026-07-28T12:00:00Z

Full-site IA reorganization per Admiral's packet (chat-delivered, not filed
as a packets/ doc yet — will be recorded on completion). Touches: `web/index.html`,
new `web/command.html` / `observe.html` / `build.html` / `story.html`,
`web/assets/js/monad-nav.js`, and a breadcrumb-nav script tag added to all
existing `web/**/index.html` and top-level `web/*.html` pages. No backend/data
changes. If Codex needs to touch anything under `web/` before this closes,
check here first — ping rather than editing the same files concurrently.

