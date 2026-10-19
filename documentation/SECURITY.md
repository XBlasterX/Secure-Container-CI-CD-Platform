# Security posture & risk notes

[← Project README](../README.md) · [Architecture](ARCHITECTURE.md)

## Current controls

| Layer | Implemented | Why it matters |
|---|---|---|
| Input | Pydantic validates `source`, `severity` and `message`; extra fields rejected | Limits unexpected API inputs |
| App image | Python 3.13 Alpine, non-root user `1000` | Reduces privileges inside the app container |
| Kubernetes app | `runAsNonRoot`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault`, `automountServiceAccountToken: false` | Defense in depth at runtime; prevents default API credential mounting |
| Availability | HTTP readiness/liveness checks and resource limits | Avoids sending traffic to unready Pods; constrains resource use |
| Supply chain | Full-SHA workflow action references; one Trivy `v0.76.0` installation; explicit `vuln,secret` scan with HIGH/CRITICAL failure gate | Controls action/scanner versions and blocks publication when the gate fails |
| Inventory | CycloneDX SBOM retained as GitHub Actions artifact | Helps investigate transitive dependencies |
| Workflow separation | `needs` dependencies; read-only token for test/build/scan, package-write token for publication | Job ordering and reduced token privileges |
| Publication | Only successful `push` to `main`; SHA-based GHCR image tag | Limits when publishing can happen, aids traceability |
| Network | Local Compose port binding; Kubernetes Services use ClusterIP | Avoids unnecessary direct public service exposure |

## Vulnerability remediation exercise

The project compared Debian-based Python runtime images using Trivy and observed repeated OS-level HIGH findings, some with no fix versions indicated in the scanner output. It also identified findings associated with bundled Python packaging tools. The working runtime was changed to `python:3.13-alpine` and retested; the successful October 2026 CI run passed the configured HIGH/CRITICAL vulnerability gate.

**Interpretation:** Scanner output depends on its vulnerability database, severity classification, image architecture and build date. A zero-findings report **does not prove the image is secure**. No assertion is made here that the Debian CVEs were universally low-risk or irrelevant.

**Layer caveat:** `RUN python -m pip uninstall -y pip` removes the pip installation from the image's merged filesystem, but earlier image layers may still contain those bytes. A carefully constructed minimal/multi-stage runtime is a future improvement. Do not describe this as complete removal from image history.

## CI version and scan controls

All 12 top-level `uses:` references are pinned to full commit SHAs, with the original version tag retained as a comment. Update these pins deliberately after reviewing the upstream release and running CI; a pinned action is not proof that its code is safe.

`TRIVY_VERSION` selects `v0.76.0` for the setup step. The Trivy action call uses `skip-setup-trivy: true`, reusing the installed binary and shared cache directory. The blocking scan explicitly selects `vuln,secret`, `CRITICAL,HIGH`, `exit-code: "1"` and `ignore-unfixed: false`. Scanner/database metadata and the local image configuration ID/architecture are recorded in CI logs.

Vulnerability databases continue to update. Version pinning improves traceability; reproducing a scan requires the exact image, scanner and database snapshot. The gate covers the API image, not the monitoring images or cluster runtime. Execution evidence remains dated in [Verification](VERIFICATION.md).

## Known gaps (prioritized)

| Priority | Gap | Recommended improvement |
|---|---|---|
| High | Monitoring Pods lack matching hardening/resource controls | Add appropriate `securityContext`, non-root support and requests/limits after testing upstream image compatibility |
| High | Grafana admin credential lifecycle is not managed by Kubernetes Secret in committed manifests | Provision per-deployment credentials securely; never commit passwords |
| Medium | Kubernetes image `secure-api:k8s-v1` is locally built and tag-based | For registry deployments, pin immutable image digests and add signed/provenance-aware publishing as appropriate |
| Medium | Monitoring uses a single Service-level scrape target | Discover/scrape each API Pod independently |
| Medium | Kubernetes monitoring has no persistent volumes; alert notification delivery is not configured | Add Kubernetes PVCs and a tested notification receiver; Compose already defines named data volumes |
| Medium | No documented end-to-end cluster security regression suite | Test fresh install, permissions, configuration and intended network behavior |
