# Log — Human Secret Custody and Recovery

- **Recorded:** 2026-07-28
- **Status:** Admiral-directed operational record; contains no secret material
- **Scope:** Passwords, API keys, recovery codes, tokens, private keys, and
  equivalent user credentials

## Governing boundary

**Human authority:** The human creates, retains, enters, recovers, rotates, and
revokes user secrets.

**Human report:** An offline, human-controlled recovery note exists. Its
contents and physical location are deliberately excluded from this archive and
remain unverified by the Captain.

**Captain duty:** The Captain may design and verify the recovery procedure,
but must not request, receive, repeat, archive, commit, transmit, or claim
custody of the secret itself.

This boundary applies equally to every user's secrets. No Captain role,
private-conference declaration, implementation task, or operational urgency
converts a credential into archive material.

## Standard recovery procedure

1. **Identify the account and recovery channel** without stating the secret.
2. **Use the provider's human-facing recovery flow** on a trusted human device.
3. **Have the human choose or generate the replacement secret locally.**
4. **Enter the secret directly into the protected provider or runtime prompt.**
5. **Store it only in the human's approved password manager or protected
   credential store.**
6. **Invalidate prior sessions, tokens, or recovery material when the provider
   supports it.**
7. **Verify access through a minimal human-operated login test.**
8. **Record only:** account purpose, recovery date, responsible human,
   verification result, and next rotation/review condition.

## Prohibited log content

Do not record:

- passwords or passphrases;
- hashes, salts, or password verifiers;
- recovery codes or security-question answers;
- API keys, session tokens, cookies, or private keys;
- screenshots or command output containing any of the above;
- hints that materially reduce the secret's search space.

## Failure handling

If recovery fails:

1. preserve the exact non-secret error;
2. stop repeated attempts before lockout or rate limiting;
3. confirm the correct provider, account identifier, and recovery channel;
4. escalate to the provider's official human support path;
5. rotate any credential that may have been exposed during the attempt.

## Compact rule

> The human protects the secret. The Captain protects the procedure and the
> evidence that recovery succeeded.
