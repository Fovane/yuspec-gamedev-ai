import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".github",
    "_build",
    "_extensions",
    "_static",
    "_templates",
    "_tools",
    "img",
}

RST_DIRECTIVE_RE = re.compile(r"^\s*\.\. [a-zA-Z0-9_-]+::")
RST_ROLE_RE = re.compile(r":([a-zA-Z0-9_-]+):`([^`]+)`")
RST_LINK_RE = re.compile(r"`([^`<]+?)\s*<[^`>]+>`_")
RST_ANON_LINK_RE = re.compile(r"`([^`]+)`_")
MULTI_BLANK_RE = re.compile(r"\n{3,}")


def should_skip(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    return any(part in SKIP_DIRS for part in rel_parts)


def clean_rst(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = RST_ROLE_RE.sub(lambda match: match.group(2), text)
    text = RST_LINK_RE.sub(lambda match: match.group(1), text)
    text = RST_ANON_LINK_RE.sub(lambda match: match.group(1), text)

    cleaned = []
    skip_indented_block = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith(".. _"):
            continue

        if RST_DIRECTIVE_RE.match(line):
            directive = stripped.split("::", 1)[0].removeprefix(".. ").strip()
            if directive in {"toctree", "figure", "image", "include", "raw", "list-table"}:
                skip_indented_block = True
                continue
            skip_indented_block = False

        if skip_indented_block:
            if not stripped or raw_line.startswith((" ", "\t")):
                continue
            skip_indented_block = False

        if stripped.startswith(":") and ":" in stripped[1:]:
            continue

        if set(stripped) <= {"=", "-", "~", "^", "\"", "#", "*"} and len(stripped) >= 3:
            continue

        if stripped.startswith(".. "):
            continue

        line = line.replace("``", "`")
        cleaned.append(line)

    output = "\n".join(cleaned)
    output = MULTI_BLANK_RE.sub("\n\n", output)
    return output.strip()


def iter_rst_files(root: Path):
    for path in sorted(root.rglob("*.rst")):
        if not should_skip(path, root):
            yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default="data/raw/godot-docs-4.6")
    parser.add_argument("--out", default="data/clean/godot_docs_4_6.txt")
    parser.add_argument("--metadata-out", default="data/metadata/sources.jsonl")
    parser.add_argument("--source-url", default="https://github.com/godotengine/godot-docs")
    parser.add_argument("--branch", default="4.6")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    if not docs_dir.exists():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    documents = []
    included_files = 0
    skipped_empty = 0

    for path in iter_rst_files(docs_dir):
        cleaned = clean_rst(path.read_text(encoding="utf-8", errors="ignore"))
        if len(cleaned) < 200:
            skipped_empty += 1
            continue
        rel = path.relative_to(docs_dir).as_posix()
        documents.append(f"<|godot|>\nSource: godot-docs/{rel}\n\n{cleaned}\n")
        included_files += 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n<|eos|>\n\n".join(documents) + "\n", encoding="utf-8")

    metadata = {
        "source": "Godot Engine official documentation",
        "url": args.source_url,
        "branch": args.branch,
        "docs_dir": str(docs_dir),
        "output": str(out_path),
        "license": "CC BY 3.0 for most documentation; classes/ is MIT per godot-docs repository license notes.",
        "included_rst_files": included_files,
        "skipped_short_files": skipped_empty,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path = Path(args.metadata_out)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Included RST files: {included_files}")
    print(f"Skipped short files: {skipped_empty}")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024 / 1024:.2f} MiB)")
    print(f"Wrote {metadata_path}")


if __name__ == "__main__":
    main()
