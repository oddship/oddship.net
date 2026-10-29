# oddship.net

A showcase of Oddship's public apps, tools, and experiments, built with Zola and
[Doordarshan](https://github.com/oddship/doordarshan-zola).

## Develop

```sh
git submodule update --init --recursive
nix develop
zola serve
```

Development, PR previews, and deployment use the same Zola package from
`flake.lock`, tracking the supported NixOS 26.05 channel. Run
`nix develop -c zola --version` to see the pinned version and
`nix build .#default` for the production build and its checks.
Keep Zola on the Tera 1 template engine until Doordarshan supports Tera 2.

`data/projects.json` contains the manually curated
public projects, their descriptions, maturity labels, and demo/download links.
To add a project, verify its public visibility and README before adding an entry.
Project screenshots are loaded from their public repositories. No private API,
account token, or client-side GitHub API call is used.

The homepage highlights entries with `featured: true`, then shows the remaining
projects. New entries appear without changing template limits. The complete
curated list is at `/projects/`. Old `/chronicles` and `/about/manifesto` routes
redirect there. There is no placeholder journal or manifesto.

## Deployment

The existing s3site deployment is preserved: GitHub Actions builds with Nix,
archives the generated site, and uploads `sites/oddship.net.tar.gz` to Garage over
Tailscale. `oddship-web` picks up the archive on its next poll. Existing repository
secrets (`TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `S3SITE_ACCESS_KEY_ID`, and
`S3SITE_SECRET_ACCESS_KEY`) supply deployment access. PR checks build without deploying.

Every build includes `revision.txt` with the source commit. After uploading,
deployment waits up to ten minutes for that exact revision at
`https://oddship.net/revision.txt`, then checks the homepage, Projects, About,
catalogue entries, and local CSS, JavaScript, and images. Requests bypass caches.
A successful object upload alone does not complete deployment. A timeout fails
the workflow so a stopped poller, stale CDN, or broken public route is visible.

## Maintenance

Dependabot opens weekly PRs for GitHub Actions updates. The Weekly maintenance
workflow runs Mondays at 06:23 UTC and can also be started manually. It checks
public repository visibility, archived status, demo/documentation links, and
screenshots. Its summary and JSON artifact list public repositories that are
absent from the catalogue for manual review. Broken links and repository status
changes fail the catalogue job.

The dependency job refreshes all Nix inputs, updates both Doordarshan pins,
builds the site, and opens or updates `automation/dependencies`. It explicitly
dispatches the PR check because PRs created by `GITHUB_TOKEN` do not trigger
`pull_request` workflows. GitHub Actions must be allowed to create pull requests
in the repository settings. Maintenance PRs require review and are not merged
automatically.

Run the maintenance checks locally:

```sh
python3 scripts/update_dependencies.py --check
python3 scripts/check_catalogue.py --report /tmp/catalogue.json
python3 -m unittest discover -s tests -v
```

To refresh dependencies, run `python3 scripts/update_dependencies.py` inside
`nix develop`, then `nix build .#default` and inspect the preview on desktop and
mobile. The build checks local routes, assets, catalogue rendering, and legacy
redirects. Python tests cover deployment retries and failures, invalid assets,
and catalogue drift without making network requests.

The `main` branch requires the `build` check before merging, including for
administrators, and blocks force pushes and deletion. Keep this check name stable
when changing the PR workflow.
The policy is recorded in `.github/branch-protection.json`. Repository
administrators can apply it with
`gh api --method PUT repos/oddship/oddship.net/branches/main/protection --input .github/branch-protection.json`.

The theme's submodule and Nix input both pin the same revision. When updating the
submodule, update the Doordarshan flake input and lock together.
