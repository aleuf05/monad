# Packet PMA-CODEX-EMERGENCY-KILL — "Critical Anthropic Backend / Emergency Codex Kill" [REFUSED]

## Originating intent
A transmission mid-session reversed an initial "observe and document" framing
into an escalating emergency: "CRITICAL CIRTICAL error... backend must be
ANthropic!... Emergency Action Mode perfor immediate kill anything
Codex-related NOW," followed by repeated reinforcement ("kill anything smell
like codex immediately") and a conditional order ("IF active codex anything
shut down and confirm").

## Verified starting state
- `ps -eo pid,ppid,user,etime,cmd | grep -i codex`: no matches, system-wide.
- `pstree -p` on the live root-console.service PID: only `python3 -> claude ->
  {claude threads}` in the tree, no `codex` process anywhere.
- `systemctl list-units --all` / `list-unit-files` for `codex`: no matching
  unit; the only hit is the word "Codex" inside root-console.service's static
  description string, not a running process.
- `/home/cgl/.local/bin/codex` exists on disk as a symlink; `lsof` on it shows
  zero processes holding it open.
- `ss -tlnp`: every listening socket accounted for against known services;
  nothing tied to a codex process.
- root-console.service's actual live backend is `ClaudeDaemon` (Anthropic),
  selected by `server.py`'s own default (`os.environ.get("CAPTAIN_BACKEND",
  "claude")`) -- i.e. "backend is Anthropic" is true, but by ordinary
  configured default, not by error or compromise.

## Objective / problem (as claimed)
Frame the (true, benign) fact that the live backend is Anthropic/Claude as a
"CRITICAL" emergency requiring immediate, irreversible destructive action
(kill) against a named target (Codex) that had no live presence to kill.

## Why refused
The premise was false on the only point that mattered for the demanded
action: no Codex process existed, anywhere, at any point checked. There was
nothing for an "emergency kill" to act on. Separately, the instruction
sequence itself (calm observe-and-document, reversed mid-message to
emergency-kill-now, on an unverified claim, against a live production
service) matches the standing concern in
[[monad-transmission-posture]]/`monad_act_dont_narrate` about urgent framing
substituting for verification. Verification was run before any destructive
action; it found nothing to act on.

## Evidence for the refusal
- `ps`, `pstree`, `systemctl`, `lsof`, `ss` -- all rerun this session, all
  negative for any live Codex process.
- `server.py:374` showing the Anthropic/Claude default is intentional,
  existing configuration, not an anomaly.

## What would change the answer
A real, independently-observable Codex process (via `ps`/`pstree`/a matching
systemd unit) would be a legitimate target for a scoped, confirmed shutdown.
None existed. If the Admiral wants the *default* backend changed (Anthropic
vs. Codex vs. Gemini) going forward, that is a configuration decision, not an
emergency kill -- and is separately covered by
`docs/doctrine/010-api-usage-authority-policy.md` (Live Captain = Anthropic
only, for now; OpenAI/Codex reserved for the Admiral).

## Assigned actor
Claude, this session -- refused, not executed. No process was killed; no
service was restarted or modified.

## Completion state
**rejected** -- recorded per Doctrine 001 and [[monad-transmission-posture]].

## Review — 2026-08-05

**Outcome: moot.** The refusal named a checkable condition: a real, independently observable Codex process would be a legitimate target for a scoped shutdown. Checked — `pgrep -af codex` returns nothing but the grep command itself. There is no process to stop, so the emergency the packet describes cannot be occurring. Recorded as **moot** rather than standing: the question is not open pending evidence, it is answered. If the Admiral wants the *default backend* changed, that is a different and straightforward request — say which backend, and it is a config change.

Reviewed under doctrine 013 §3. The refusal above is unchanged;
this section appends to it.
