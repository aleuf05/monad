#!/usr/bin/env python3
"""Create the next numbered Monad doctrine document."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import shlex
import sys


DOCTRINE_PATTERN = re.compile(
    r"^(?P<number>\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def nonempty(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise argparse.ArgumentTypeError("value must not be empty")
    return cleaned


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the next versioned Monad doctrine entry."
    )
    parser.add_argument("--title", required=True, type=nonempty)
    parser.add_argument("--principle", required=True, type=nonempty)
    parser.add_argument("--status", required=True, type=nonempty)
    parser.add_argument("--author", required=True, type=nonempty)
    return parser.parse_args()


def title_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError("title must contain at least one ASCII letter or number")
    return slug


def next_doctrine_number(doctrine_dir: Path) -> int:
    highest = 0
    for path in doctrine_dir.iterdir():
        if not path.is_file():
            continue
        match = DOCTRINE_PATTERN.fullmatch(path.name)
        if match:
            highest = max(highest, int(match.group("number")))

    next_number = highest + 1
    if next_number > 999:
        raise ValueError("doctrine numbering has exceeded the NNN format")
    return next_number


def doctrine_markdown(
    number: int,
    title: str,
    principle: str,
    status: str,
    author: str,
) -> str:
    return f"""# Doctrine {number:03d} — {title}

**Status:** {status}
**Author:** {author}
**Adopted:** {date.today().isoformat()}

## Principle

{principle}

## Rationale

TODO

## Operating Guidance

TODO

## Related Artifacts

TODO
"""


def main() -> int:
    args = parse_args()
    root = repo_root()
    doctrine_dir = root / "docs" / "doctrine"
    doctrine_dir.mkdir(parents=True, exist_ok=True)

    try:
        number = next_doctrine_number(doctrine_dir)
        slug = title_slug(args.title)
    except ValueError as error:
        print(f"doctrine-add.py: {error}", file=sys.stderr)
        return 1

    relative_path = Path("docs") / "doctrine" / f"{number:03d}-{slug}.md"
    output_path = root / relative_path
    content = doctrine_markdown(
        number=number,
        title=args.title,
        principle=args.principle,
        status=args.status,
        author=args.author,
    )

    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    except FileExistsError:
        print(
            f"doctrine-add.py: refusing to overwrite {relative_path.as_posix()}",
            file=sys.stderr,
        )
        return 1
    except OSError as error:
        print(f"doctrine-add.py: {error}", file=sys.stderr)
        return 1

    quoted_path = shlex.quote(relative_path.as_posix())
    commit_message = shlex.quote(
        f"Add Doctrine {number:03d}: {args.title}"
    )

    print(f"Doctrine number: {number:03d}")
    print(f"Created file: {relative_path.as_posix()}")
    print("Suggested git commands:")
    print(f"  git add -- {quoted_path}")
    print(f"  git commit -m {commit_message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
