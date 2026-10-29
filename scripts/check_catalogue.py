"""Check public project links and report repositories awaiting curation."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from check_site import catalogue


def request(url, github=False):
    headers = {"User-Agent": "Oddship-catalogue-check/1.0"}
    if github and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
    return urlopen(Request(url, headers=headers), timeout=20)


def repositories():
    repos = []
    page = 1
    while True:
        with request(f"https://api.github.com/orgs/oddship/repos?type=public&per_page=100&page={page}", True) as response:
            batch = json.load(response)
        repos.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            return repos
        page += 1


def check_link(url):
    for attempt in range(3):
        try:
            with request(url) as response:
                content_type = response.headers.get_content_type()
                response.read(1)
                if urlsplit(url).path.lower().endswith((".png", ".jpg", ".webp", ".gif")) and not content_type.startswith("image/"):
                    raise ValueError(f"Expected an image, got {content_type}")
                return {"url": url, "status": "passed", "http_status": response.status}
        except (OSError, ValueError) as error:
            if attempt == 2:
                return {"url": url, "status": "failed", "error": str(error)}
            time.sleep(attempt + 1)


def inspect(projects, repos):
    by_name = {repo["name"]: repo for repo in repos}
    names = {project["name"] for project in projects}
    issues = []
    for project in projects:
        repo = by_name.get(project["name"])
        if repo is None:
            issues.append(f"{project['name']}: repository is no longer public or was renamed")
        elif repo["archived"]:
            issues.append(f"{project['name']}: repository is archived; review its status")
    candidates = [
        {key: repo.get(key) for key in ("name", "description", "html_url", "homepage", "pushed_at")}
        for repo in repos if repo["name"] not in names | {"oddship.net"} and not repo["archived"]
    ]
    return issues, candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    projects = catalogue()
    report = {"links": [], "issues": [], "uncatalogued": []}
    try:
        report["issues"], report["uncatalogued"] = inspect(projects, repositories())
        urls = sorted({project[key] for project in projects for key in ("homepage", "image") if project.get(key)})
        with ThreadPoolExecutor(max_workers=6) as executor:
            report["links"] = list(executor.map(check_link, urls))
    except (OSError, ValueError) as error:
        report["issues"].append(str(error))
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    failures = report["issues"] + [row["url"] for row in report["links"] if row["status"] == "failed"]
    summary = ["## Catalogue maintenance", "", f"Checked {len(projects)} public projects and {len(report['links'])} links.", ""]
    summary += [f"- Needs attention: {issue}" for issue in failures]
    summary += ["", "### Public repositories to review for inclusion", ""]
    summary += [f"- [{repo['name']}]({repo['html_url']})" for repo in report["uncatalogued"]]
    summary += ["", "Catalogue entries remain manually reviewed. See the JSON artifact for details."]
    if args.summary:
        with args.summary.open("a") as stream:
            stream.write("\n".join(summary) + "\n")
    print("\n".join(summary))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
