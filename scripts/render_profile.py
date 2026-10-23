"""Write the organization's public repositories into profile/README.md.

The table between the `repositories:start` and `repositories:end` markers is
generated from the GitHub API: every public repository of EmpirioLabs-AI that
is not a fork, not archived and not this one, with its own description. A new
repository, a renamed one or a changed description reaches the profile on the
next run of .github/workflows/profile-repositories.yml, with no hand edit.

    python scripts/render_profile.py           # rewrite the table if it changed
    python scripts/render_profile.py --check   # exit 1 when the table is stale
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ORG = "EmpirioLabs-AI"
README = Path(__file__).resolve().parents[1] / "profile" / "README.md"
START, END = "<!-- repositories:start -->", "<!-- repositories:end -->"
SKIP = {".github"}


def repositories() -> list[dict]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{ORG}-profile"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    found, page = [], 1
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos?type=public&per_page=100&page={page}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            batch = json.load(response)
        found += batch
        if len(batch) < 100:
            return found
        page += 1


def table(repos: list[dict]) -> str:
    rows = ["| Repository | Description |", "| --- | --- |"]
    for repo in sorted(repos, key=lambda r: r["name"].lower()):
        if repo["fork"] or repo["archived"] or repo["private"] or repo["name"] in SKIP:
            continue
        # One style for every row: no closing period, whatever the description has.
        description = (repo.get("description") or "").strip().rstrip(".").replace("|", "\\|")
        rows.append(f"| [{repo['name']}]({repo['html_url']}) | {description} |")
    return "\n".join(rows)


def render(text: str, block: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"{README} has no {START} ... {END} block")
    return pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)


def main() -> int:
    raw = README.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    current = raw.replace("\r\n", "\n")
    wanted = render(current, table(repositories()))
    if wanted == current:
        print("profile: the repository table is current")
        return 0
    if "--check" in sys.argv[1:]:
        print("profile: the repository table is stale; run python scripts/render_profile.py")
        return 1
    README.write_bytes(wanted.replace("\n", newline).encode("utf-8"))
    print("profile: rewrote the repository table")
    return 0


if __name__ == "__main__":
    sys.exit(main())
