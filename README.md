# Zyn Anisette for SideStore
Custom anisette v3 server for Vercel Container Runtime. Based on Dadoum/anisette-v3-server at commit 684895737aaf1a1c4586fcd5b67509ffd500a36c.

[Deploy on Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FNightVibes33%2FUnrealMCP%2Ftree%2Ftemp-zyn-anisette-vercel&project-name=zyn-anisette&repository-name=zyn-anisette)

## Deployment
Use the deploy link above to import this temporary branch as a new project named "zyn-anisette". Vercel detects Dockerfile.vercel automatically. Enable Fluid Compute. Disable deployment authentication for production so SideStore can reach it. Container Runtime and WebSockets require the current Vercel beta features described in https://vercel.com/docs/functions/runtimes/container and https://vercel.com/docs/functions/websockets.

Alternatively, in this folder with Vercel CLI already authenticated:
    vercel --scope bobbytatum12345-5121s-projects --prod

Use the resulting production origin (https://your-project.vercel.app) in SideStore Settings > Anisette Servers > custom server.

## Behavior
- Native anisette v3 generation; no forwarding to public anisette servers.
- Per-client provisioning supplied by SideStore; no shared v1 machine.
- Apple libraries downloaded directly from Apple during the image build.
- GET / returns JSON health metadata.
- GET /v3/client_info returns protocol client information.
- WebSocket /v3/provisioning_session performs native provisioning.
- POST /v3/get_headers generates anisette headers.
- Provisioning files use independent temporary directories and are removed after use.
- 30-second client-message timeout.
- Apple ID credentials are not needed by this server.

## Verification and current limitation
Source customization has been checked against the pinned upstream source. The Docker image and live Apple provisioning have NOT been tested: this workspace has no Docker or Vercel CLI. Vercel project creation through the connected account returned HTTP 403 on October 13, 2026. Use the deploy link to create the deployment from your browser.

The -80045 Apple sign-in error is currently reported across several sideloading clients in https://github.com/altstoreio/AltStore/issues/1828. This server does not guarantee a fix for Apple's sign-in rejection.

Upstream source and licensing remain in the pinned upstream repository. This bundle includes only the deployment recipe and customizations.
