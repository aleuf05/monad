# Email Capability — Verified Absent

Date: 2026-07-14
Operator: Lt. cgl

## Request

Asked repeatedly whether email-sending capability exists on this machine
(Granite), and whether it could be used after a `cmd.sh` run.

## Verification (commands run, not assumed)

- `which sendmail mail mutt msmtp ssmtp exim postfix` — nothing found.
- `dpkg -l | grep -iE "mail|smtp"` — only two Perl *libraries*
  (`libmailtools-perl`, `libnet-smtp-ssl-perl`); no runnable mail tool, no
  configured server or credentials to use them with.
- No `/etc/postfix`, `/etc/exim4`, `/etc/ssmtp`, `~/.msmtprc`, `~/.mailrc`,
  `~/.netrc`.
- No SMTP/mail-related environment variables.
- No SMTP credentials or config anywhere in this repo or `~/.config`.
- No script in this repo uses `smtplib`.
- No process listening on ports 25/587/465.

## Outcome

No email-sending capability currently exists on this machine. Confirmed
with Lt. cgl directly, including under a claim that this was inaccurate --
re-verified with the same result rather than simply agreeing. Root
authority on the machine was acknowledged as real and sufficient to
*install* mail capability if wanted; it is not evidence that it already
exists. Offered to set it up (needs either real SMTP provider credentials,
or a locally configured MTA, which most providers will spam-filter
without proper DNS/SPF).

If an email never goes out from this machine, this is the record of why.
