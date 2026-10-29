"""Validate the catalogue and generated pages without network access."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = {"/": "Apps and tools", "/projects/": "What we've built", "/about/": "About Oddship"}


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.assets = []
        self.redirects = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in ("img", "script") and attrs.get("src"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") in ("stylesheet", "icon"):
            self.assets.append(attrs["href"])
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.redirects.append(attrs.get("content", ""))

    def handle_data(self, text):
        self.text.append(text)


def catalogue(path=ROOT / "data/projects.json"):
    projects = json.loads(path.read_text())
    names = set()
    for project in projects:
        for field in ("name", "title", "description", "body", "url", "language", "status"):
            if not isinstance(project.get(field), str) or not project[field].strip():
                raise ValueError(f"Missing {field} in project {project.get('name')}")
        if project["name"] in names:
            raise ValueError(f"Duplicate project: {project['name']}")
        names.add(project["name"])
        if type(project.get("featured")) is not bool:
            raise ValueError(f"Missing featured boolean: {project['name']}")
        if project.get("image") and not project.get("image_alt"):
            raise ValueError(f"Missing image description: {project['name']}")
        if project.get("homepage") and not project.get("action"):
            raise ValueError(f"Missing homepage action: {project['name']}")
        for key in ("url", "homepage", "image"):
            if project.get(key) and urlsplit(project[key]).scheme != "https":
                raise ValueError(f"Expected HTTPS {key}: {project['name']}")
    return projects


def validate_page(html, route, projects):
    page = Page(html)
    if PAGES[route] not in " ".join(page.text):
        raise ValueError(f"Missing expected content at {route}")
    if route in ("/", "/projects/"):
        for project in projects:
            if project["url"] not in page.links:
                raise ValueError(f"Missing project {project['name']} at {route}")
    return page


def check_site(site):
    projects = catalogue()
    for route in PAGES:
        page = validate_page((site / route.lstrip("/") / "index.html").read_text(), route, projects)
        for url in page.links + page.assets:
            parsed = urlsplit(url)
            if parsed.scheme and parsed.netloc != "oddship.net":
                continue
            if not parsed.path or parsed.scheme not in ("", "https", "http"):
                continue
            path = site / unquote(parsed.path).lstrip("/")
            if parsed.path.endswith("/"):
                path /= "index.html"
            if not path.is_file():
                raise ValueError(f"Missing local link or asset: {url}")
    for route in ("chronicles", "about/manifesto"):
        html = (site / route / "index.html").read_text()
        if not any("/projects/" in redirect for redirect in Page(html).redirects):
            raise ValueError(f"Missing legacy redirect: {route}")
    if not (site / "revision.txt").read_text().strip():
        raise ValueError("Missing deployment revision")
    print(f"Checked {len(PAGES)} pages, {len(projects)} projects, local assets, and legacy redirects")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    check_site(parser.parse_args().site)
