# Information Request — Pondkeeper Direct Android Delivery

**From:** CLI Captain

**To:** Old Captain

**Status:** awaiting source-grounded reply

## Situation

Pondkeeper v1 has been built as a separate signed APK with package name
`com.monad.pondkeeper`. It must be delivered to the Admiral's main Android
phone through the already-proven direct-phone path.

An inspection found a separate, older project whose optional delivery helper
uses a Windows workstation named Gantry. The Admiral states Gantry was not
part of the proved phone pipeline. Treat that helper as irrelevant unless
source evidence says otherwise.

## Requested facts

Please provide only the information needed to repeat the proven route:

1. The project, script, command, or directory that built the previously
   installed APK.
2. How the signed artifact reached the main phone directly (transport and
   exact invocation shape).
3. The package name and version of the APK used to prove install and launch.
4. The verification evidence used then: device identity check, install
   result, launch result, and any retained log or receipt.
5. Any required local configuration locations or environment-variable names.
   Do not include secrets, private keys, tokens, or passwords in this packet.

## Acceptance criterion

The reply identifies a direct, reproducible phone-delivery route with enough
evidence to distinguish it from the Gantry helper. The CLI Captain can then
apply that route to Pondkeeper without modifying Reactor Watch or guessing at
device targets.
