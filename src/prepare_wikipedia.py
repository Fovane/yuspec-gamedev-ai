import argparse
import bz2
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TR_DUMP_URL = "https://dumps.wikimedia.org/trwiki/latest/trwiki-latest-pages-articles.xml.bz2"

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
REF_RE = re.compile(r"<ref[^>/]*?>.*?</ref>|<ref[^>]*/>", re.DOTALL | re.IGNORECASE)
TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")
FILE_RE = re.compile(r"\[\[(?:File|Image|Dosya|Resim):[^\]]+\]\]", re.IGNORECASE)
LINK_RE = re.compile(r"\[\[([^|\]]+\|)?([^\]]+)\]\]")
URL_RE = re.compile(r"\[https?://[^\s\]]+\s*([^\]]*)\]")
HEADING_RE = re.compile(r"^=+\s*(.*?)\s*=+$", re.MULTILINE)
MULTI_BLANK_RE = re.compile(r"\n{3,}")


def maybe_download(url, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and out_path.stat().st_size > 0:
        return out_path

    print(f"downloading {url}")
    with urllib.request.urlopen(url) as response, out_path.open("wb") as f:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return out_path


def strip_templates(text):
    previous = None
    while previous != text:
        previous = text
        text = TEMPLATE_RE.sub("", text)
    return text


def clean_wikitext(text):
    text = text.replace("\r\n", "\n")
    text = COMMENT_RE.sub("", text)
    text = REF_RE.sub("", text)
    text = FILE_RE.sub("", text)
    text = strip_templates(text)
    text = LINK_RE.sub(lambda match: match.group(2), text)
    text = URL_RE.sub(lambda match: match.group(1), text)
    text = HEADING_RE.sub(lambda match: f"\n{match.group(1)}\n", text)

    cleaned_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            cleaned_lines.append("")
            continue
        if line.startswith(("{|", "|}", "|-", "|", "!", "[[Kategori:", "[[Category:")):
            continue
        if line.startswith(("*", "#", ";", ":")):
            line = line.lstrip("*#;:").strip()
        if len(line) >= 2:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def iter_pages(dump_path):
    with bz2.open(dump_path, "rb") as f:
        context = ET.iterparse(f, events=("end",))
        for _, elem in context:
            if not elem.tag.endswith("page"):
                continue

            title = None
            ns = None
            text = None
            redirect = False

            for child in elem:
                if child.tag.endswith("title"):
                    title = child.text or ""
                elif child.tag.endswith("ns"):
                    ns = child.text or ""
                elif child.tag.endswith("redirect"):
                    redirect = True
                elif child.tag.endswith("revision"):
                    for rev_child in child:
                        if rev_child.tag.endswith("text"):
                            text = rev_child.text or ""

            elem.clear()

            if ns != "0" or redirect or not title or not text:
                continue
            yield title, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", help="Local pages-articles.xml.bz2 dump path")
    parser.add_argument("--download-url", default=DEFAULT_TR_DUMP_URL)
    parser.add_argument("--download-to", default="data/raw/wikipedia/trwiki-latest-pages-articles.xml.bz2")
    parser.add_argument("--out", default="data/clean/wikipedia_tr_sample.txt")
    parser.add_argument("--metadata-out", default="data/metadata/wikipedia_sources.jsonl")
    parser.add_argument("--max-articles", type=int, default=2000)
    parser.add_argument("--min-chars", type=int, default=800)
    parser.add_argument("--max-chars-per-article", type=int, default=6000)
    args = parser.parse_args()

    dump_path = Path(args.dump) if args.dump else maybe_download(args.download_url, Path(args.download_to))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    with out_path.open("w", encoding="utf-8") as out:
        for title, raw_text in iter_pages(dump_path):
            cleaned = clean_wikitext(raw_text)
            if len(cleaned) < args.min_chars:
                skipped += 1
                continue

            cleaned = cleaned[: args.max_chars_per_article].rsplit("\n", 1)[0].strip()
            out.write(f"Source: Turkish Wikipedia\nTitle: {title}\n\n{cleaned}\n\n<|eos|>\n\n")
            written += 1
            if written >= args.max_articles:
                break

    metadata = {
        "source": "Turkish Wikipedia pages-articles dump",
        "url": args.download_url if not args.dump else None,
        "dump": str(dump_path),
        "output": str(out_path),
        "license": "CC BY-SA; see Wikimedia dump metadata and article history for attribution requirements.",
        "articles_written": written,
        "articles_skipped_short": skipped,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = Path(args.metadata_out)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(metadata, ensure_ascii=False) + "\n")

    print(f"wrote {written} articles to {out_path}")
    print(f"skipped short articles: {skipped}")
    print(f"wrote metadata to {metadata_path}")


if __name__ == "__main__":
    main()
