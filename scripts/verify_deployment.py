"""Wait for the expected revision and smoke-test the public site."""

import argparse
import time
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from check_site import PAGES, catalogue, validate_page


def fetch(url, revision, timeout):
    separator = "&" if "?" in url else "?"
    request = Request(
        url + separator + urlencode({"deploy": revision, "check": time.time_ns()}),
        headers={"Cache-Control": "no-cache, no-store", "Pragma": "no-cache",
                 "User-Agent": "Oddship-deployment-check/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"{url} returned {response.status}")
        return response.read(), response.headers.get_content_type()


def verify(base_url, revision, timeout=600, interval=10):
    deadline = time.monotonic() + timeout
    projects = catalogue()
    last_error = "No attempts made"
    while time.monotonic() < deadline:
        try:
            def get(path):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Deployment verification deadline reached")
                return fetch(urljoin(base_url.rstrip("/") + "/", path), revision, min(20, remaining))

            marker, _ = get("revision.txt")
            if marker.decode().strip() != revision:
                raise ValueError("Public site is still serving a different revision")
            assets = set()
            for route in PAGES:
                html, content_type = get(route)
                if content_type != "text/html":
                    raise ValueError(f"Expected HTML at {route}, got {content_type}")
                page = validate_page(html.decode(), route, projects)
                assets.update(page.assets)
            for asset in sorted(assets):
                absolute = urljoin(base_url, asset)
                if urlsplit(absolute).netloc != urlsplit(base_url).netloc:
                    continue
                body, content_type = get(absolute)
                if not body or content_type == "text/html":
                    raise ValueError(f"Missing or invalid public asset: {asset}")
            print(f"Verified public revision {revision}, pages, project links, and local assets", flush=True)
            return
        except (OSError, ValueError, UnicodeError) as error:
            last_error = str(error)
            print(f"Waiting for deployment: {last_error}", flush=True)
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"Public deployment did not become healthy: {last_error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    verify(args.url, args.revision, args.timeout)
