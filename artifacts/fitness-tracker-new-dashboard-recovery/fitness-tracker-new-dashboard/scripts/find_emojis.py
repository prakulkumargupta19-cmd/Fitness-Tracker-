"""Report emoji-like Unicode characters in frontend source files."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|"
    r"[\u2b50-\u2b55]|[\u203c\u2049\u2139\u2194-\u2199"
    r"\u21a9-\u21aa\u231a-\u231b\u2328\u23cf\u23e9-\u23f3"
    r"\u23f8-\u23fa\u24c2\u25aa-\u25ab\u25b6\u25c0"
    r"\u25fb-\u25fe\u2600-\u27ef\u2934-\u2935\u2b05-\u2b07"
    r"\u2b1b-\u2b1c\u2b50\u2b55\u3030\u303d\u3297\u3299]"
)
SOURCE_SUFFIXES = {".html", ".js", ".css"}


def find_emojis(root: Path) -> int:
    """Print matching characters and return their total count."""
    count = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath, filename)
            if path.suffix not in SOURCE_SUFFIXES or filename == "index.html":
                continue

            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError as error:
                print(f"Could not read {path}: {error}", file=sys.stderr)
                continue

            for line_number, line in enumerate(lines, start=1):
                matches = EMOJI_PATTERN.findall(line)
                if matches:
                    relative_path = path.relative_to(root)
                    codepoints = [f"U+{ord(char):04X}" for char in matches]
                    print(f"{relative_path}:{line_number} -> {codepoints}")
                    count += len(matches)

    print(f"Total emojis found: {count}")
    return count


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=project_root / "frontend1",
        help="directory to scan (default: %(default)s)",
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        parser.error(f"not a directory: {args.root}")

    find_emojis(args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())