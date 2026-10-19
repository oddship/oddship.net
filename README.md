# oddship.net

A showcase of Oddship's public apps, tools, and experiments, built with Zola and
[Doordarshan](https://github.com/oddship/doordarshan-zola).

## Develop

```sh
git submodule update --init --recursive
nix develop
zola serve
```

Or use Zola 0.21.0 directly. `data/projects.json` contains the manually curated
public projects, their descriptions, maturity labels, and demo/download links.
To add a project, verify its public visibility and README before adding an entry.
Project screenshots are loaded from their public repositories. No private API,
account token, or client-side GitHub API call is used.

The homepage highlights apps, then developer tools, then experiments. The complete
curated list is at `/projects/`. Old `/chronicles` and `/about/manifesto` routes
redirect there. There is no placeholder journal or manifesto.

## Deployment

The existing s3site deployment is preserved: GitHub Actions builds with Nix,
archives the generated site, and uploads `sites/oddship.net.tar.gz` to Garage over
Tailscale. `oddship-web` picks up the archive on its next poll. Existing repository
secrets (`TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`, `S3SITE_ACCESS_KEY_ID`, and
`S3SITE_SECRET_ACCESS_KEY`) are unchanged. PR checks build without deploying.

The theme's submodule and Nix input both pin the same revision. When updating the
submodule, update the Doordarshan flake input and lock together.
