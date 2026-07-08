#!/usr/bin/env python3
"""Build volatile watch context from the bounded tail of the active Helmsman log."""

import os
import sys
import json


DEFAULT_ENTRY_COUNT = 50
LOG_RELATIVE_PATH = os.path.join("logs", "agents", "helmsman", "2026")
OUTPUT_NAME = "volatile_context.json"


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def requested_entry_count():
    if len(sys.argv) > 2:
        raise ValueError("usage: prune_logs.py [entry-count]")
    if len(sys.argv) == 1:
        return DEFAULT_ENTRY_COUNT

    count = int(sys.argv[1])
    if count < 1:
        raise ValueError("entry-count must be greater than zero")
    return count


def active_log(log_directory):
    candidates = []
    for name in os.listdir(log_directory):
        path = os.path.join(log_directory, name)
        if name.endswith(".jsonl") and os.path.isfile(path):
            candidates.append(path)

    if not candidates:
        raise FileNotFoundError("no .jsonl logs found in " + log_directory)
    return max(candidates, key=os.path.getmtime)


def tail_entries(path, limit):
    entries = []
    with open(path, "r", encoding="utf-8") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if not line:
                continue
            entries.append(line)
            if len(entries) > limit:
                del entries[0]
    return entries


def text_matrix(lines):
    matrix = []
    for index, line in enumerate(lines, start=1):
        try:
            normalized = json.dumps(
                json.loads(line),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except json.JSONDecodeError:
            normalized = line
        matrix.append("{:03d} | {}".format(index, normalized))
    return "\n".join(matrix)


def write_payload(root, source_path, lines):
    output_path = os.path.join(root, OUTPUT_NAME)
    temporary_path = output_path + ".tmp"
    payload = {
        "generated_by": "tools/prune_logs.py",
        "source_log": os.path.relpath(source_path, root).replace(os.sep, "/"),
        "entry_count": len(lines),
        "recent_history": text_matrix(lines),
    }

    with open(temporary_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.replace(temporary_path, output_path)
    return output_path


def main():
    try:
        count = requested_entry_count()
        root = repo_root()
        log_path = active_log(os.path.join(root, LOG_RELATIVE_PATH))
        lines = tail_entries(log_path, count)
        output_path = write_payload(root, log_path, lines)
    except (OSError, ValueError) as error:
        print("prune_logs.py: {}".format(error), file=sys.stderr)
        return 1

    print(
        "Wrote {} entries from {} to {}".format(
            len(lines),
            os.path.relpath(log_path, root),
            os.path.relpath(output_path, root),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
