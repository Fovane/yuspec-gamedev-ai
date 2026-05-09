import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


START_URL = "https://dev.epicgames.com/documentation/en-us/unreal-engine?application_version=5.7"
ALLOWED_PREFIX = "https://dev.epicgames.com/documentation/en-us/unreal-engine"
USER_AGENT = "Mozilla/5.0 (compatible; local-doc-prep/1.0)"


class LinkAndTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
            return
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "pre", "code"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        data = data.strip()
        if data:
            self.parts.append(data)

    def text(self):
        return " ".join(self.parts)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        final_url = response.geturl()
        body = response.read().decode("utf-8", errors="ignore")
    return final_url, body


def normalize_url(base, href):
    url = urllib.parse.urljoin(base, href)
    url, _frag = urllib.parse.urldefrag(url)
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "dev.epicgames.com":
        return None
    normalized = urllib.parse.urlunparse(parsed._replace(query="application_version=5.7"))
    if not normalized.startswith(ALLOWED_PREFIX):
        return None
    if "/API/" in normalized:
        return None
    return normalized


def clean_text(text):
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(Unreal Engine 5\.7 Documentation\s*)+", "Unreal Engine 5.7 Documentation ", text)
    text = text.replace("Copy full snippet", "")
    return text.strip()


def is_relevant_url(url):
    lowered = url.lower()
    keep_terms = (
        "programming",
        "c++",
        "cpp",
        "blueprint",
        "gameplay",
        "networking",
        "multiplayer",
        "actor",
        "character",
        "component",
        "input",
        "user-interface",
        "umg",
        "ai",
        "animation",
    )
    return any(term in lowered for term in keep_terms)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-url", default=START_URL)
    parser.add_argument("--out", default="data/clean/unreal_engine_5_7_docs_sample.txt")
    parser.add_argument("--metadata-out", default="data/metadata/unreal_docs_sources.jsonl")
    parser.add_argument("--max-pages", type=int, default=140)
    parser.add_argument("--min-chars", type=int, default=600)
    parser.add_argument("--max-chars-per-page", type=int, default=9000)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()

    queue = deque([args.start_url])
    seen = set()
    documents = []
    failures = []

    while queue and len(documents) < args.max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        try:
            final_url, body = fetch(url)
        except Exception as exc:
            failures.append({"url": url, "error": str(exc)})
            continue

        parser_obj = LinkAndTextParser()
        parser_obj.feed(body)

        for href in parser_obj.links:
            next_url = normalize_url(final_url, href)
            if next_url and next_url not in seen and (is_relevant_url(next_url) or len(documents) < 10):
                queue.append(next_url)

        text = clean_text(parser_obj.text())
        if len(text) >= args.min_chars and (is_relevant_url(final_url) or len(documents) < 10):
            text = text[: args.max_chars_per_page].rsplit(" ", 1)[0].strip()
            documents.append(
                "Domain: Unreal Engine 5.7 documentation\n"
                f"Source: {final_url}\n\n"
                f"{text}\n"
            )
            print(f"[{len(documents)}/{args.max_pages}] {final_url}")

        if args.delay > 0:
            time.sleep(args.delay)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n<|eos|>\n\n".join(documents) + "\n", encoding="utf-8")

    metadata = {
        "source": "Epic Developer Community Unreal Engine 5.7 Documentation",
        "start_url": args.start_url,
        "output": str(out_path),
        "license_note": "Official Epic documentation; review Epic terms before redistribution.",
        "pages_written": len(documents),
        "seen_urls": len(seen),
        "failures": failures[:20],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = Path(args.metadata_out)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {len(documents)} pages to {out_path}")
    print(f"wrote metadata to {metadata_path}")


if __name__ == "__main__":
    main()
