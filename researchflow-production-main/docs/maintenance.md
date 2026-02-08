# Maintenance and Operations

Short reference for deployment and operational constraints.

## Storage and paths (deployment)

- **ARTIFACTS_PATH** (and aliases `ARTIFACT_PATH`, `RESEARCHFLOW_ARTIFACTS_DIR`) must be **absolute** and under **`/data/*`** (e.g. `/data/artifacts`) in deployment runs. Do not use paths under `/app` or relative paths.
- **Avoid bind-mounting `/app`** on server deployments (e.g. `./services/worker:/app` or `./services/collab:/app`). It overwrites built image contents and can break permissions and artifacts. Use the published GHCR images as-is, with only `/data` (and optionally `/data/projects`) volume-mounted.

See also: [Hetzner Full-Stack Deployment](deployment/hetzner-fullstack.md#persistent-data-storage).

## Collab service (if still misbehaving)

Removing `./services/collab:/app` is the durable fix. If collab still behaves strangely after redeploy, the next step is to remove any volume that can shadow built artifacts—e.g. drop `./packages:/app/packages` and `/app/node_modules` for the collab service in the compose file used on the server so the container runs the image as-is.
