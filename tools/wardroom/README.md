# Wardroom Clerk

Append-only capture for formal meetings. It records classified events,
candidate canon, explicit rulings, actions, and adjournment; it never edits
doctrine or the Canon Register automatically.

```bash
python3 tools/wardroom/wardroom.py --ledger data/wardroom/MEETING.jsonl init \
  --meeting "Craft Role Grammar" --purpose "Resolve the role grammar" \
  --muster "Admiral · Captain · Master Chief"

python3 tools/wardroom/wardroom.py --ledger data/wardroom/MEETING.jsonl candidate \
  --id RG-01 --text "Candidate language" --scope "Temporary craft postures" \
  --explanation "States the durable rule being considered and why it belongs in the meeting."

python3 tools/wardroom/wardroom.py --ledger data/wardroom/MEETING.jsonl rule \
  --id RG-01 --ruling CANON --authority "Admiral Cameron Lampley" \
  --explanation "Explains what changed and why the authority applies."

python3 tools/wardroom/wardroom.py --ledger data/wardroom/MEETING.jsonl readback
```

The JSONL ledger is the append-only event source. The Markdown meeting record
remains the human-facing artifact maintained by the Captain from that source.
