import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PERMISSIVE_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Zlib",
    "Unlicense",
}

DOMAIN_QUERIES = {
    "godot": [
        "topic:godot language:GDScript stars:>100 archived:false",
        "godot game language:GDScript stars:>100 archived:false",
    ],
    "unity": [
        "topic:unity language:C# stars:>300 archived:false",
        "unity game language:C# stars:>300 archived:false",
    ],
    "unreal": [
        "topic:unreal-engine language:C++ stars:>100 archived:false",
        "unreal engine language:C++ stars:>100 archived:false",
    ],
}

DOMAIN_TERMS = {
    "godot": ["godot", "gdscript", "node", "scene", "signal", "export", "area2d", "characterbody"],
    "unity": ["unity", "c#", "csharp", "monobehaviour", "gameobject", "prefab", "scene", "inspector", "serializefield"],
    "unreal": ["unreal", "ue5", "ue4", "c++", "blueprint", "uclass", "uproperty", "actor", "component"],
}

REPO_DOMAIN_TERMS = {
    "godot": ("godot", "gdscript"),
    "unity": ("unity", "unity3d", "unity-engine", "monobehaviour", "gameobject"),
    "unreal": ("unreal", "ue4", "ue5", "unreal-engine", "blueprint"),
}


def request_json(url, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "yuspec-gamedev-benchmark",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def search_repositories(query, token, per_page=8):
    encoded = urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": per_page})
    return request_json(f"https://api.github.com/search/repositories?{encoded}", token).get("items", [])


def get_open_issues(full_name, token, per_page=12):
    encoded = urllib.parse.urlencode({"state": "open", "per_page": per_page, "sort": "updated", "direction": "desc"})
    return request_json(f"https://api.github.com/repos/{full_name}/issues?{encoded}", token)


def clean_text(text, max_chars=1800):
    if not text:
        return ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text[:max_chars].strip()


def has_domain_signal(domain, issue):
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    return any(term in text for term in DOMAIN_TERMS[domain])


def label_names(issue):
    return [label.get("name", "") for label in issue.get("labels", [])]


def repo_matches_domain(domain, repo):
    topics = " ".join(repo.get("topics") or [])
    haystack = f"{repo.get('full_name', '')} {repo.get('description') or ''} {topics}".lower()
    return any(term in haystack for term in REPO_DOMAIN_TERMS[domain])


def is_candidate_issue(domain, issue):
    if "pull_request" in issue:
        return False
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    if len(title.strip()) < 8:
        return False
    if len(body.strip()) < 80 and not has_domain_signal(domain, issue):
        return False
    labels = " ".join(label_names(issue)).lower()
    text = f"{title}\n{body}".lower()
    useful_terms = ("bug", "fix", "error", "exception", "crash", "compile", "build", "null", "fail", "issue")
    return any(term in labels or term in text for term in useful_terms) or has_domain_signal(domain, issue)


def make_prompt(domain, repo, issue):
    license_id = repo.get("license", {}).get("spdx_id", "NOASSERTION")
    labels = ", ".join(label_names(issue)) or "none"
    body = clean_text(issue.get("body", ""))
    return (
        f"Repo: {repo['full_name']}\n"
        f"Engine domain: {domain}\n"
        f"License: {license_id}\n"
        f"Language: {repo.get('language') or 'unknown'}\n"
        f"Issue #{issue['number']}: {issue['title']}\n"
        f"Labels: {labels}\n\n"
        f"Issue body:\n{body}\n\n"
        "Task: Diagnose the likely cause and propose a concrete fix. "
        "If code is useful, include a concise patch-style code example for this engine. "
        "Keep the answer practical and avoid unsupported assumptions."
    )


def collect(args):
    token = args.github_token
    repos_by_domain = {domain: [] for domain in DOMAIN_QUERIES}
    seen_repos = set()

    for domain, queries in DOMAIN_QUERIES.items():
        for query in queries:
            if len(repos_by_domain[domain]) >= args.repos_per_domain:
                break
            try:
                repos = search_repositories(query, token, per_page=args.search_per_query)
            except urllib.error.HTTPError as exc:
                print(f"search failed for {domain}: {exc}")
                continue
            for repo in repos:
                full_name = repo["full_name"]
                if full_name in seen_repos:
                    continue
                license_id = (repo.get("license") or {}).get("spdx_id")
                if license_id not in PERMISSIVE_LICENSES:
                    continue
                if not repo_matches_domain(domain, repo):
                    continue
                if repo.get("open_issues_count", 0) < 1:
                    continue
                repos_by_domain[domain].append(repo)
                seen_repos.add(full_name)
                if len(repos_by_domain[domain]) >= args.repos_per_domain:
                    break
            time.sleep(args.sleep)

    benchmark = []
    repo_rows = []
    seen_issues = set()

    for domain, repos in repos_by_domain.items():
        for repo in repos:
            full_name = repo["full_name"]
            repo_rows.append(
                {
                    "domain": domain,
                    "full_name": full_name,
                    "html_url": repo["html_url"],
                    "license": repo.get("license", {}).get("spdx_id"),
                    "stars": repo.get("stargazers_count"),
                    "language": repo.get("language"),
                    "description": repo.get("description"),
                }
            )
            try:
                issues = get_open_issues(full_name, token, per_page=args.issues_scan_per_repo)
            except urllib.error.HTTPError as exc:
                print(f"issues failed for {full_name}: {exc}")
                continue
            picked = 0
            for issue in issues:
                key = f"{full_name}#{issue.get('number')}"
                if key in seen_issues or not is_candidate_issue(domain, issue):
                    continue
                seen_issues.add(key)
                expected = DOMAIN_TERMS[domain][:]
                expected.extend([term for term in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", issue.get("title", ""))[:4]])
                benchmark.append(
                    {
                        "id": f"{domain}_{full_name.replace('/', '_')}_{issue['number']}",
                        "domain": domain,
                        "repo": full_name,
                        "repo_url": repo["html_url"],
                        "issue_number": issue["number"],
                        "issue_url": issue["html_url"],
                        "license": repo.get("license", {}).get("spdx_id"),
                        "title": issue["title"],
                        "labels": label_names(issue),
                        "type": "issue_fix",
                        "prompt": make_prompt(domain, repo, issue),
                        "expected": expected,
                    }
                )
                picked += 1
                if picked >= args.issues_per_repo:
                    break
            time.sleep(args.sleep)

    out_benchmark = Path(args.out_benchmark)
    out_benchmark.parent.mkdir(parents=True, exist_ok=True)
    with out_benchmark.open("w", encoding="utf-8") as f:
        for row in benchmark:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    out_repos = Path(args.out_repos)
    out_repos.parent.mkdir(parents=True, exist_ok=True)
    with out_repos.open("w", encoding="utf-8") as f:
        for row in repo_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"repos: {len(repo_rows)} -> {out_repos}")
    print(f"issues: {len(benchmark)} -> {out_benchmark}")
    for domain in DOMAIN_QUERIES:
        print(f"{domain}: {sum(1 for row in benchmark if row['domain'] == domain)} issues")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-benchmark", default="eval/github_issue_benchmark.jsonl")
    parser.add_argument("--out-repos", default="eval/github_issue_repos.jsonl")
    parser.add_argument("--repos-per-domain", type=int, default=3)
    parser.add_argument("--issues-per-repo", type=int, default=2)
    parser.add_argument("--issues-scan-per-repo", type=int, default=15)
    parser.add_argument("--search-per-query", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=0.7)
    parser.add_argument("--github-token", default=None)
    args = parser.parse_args()
    collect(args)


if __name__ == "__main__":
    main()
