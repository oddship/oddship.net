"""Refresh Nix inputs and keep both Doordarshan pins at the same revision."""

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "themes/doordarshan"
PIN = re.compile(r"github:oddship/doordarshan-zola/([0-9a-f]{40})")


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def check():
    match = PIN.search((ROOT / "flake.nix").read_text())
    lock = json.loads((ROOT / "flake.lock").read_text())["nodes"]["doordarshan"]
    head = run("git", "-C", str(THEME), "rev-parse", "HEAD")
    if not match or not (
        match[1] == lock["locked"]["rev"] == lock["original"]["rev"] == head
    ):
        raise ValueError("Doordarshan submodule, flake input, and lock must match")
    print(f"Doordarshan pins match: {head}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        run("git", "submodule", "update", "--init", "--recursive")
        run("git", "-C", str(THEME), "fetch", "origin", "main")
        revision = run("git", "-C", str(THEME), "rev-parse", "FETCH_HEAD")
        run("git", "-C", str(THEME), "checkout", "--detach", revision)
        flake = ROOT / "flake.nix"
        contents, count = PIN.subn(
            f"github:oddship/doordarshan-zola/{revision}", flake.read_text()
        )
        if count != 1:
            raise ValueError("Expected exactly one Doordarshan flake input")
        flake.write_text(contents)
        subprocess.run(
            ["nix", "--extra-experimental-features", "nix-command flakes",
             "flake", "update"], cwd=ROOT, check=True
        )
    check()


if __name__ == "__main__":
    main()
