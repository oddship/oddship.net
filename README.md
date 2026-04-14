# oddship.net

This repository contains the source for the [oddship.net](https://oddship.net) website, built with [Astro](https://astro.build/) and MDX.

## Deployment

`oddship.net` now follows the same hosted deploy model as `rohanverma.net`:

- GitHub Actions builds the site
- a manual GitHub Actions workflow uploads `sites/oddship.net.tar.gz` to Garage over Tailscale
- `oddship-web` serves the site through `s3site`
- production picks up new uploads on the next `s3site` poll

The deploy workflow expects these repository secrets:

- `TS_OAUTH_CLIENT_ID`
- `TS_OAUTH_SECRET`
- `S3SITE_ACCESS_KEY_ID`
- `S3SITE_SECRET_ACCESS_KEY`

Use a dedicated Garage write key for this repo rather than reusing the runtime read-only host key.
