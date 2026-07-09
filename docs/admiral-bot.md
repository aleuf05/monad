# Admiral Bot

Admiral Bot is a draft-only public dispatch generator.

## Purpose

Admiral Bot transforms manually curated, public-safe log entries into reviewable public dispatch drafts.

It formalizes the public/private boundary by treating publication as a human decision, not an automated side effect.

## Source

The only source for Admiral Bot v0.1 is:

```text
logs/public-ready.log
```

Entries in this file must already be manually gated for public safety before Admiral Bot reads them.

## Output

Admiral Bot writes Markdown drafts to:

```text
outbox/drafts/YYYY-MM-DD.md
```

Draft files are review material. They are not public posts.

## Publication Doctrine

- Manual human approval only.
- Cameron must review and edit before anything becomes public.
- No direct posting.
- No scheduled posting.
- No background loop.
- No posting APIs.
- No credentials.
- Admiral Bot is Curator/Editor, not Publisher.

## Hard Exclusions

Public-ready entries must not include:

- health
- family
- money/substance details
- local IPs
- MAC addresses
- API keys
- private file paths
- private server configs
- raw stack traces
- household logistics
- unreviewed emotional/personal material

## Standing Doctrine

Admiral Bot may draft.

Admiral Bot may not publish.

Public-ready logs are manually gated.

Git is truth.

Human approval is required before public release.
