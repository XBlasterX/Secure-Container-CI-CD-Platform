# Secure Container CI/CD Platform

A containerized **FastAPI infrastructure-event API** with automated testing, vulnerability scanning, SBOM generation and image publishing through GitHub Actions. The repository also includes Docker Compose and local Kubernetes deployments with Prometheus and Grafana monitoring.

[![CI](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml)

## Verification status

Evidence snapshot: **17 October 2026**, commit [`ba7fe4e`](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/commit/ba7fe4e2f3bf5261d036a3e8198345f33c71e25e), [CI run #19](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/runs/39051900362) (push to `main`).

| Area | Confirmed result | Scope / remaining verification |
| --- | --- | --- |
| Application checks | Ruff passed; Pytest: **13 passed, 1 warning** | In-process FastAPI `TestClient` tests; the built container is not started by CI |
| Image build and scan | Linux/amd64 image built; Trivy HIGH/CRITICAL gate passed | Applies to this image and scan date; monitoring images and runtime security are outside this gate |
| SBOM | CycloneDX generated and uploaded as the `sbom` artifact | Attached to CI run as artifact |
| Image publication | `publish` loaded the scanned image artifact and successfully pushed its SHA tag to GHCR | Publication is confirmed; pulling and running the registry image is not tested by this workflow |
| Service readiness | Docker health check and Kubernetes probes are configured | No Compose/container/cluster smoke test runs in CI; `/readyz` returns a fixed response without dependency checks |
| Monitoring and deployment | Compose configuration and manual kind deployment manifests are present | End-to-end readiness, independent health of both replicas and alert delivery are not established by this CI run |

See [Verification evidence and pending scenarios](documentation/VERIFICATION.md) for job links, the published image digest and the remaining checks.

## Architecture

| Path | Build and verification | Destination |
| --- | --- | --- |
| GitHub Actions | Ruff/Pytest → API image build → SBOM generation → Trivy gate → image artifact | GHCR publication on successful push to `main` |
| Docker Compose | Local API build; separate upstream Prometheus/Grafana images | Local Compose stack |
| kind | Separate local API build → kind image load → manual `kubectl apply` | Local Kubernetes cluster |

The workflow automatically publishes a scanned API image to **GitHub Container Registry (GHCR)**. Compose and kind build separate local images; the kind instructions do not deploy the published GHCR digest.

## Technology stack

| Component | Technology |
| --- | --- |
| API | Python 3.13, FastAPI, Pydantic |
| Testing and linting | Pytest, Ruff |
| Containers | Docker, Docker Compose, Alpine Linux |
| CI and image registry | GitHub Actions, GHCR |
| Container security | Trivy, CycloneDX SBOM |
| Orchestration | Kubernetes, kind, kubectl |
| Monitoring | Prometheus, Grafana |

## Features

- REST API for validated infrastructure events, with structured JSON logging and Prometheus metrics.
- Automated linting and **13 in-process FastAPI tests** on pushes to `main`, pull requests targeting `main` and manual workflow dispatch.
- Docker image builds followed by Trivy scanning; HIGH/CRITICAL findings fail the CI job.
- CycloneDX SBOM retained as a GitHub Actions artifact.
- SHA-tagged container images published to GHCR on successful pushes to `main`.
- Kubernetes Deployment with **two API replicas**, health probes, CPU/memory limits, non-root security context and disabled ServiceAccount token automounting.
- Prometheus metrics collection, an availability alert rule and Grafana dashboards.

## Quick start — Docker Compose

**Prerequisites:** Docker with Compose support.

```bash
git clone https://github.com/XBlasterX/Secure-Container-CI-CD-Platform.git
cd Secure-Container-CI-CD-Platform
docker compose up --build -d
```

| Service | URL |
| --- | --- |
| FastAPI | http://localhost:8080 |
| Interactive API docs | http://localhost:8080/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Verify the API:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
docker compose ps
```

Stop the stack:

```bash
docker compose down
```

The Compose services use a user-defined bridge network, and published ports are bound to localhost. Compose builds the API locally; it does not pull the image published by CI.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/healthz` | Health check |
| `GET` | `/readyz` | Readiness check |
| `GET` | `/version` | API version |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/events` | Validate and log an infrastructure event |

Example request:

```bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{"source":"firewall-01","severity":"critical","message":"SSH brute force detected"}'
```

The API validates `source`, `message` and `severity` with Pydantic. Supported severity values are `info`, `warning` and `critical`. Accepted events are written as JSON logs and increment `infrastructure_events_accepted_total`.

## Kubernetes deployment (kind)

**Prerequisites:** Docker, [kind](https://kind.sigs.k8s.io/) and `kubectl`. Build the image for the same CPU architecture as the kind nodes.

```bash
kind create cluster --name secure-platform

docker build -t secure-api:k8s-v1 .
kind load docker-image secure-api:k8s-v1 --name secure-platform

kubectl --context kind-secure-platform apply -f k8s/namespace.yaml
kubectl --context kind-secure-platform apply -f k8s/deployment.yaml
kubectl --context kind-secure-platform apply -f k8s/service.yaml
kubectl --context kind-secure-platform apply -f k8s/monitoring/

kubectl --context kind-secure-platform -n secure-platform get deployments,pods,services
kubectl --context kind-secure-platform -n secure-platform rollout status deployment/secure-platform-deployment
```

Access the API via port forwarding:

```bash
kubectl --context kind-secure-platform -n secure-platform \
  port-forward svc/secure-platform-service 8081:8000
```

Open http://localhost:8081/healthz to verify the deployment.

The manifests use the locally loaded `secure-api:k8s-v1` image. GHCR publishing and local cluster deployment are separate steps.

## Monitoring

**Prometheus** scrapes the API's `/metrics` endpoint every 15 seconds and evaluates an `APIMetricsUnavailable` alert rule. **Grafana** is configured with a Prometheus datasource and dashboards.

With Docker Compose, monitoring is available at `localhost:9090` and `localhost:3000`.

For Kubernetes, forward the monitoring services in separate terminals:

```bash
kubectl --context kind-secure-platform -n secure-platform \
  port-forward svc/prometheus-service 9090:9090

kubectl --context kind-secure-platform -n secure-platform \
  port-forward svc/grafana-service 3000:3000
```

In Prometheus, the query `up{job="infrastructure-api"}` shows whether its API scrape target is reachable. Kubernetes monitoring currently scrapes the API Service endpoint.

## CI/CD pipeline

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

| Job | Steps |
| --- | --- |
| `app_test` | Install Python dependencies, run Ruff and Pytest |
| `build_scan` | Build image, generate SBOMs, scan with Trivy, upload image artifact |
| `publish` | Download scanned image, tag with the commit SHA, push to GHCR |

All 12 workflow action references are pinned to full commit SHAs. Trivy `v0.76.0` is installed once and reused for SBOM generation and the blocking scan. CI logs the scanner version, available database metadata and local image ID/architecture. Vulnerability databases remain updated; repeating a result requires the same image and database snapshot as well as the same scanner version.

The `publish` job runs only for successful pushes to `main`. It reuses the image artifact produced by `build_scan` rather than rebuilding the image after scanning.

[View CI runs](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml)

Run checks locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev]"
python -m ruff check src tests
python -m pytest -q
```

## Security controls

- API container runs as a non-root user (`UID 1000`).
- Kubernetes API Pods disable privilege escalation, drop Linux capabilities and use the `RuntimeDefault` seccomp profile.
- Readiness/liveness probes and resource requests/limits are configured for the API Deployment.
- Trivy blocks image publication when it reports HIGH or CRITICAL vulnerabilities.
- The Trivy gate scans the API image; monitoring images and Kubernetes runtime behavior are outside this CI gate.
- CI permissions are scoped by job; package publication uses `packages: write`.

For configuration details, see [Architecture](documentation/ARCHITECTURE.md) and [Security](documentation/SECURITY.md). For observed results and their limits, see [Verification](documentation/VERIFICATION.md).

## Repository structure

| Path | Contents |
| --- | --- |
| [`src/`](src/) | FastAPI application, models and logging |
| [`tests/`](tests/) | API tests |
| [`Dockerfile`](Dockerfile) | Application image |
| [`compose.yaml`](compose.yaml) | Local API and monitoring stack |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI, security scans and GHCR publishing |
| [`k8s/`](k8s/) | Kubernetes API and monitoring manifests |
| [`monitoring/`](monitoring/) | Prometheus and Grafana configuration for Compose |
| [`documentation/`](documentation/) | Architecture, security and verification evidence |

