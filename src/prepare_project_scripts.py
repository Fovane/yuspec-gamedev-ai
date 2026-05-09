import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_EXTENSIONS = {".cs", ".js", ".md", ".txt"}
SKIP_DIRS = {
    ".git",
    "Library",
    "Temp",
    "Obj",
    "Build",
    "Builds",
    "Logs",
    "UserSettings",
}


def should_skip(path):
    return path.suffix.lower() == ".meta" or any(part in SKIP_DIRS for part in path.parts)


def iter_files(root, extensions):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        if path.suffix.lower() in extensions:
            yield path


def file_type_for(path):
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name.endswith(".build.cs") or name.endswith(".target.cs"):
        return "unreal-build-csharp"
    if suffix == ".cs":
        return "csharp"
    if suffix in {".cpp", ".cc", ".cxx"}:
        return "cpp"
    if suffix in {".h", ".hpp", ".hh"}:
        return "cpp-header"
    if suffix == ".js":
        return "javascript"
    return "notes"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts-dir", required=True)
    parser.add_argument("--out", default="data/clean/mmorpg_project_scripts.txt")
    parser.add_argument("--metadata-out", default="data/metadata/mmorpg_project_scripts.jsonl")
    parser.add_argument("--max-file-chars", type=int, default=12000)
    parser.add_argument("--extension", action="append")
    parser.add_argument("--domain-label", default="Unity MMORPG project")
    parser.add_argument("--source-label", default="Scripts")
    args = parser.parse_args()

    root = Path(args.scripts_dir).resolve()
    if not root.exists():
        raise SystemExit(f"Scripts directory not found: {root}")

    extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in args.extension or []}
    if not extensions:
        extensions = DEFAULT_EXTENSIONS

    documents = []
    included = 0
    skipped_empty = 0
    total_chars = 0

    for path in iter_files(root, extensions):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if len(text) < 20:
            skipped_empty += 1
            continue
        if len(text) > args.max_file_chars:
            text = text[: args.max_file_chars].rsplit("\n", 1)[0].strip()

        documents.append(
            f"Domain: {args.domain_label}\n"
            f"Source: {args.source_label}/{rel}\n"
            f"Type: {file_type_for(path)}\n\n"
            f"{text}\n"
        )
        included += 1
        total_chars += len(text)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n<|eos|>\n\n".join(documents) + "\n", encoding="utf-8")

    metadata = {
        "source": "local Unity MMORPG project scripts",
        "scripts_dir": str(root),
        "domain_label": args.domain_label,
        "source_label": args.source_label,
        "output": str(out_path),
        "extensions": sorted(extensions),
        "included_files": included,
        "skipped_empty_files": skipped_empty,
        "total_chars": total_chars,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = Path(args.metadata_out)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"included files: {included}")
    print(f"skipped empty: {skipped_empty}")
    print(f"wrote {out_path} ({out_path.stat().st_size / 1024 / 1024:.2f} MiB)")
    print(f"wrote {metadata_path}")


if __name__ == "__main__":
    main()
