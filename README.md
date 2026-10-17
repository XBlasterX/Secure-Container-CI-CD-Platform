# Secure Container CI/CD Platform

**A hands-on DevSecOps project: build, test, scan, publish and run an observable FastAPI service with Docker, GitHub Actions and Kubernetes.**

[![CI](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-kind-326CE5?logo=kubernetes&logoColor=white)](https://kind.sigs.k8s.io/)
[![Security](https://img.shields.io/badge/Security-Trivy%20%2B%20SBOM-555)](documentation/SECURITY.md)

## Overview

This project demonstrates the complete **build-to-registry** workflow for a small infrastructure-event API and its **manual deployment** into a local Kubernetes cluster. The goal is to make security controls, release traceability and observability visible in a reproducible lab—not to claim a production-ready platform.

**Implemented:**
- FastAPI API with strict Pydantic input validation, JSON event logs and Prometheus metrics.
- 13 automated tests and Ruff linting in GitHub Actions.
- Alpine-based, non-root Docker image and Docker Compose environment.
- GitHub Actions pipeline with gated build, Trivy vulnerability scanning, CycloneDX SBOM and SHA-tagged publication to GitHub Container Registry (GHCR).
- Local Kubernetes (kind) deployment with two API replicas, ClusterIP networking, health probes, resource limits and container security settings.
- Prometheus scraping, an availability alert rule, Grafana datasource configuration and provisioned dashboards.

**Scope boundary:** GitHub Actions publishes the image to GHCR automatically after successful checks. **Kubernetes deployments are applied manually with kubectl**; there is no automated cluster deployment step.

## Architecture

~~~text
Developer / GitHub repository
            |
      push / pull request
            v
      GitHub Actions
       app_test job
      Ruff + 13 tests
            |
            v
       build_scan job
    Docker Buildx -> local image
            |              |
     CycloneDX SBOM     Trivy (HIGH/CRITICAL gate)
            |              |
       Actions artifact    PASS
                           |
                      image.tar artifact
                           |
                           v
                     publish job
                  (push to main only)
                 docker load / tag / push
                           |
                           v
          GHCR: sha-<full-commit-sha>
                           |
                   manual deployment
                           v
             kind (local Kubernetes)
             Namespace: secure-platform
                           |
             +-------------+----------------+
             |                              |
      FastAPI Deployment               Observability
         2 replicas                    Prometheus
             |                              |
       ClusterIP Service <---- scrape ------+
                                            |
                                      Grafana UI
~~~

See [Architecture & engineering decisions](documentation/ARCHITECTURE.md) for a detailed explanation of the trade-offs and component boundaries.

## Technology stack

| Area | Technology | Purpose |
|---|---|---|
| API | Python 3.13, FastAPI, Pydantic | API, input validation, health endpoints |
| Quality | Pytest, Ruff | Functional and lint checks |
| Image | Docker, Buildx, Alpine | Build and run a non-root container |
| CI / registry | GitHub Actions, GHCR | Automated checks and image publication |
| Supply-chain security | Trivy, CycloneDX SBOM | Vulnerability gate and dependency inventory |
| Orchestration | Kubernetes, kind, kubectl | Local container orchestration |
| Monitoring | Prometheus, Grafana | Metrics, visualization and alert rule |

## Key engineering decisions

| Decision | Rationale |
|---|---|
| **Scan before publishing** | A failed HIGH/CRITICAL scan blocks the downstream publish job. |
| **Transfer the built image as an artifact** | Separate GitHub-hosted jobs cannot access each other's local Docker images. The publish job loads the previously scanned image instead of rebuilding it. |
| **SHA-based GHCR tags** | Each published tag points to the image from a specific commit; deployment still requires deliberate image selection. |
| **Alpine runtime** | Reduced findings in this project's Trivy comparison with Debian-based Python images. Zero reported findings is **not** proof of zero risk. |
| **Two Kubernetes API replicas** | Demonstrates Deployment, Service routing and readiness-aware availability. |
| **ClusterIP + local port-forward** | Lab interfaces are not intentionally exposed through public LoadBalancer/NodePort services. |
| **Manual kind deployment** | Separates release artifact publication from runtime deployment and keeps the lab cloud-cost-free. |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness / basic health: `{"status":"ok"}` |
| GET | `/readyz` | Readiness: `{"status":"ready"}` |
| GET | `/version` | Current API version |
| GET | `/metrics` | Prometheus exposition format |
| POST | `/events` | Validate and log an infrastructure event; increment a counter by severity |

Example event:

~~~bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/json" \
  -d '{"source":"firewall-01","severity":"critical","message":"SSH brute force detected"}'
~~~

Allowed severity values: `info`, `warning`, `critical`. Invalid or extra fields are rejected by Pydantic. Accepted events are emitted as JSON log messages and increase `infrastructure_events_accepted_total{severity="..."}`.

> This is a demonstration API. Events are logged, not persisted to a database; the per-process metric counter is not shared between replicas.

## Run locally with Docker Compose

**Requirements:** Docker Desktop or a compatible Docker Engine with Compose.

~~~bash
git clone https://github.com/XBlasterX/Secure-Container-CI-CD-Platform.git
cd Secure-Container-CI-CD-Platform
docker compose up --build -d
~~~

| Service | Local URL |
|---|---|
| API | http://localhost:8080/healthz |
| API metrics | http://localhost:8080/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

~~~bash
curl -fsS http://localhost:8080/healthz
docker compose ps
docker compose down
~~~

Compose configuration uses the Docker DNS name `api:8000` for Prometheus, and binds exposed ports to `127.0.0.1`. The compose stack and the Kubernetes stack are **alternative local environments**; stop one before starting the other if ports or resources conflict.

## Run on local Kubernetes (kind)

**Requirements:** Docker running, `kind` and `kubectl` installed. On Apple Silicon, build for `linux/arm64`; choose the architecture matching your kind node.

~~~bash
kind create cluster --name secure-platform

# Build the image for the local cluster (Apple Silicon example).
docker build --platform linux/arm64 -t secure-api:k8s-v1 .
kind load docker-image secure-api:k8s-v1 --name secure-platform

kubectl --context kind-secure-platform apply -f k8s/namespace.yaml
kubectl --context kind-secure-platform apply -f k8s/deployment.yaml
kubectl --context kind-secure-platform apply -f k8s/service.yaml
kubectl --context kind-secure-platform apply -f k8s/monitoring/

kubectl --context kind-secure-platform -n secure-platform get deploy,pods,svc
~~~

The Kubernetes manifest references **`secure-api:k8s-v1` loaded into kind**, not an automatically pulled GHCR release. This is intentional for the local ARM64 lab.

API verification (in one terminal):

~~~bash
kubectl --context kind-secure-platform -n secure-platform \
  port-forward svc/secure-platform-service 8081:8000
~~~

In a second terminal:

~~~bash
curl -fsS http://localhost:8081/healthz
curl -fsS http://localhost:8081/readyz
curl -fsS http://localhost:8081/metrics
~~~

Monitoring access (run each port-forward in a separate terminal):

~~~bash
kubectl --context kind-secure-platform -n secure-platform \
  port-forward svc/prometheus-service 9090:9090

kubectl --context kind-secure-platform -n secure-platform \
  port-forward svc/grafana-service 3000:3000
~~~

In Prometheus, query `up{job="infrastructure-api"}` (expected `1` when scraping succeeds). Grafana has a provisioned datasource and a simple availability dashboard. A successful `up` measures **one configured scrape target**, not both API Pods individually.

For deployment prerequisites, monitoring behavior and known trade-offs, see [Architecture](documentation/ARCHITECTURE.md).

## CI pipeline and security gate

The workflow is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

| Job | Executes | Outcome |
|---|---|---|
| `app_test` | Checkout → Python 3.13 → dependencies → Ruff → Pytest | Stops bad application changes |
| `build_scan` | Buildx → Docker image → CycloneDX SBOM → Trivy → image artifact | Blocks on reported HIGH/CRITICAL vulnerabilities |
| `publish` | Download scanned image → load → tag → GHCR push | Executes only on a successful push to `main` |

The workflow also runs for pull requests and manual dispatch; **publication is restricted to pushes to `main`**. The `publish` job receives `packages: write`; test and scan jobs have read-only repository access.

The pipeline stores a downloadable `sbom` artifact and a Docker image artifact in its workflow run. It additionally generates an SPDX report, which is not uploaded as a dedicated artifact.

[View workflow runs and results](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml)

### Run quality checks locally

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[dev]"
python -m ruff check src tests
python -m pytest -q
~~~

## Security posture

Implemented controls include:
- Non-root container user (`UID 1000`), Kubernetes `runAsNonRoot` and `runAsUser`.
- `allowPrivilegeEscalation: false`, dropping all Linux capabilities and `RuntimeDefault` seccomp profile for FastAPI.
- Kubernetes readiness/liveness probes, resource requests and limits.
- Image vulnerability scanning that fails the build on detected HIGH/CRITICAL issues.
- SBOM output to support package inventory and later vulnerability investigation.
- Container publication restricted to a controlled event and a narrowly scoped token.

**Important limitations:** The vulnerability database and image dependencies change over time; scanning is a point-in-time check. GitHub Actions dependencies are version-tagged rather than all pinned to full commit digests; `pip` removal in a Docker layer does not remove its bytes from earlier layers. Kubernetes monitoring resources do not currently implement equivalent security contexts and resource controls, and the API Pod does not explicitly disable ServiceAccount-token automounting. See [Security review & improvement backlog](documentation/SECURITY.md).

## Current limitations / next improvements

1. **Kubernetes rollout is manual.** There is no Argo CD, Flux or GitHub-to-cluster deployment automation.
2. **Monitoring is service-based.** Prometheus scrapes `secure-platform-service:8000`, not each Pod via Kubernetes service discovery. Per-replica counters can therefore be incomplete or inconsistent.
3. **Metrics and dashboards are lab-grade.** No durable Kubernetes Prometheus/Grafana storage and no Alertmanager notification routing; the configured alert is only a Prometheus rule.
4. **Images and actions:** GHCR currently publishes the runner's build architecture; Kubernetes on Apple Silicon uses a separate local ARM64 build. Multi-platform builds and pinned digests remain future work.
5. **Security hardening:** Apply consistent Pod security and credentials management to the monitoring stack, use immutable digests, pin GitHub Actions, review remaining package/layer risks and validate the full stack from a clean checkout.
6. **Repository hygiene:** Remove checked-in `build/`, `*.egg-info/` and large generated JSON reports from normal source tracking; retain curated reports or links only as evidence.

These boundaries are intentional disclosures of current implementation, not claims of production readiness.

## Evidence and source

- [GitHub Actions – build, scan, publish](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/workflows/ci.yml)
- [Kubernetes manifests](k8s/) · [Prometheus / Grafana manifests](k8s/monitoring/)
- [API and tests](src/) · [Test suite](tests/)
- [Docker Compose](compose.yaml) · [Dockerfile](Dockerfile)
- [Architecture & decisions](documentation/ARCHITECTURE.md) · [Security assessment](documentation/SECURITY.md)

### Interview talking points

- **Why publish a saved image instead of rebuilding?** GitHub jobs run on isolated runners; saving/loading preserves the scanned image across the security gate.
- **Why use readiness and liveness separately?** Readiness controls whether a Pod receives Service traffic, while liveness controls restart decisions.
- **Why not claim automated Kubernetes CD?** The workflow ends at GHCR; the local kind image and manifests are applied manually.
- **Why Alpine?** In the tested environment it reduced Trivy findings. That is a measurable result, not a universal security guarantee.

---

*Personal learning/portfolio lab built to practise CI/CD, container security, Kubernetes and observability with explicit engineering trade-offs.*
