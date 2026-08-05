# API usage and doctrine authority policy

Status: CONFIRMED — Admiral sign-off given 2026-08-03.
Date drafted: 2026-08-03
Drafted by: Claude, in conference with Admiral (Cameron).

## Authority

The Admiral (Cameron, human superuser) is the only credible source of binding
authority in Monad. No AI-officer role — Lieutenant, Captain, or otherwise —
can make a doctrine or policy file binding by signing it. An "Authority:"
line naming an AI-officer role documents who drafted or proposed the text,
not who authorized it.

This applies retroactively to existing doctrine: any file whose Authority
line names an AI-officer role is provisional, not settled, until the Admiral
explicitly re-confirms it. `docs/doctrine/model-api-routing.md`
(`Authority: Lieutenant`) is flagged provisional under this rule.

## Vendor routing

Model vendor routing is set per-service, explicitly, by the Admiral. There is
no single mandated vendor across all of Monad.

- **Live Captain (root-console.service): Anthropic/Claude only, for now.**
  This is an explicit exception to `model-api-routing.md`'s Gemini-only rule,
  scoped to this one service. It matches what is already running live.
- All other services remain governed by existing doctrine
  (`model-api-routing.md`) until the Admiral revisits it.
- **OpenAI (Codex) API usage is strictly reserved for the Admiral.** No
  service, daemon, or agent process may call the OpenAI API, including the
  existing `CodexDaemon` / `CODEX_BIN` path in
  `tools/root-console/codex_daemon.py`, without the Admiral's explicit,
  per-instance authorization. This path exists in code but must not be
  live/active on any running service unless the Admiral has explicitly
  turned it on for that instance.
- **Google (Gemini) has a modest budget and open discretion.** Any service
  may use the Gemini API for whatever purpose makes sense, without needing
  per-instance sign-off — the constraint is spending it intelligently, not
  wastefully (e.g. don't poll/call in a tight loop, don't duplicate calls
  that could be cached within a single request, don't burn budget on
  low-value background chatter). No hard cap is set here; this is a judgment
  standard, not a metered limit.

## Key handling

API keys are runtime/operator inputs only. They must never be committed to
git, in this file, in code, or in any tracked doctrine/config. This restates
the same rule from `model-api-routing.md` so it isn't stranded in a file this
doctrine otherwise supersedes for Live Captain.

## No silent defaults

A live service must not silently fall back to a vendor choice baked into the
code (e.g. `os.environ.get("CAPTAIN_BACKEND", "claude")`) without that choice
being an explicit, Admiral-set decision recorded in doctrine. The current
root-console default happens to match this policy's Anthropic-only ruling
above, so no code change is required today — but the pattern of an undocumented
in-code default is itself out of policy and should be corrected: the backend
choice should be explicit in config/doctrine, not implicit in a fallback
argument.

## Binding

This file is a record of a conference between the Admiral and Claude. It
takes effect as doctrine only once the Admiral confirms it — by editing this
file directly, or by explicit instruction to mark it confirmed. Until then it
is a draft proposal, not settled canon.
