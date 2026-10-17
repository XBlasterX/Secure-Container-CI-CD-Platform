# Security posture & risk notes

[← Project README](../README.md) · [Architecture](ARCHITECTURE.md)

## Current controls

| Layer | Implemented | Why it matters |
|---|---|---|
| Input | Pydantic validates `source`, `severity` and `message`; extra fields rejected | Limits unexpected API inputs |
| App image | Python 3.13 Alpine, non-root user `1000` | Reduces privileges inside the app container |
| Kubernetes app | `runAsNonRoot`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault` | Defense in depth at runtime |
| Availability | HTTP readiness/liveness checks and resource limits | Avoids sending traffic to unready Pods; constrains resource use |
| Supply chain | Trivy image scanning with HIGH/CRITICAL failure gate | Blocks publication when scanner reports these findings |
| Inventory | CycloneDX SBOM retained as GitHub Actions artifact | Helps investigate transitive dependencies |
| Workflow separation | `needs` dependencies; read-only token for test/build/scan, package-write token for publication | Job ordering and reduced token privileges |
| Publication | Only successful `push` to `main`; SHA-based GHCR image tag | Limits when publishing can happen, aids traceability |
| Network | Local Compose port binding; Kubernetes Services use ClusterIP | Avoids unnecessary direct public service exposure |

## Vulnerability remediation exercise

The project compared Debian-based Python runtime images using Trivy and observed repeated OS-level HIGH findings, some with no fix versions indicated in the scanner output. It also identified findings associated with bundled Python packaging tools. The working runtime was changed to `python:3.13-alpine` and retested; the successful October 2026 CI run passed the configured HIGH/CRITICAL vulnerability gate.

**Interpretation:** Scanner output depends on its vulnerability database, severity classification, image architecture and build date. A zero-findings report **does not prove the image is secure**. No assertion is made here that the Debian CVEs were universally low-risk or irrelevant. Generated JSON reports are retained under `documentation/` as lab artifacts, not as automatically approved exceptions.

**Layer caveat:** `RUN python -m pip uninstall -y pip` removes the pip installation from the image's merged filesystem, but earlier image layers may still contain those bytes. A carefully constructed minimal/multi-stage runtime is a future improvement. Do not describe this as complete removal from image history.

## Known gaps (prioritized)

| Priority | Gap | Recommended improvement |
|---|---|---|
| High | Monitoring Pods lack matching hardening/resource controls | Add appropriate `securityContext`, non-root support and requests/limits after testing upstream image compatibility |
| High | Grafana admin credential lifecycle is not managed by Kubernetes Secret in committed manifests | Provision per-deployment credentials securely; never commit passwords |
| High | GitHub Actions are version-tagged; Trivy installer selects `latest` | Pin action refs to reviewed commit SHAs and select a controlled scanner version |
| Medium | API Pod does not set `automountServiceAccountToken: false` | Disable default token automount when Kubernetes API access is unnecessary |
| Medium | Kubernetes image `secure-api:k8s-v1` is locally built and tag-based | For registry deployments, pin immutable image digests and add signed/provenance-aware publishing as appropriate |
| Medium | Monitoring uses a single Service-level scrape target | Discover/scrape each API Pod independently |
| Medium | No persistent metrics/dashboard volumes and no alert routing | Add PVC and Alertmanager / notification configuration |
| Medium | No documented end-to-end cluster security regression suite | Test fresh install, permissions, configuration and intended network behavior |
| Low | Generated reports and Python build artifacts are checked in | Curate evidence and remove generated files from normal Git tracking |

## Honest boundaries for interviews

- **Not full CD to Kubernetes:** CI automatically builds, tests, scans and publishes; Kubernetes deployment is manual.
- **Not guaranteed vulnerability-free:** The scanner found no gate-blocking vulnerabilities in the specific successful run.
- **Not a production observability stack:** No HA, durable time-series store or notification routing.
- **Not comprehensive per-Pod visibility:** `up{job="infrastructure-api"}` currently checks a Service target.
- **No claim of verified compliance:** Security settings are learning controls, not a certification or formal audit.

The point of the project is to implement and explain concrete risk-reduction mechanisms and their limitations.
