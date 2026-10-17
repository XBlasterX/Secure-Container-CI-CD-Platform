# Verification evidence

[← Project README](../README.md) · [Architecture](ARCHITECTURE.md) · [Security](SECURITY.md)

## Reviewed snapshot

Reviewed on **17 October 2026** at commit [`ba7fe4e2f3bf5261d036a3e8198345f33c71e25e`](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/commit/ba7fe4e2f3bf5261d036a3e8198345f33c71e25e). Observations below come from source files, job logs, step conclusions and artifact metadata for [CI run #19](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/runs/39051900362), attempt 1, triggered by a push to `main` at 17:00:59 UTC.

This is a dated result, not a live status report. Earlier workflow commits and a green overall badge do not independently establish runtime behavior.

## Tests executed

[`app_test` job and logs](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/runs/39051900362/job/117452013460):

- `python -m ruff check src tests`: **All checks passed**.
- `python -m pytest -q`: **13 passed, 1 warning in 0.61s**.
- The warning concerns deprecated `httpx` usage by Starlette's `TestClient`; the run passed with that warning.

The [test suite](../tests/main_test.py) uses FastAPI's in-process `TestClient`. It checks health/readiness/version responses, an unknown route, valid and invalid event inputs, the metrics endpoint and event counter behavior. It does not start Uvicorn in the built image or exercise Docker networking, Compose, Kubernetes, Prometheus or Grafana.

## Build, scan and SBOM results

[`build_scan` job and logs](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/runs/39051900362/job/117452071653):

| Operation | Observed result | Limit |
| --- | --- | --- |
| Docker build | `image:latest` built and loaded for `linux/amd64`; log records Python Alpine and Alpine 3.24.2 | Build success does not prove the image starts or its health check passes |
| Trivy vulnerability gate | Trivy 0.76.0 completed successfully; the filtered report shows 0 HIGH/CRITICAL vulnerabilities for the listed OS and Python package targets | `severity: CRITICAL,HIGH`, `exit-code: 1`, `ignore-unfixed: false`; this is not a claim of zero vulnerabilities at every severity |
| CycloneDX SBOM | `sbom.json` generated and uploaded as artifact `sbom` (ID `12108206036`) | Artifact existence does not establish inventory completeness or SBOM validation |
| SPDX SBOM | The `sbom.spdx` generation step succeeded | No workflow step uploads that file |
| Image handoff | `image.tar` saved and uploaded as `docker-image` (ID `12107972657`) after the scan passed | Prometheus and Grafana images from Compose are not scanned by this job |

The Dockerfile configures a non-root user (UID 1000) and a Docker `HEALTHCHECK` against `/healthz`. Neither is exercised as a runtime assertion by the reviewed workflow. Scanner results depend on the image, scanner/database versions and scan date; they do not establish general runtime security.

## Image publication

[`publish` job and logs](https://github.com/XBlasterX/Secure-Container-CI-CD-Platform/actions/runs/39051900362/job/117452320812) successfully downloaded and loaded `docker-image`, tagged the loaded image and completed `docker push`. There is no rebuild in this job.

- Published reference: `ghcr.io/xblasterx/secure-container-ci-cd-platform:sha-ba7fe4e2f3bf5261d036a3e8198345f33c71e25e`
- Registry digest reported by `docker push`: `sha256:1201e7f8b0ad27e97e7985227eb690dc280cd839a4920543f700d736ef10d146`
- The uploaded and downloaded image artifact ZIP digests match in the logs: `sha256:5a096c092c596f80eaf9f30d72101954d42cf76e48ede3cf0c5547774d22094d`. This is an **artifact archive digest**, distinct from the registry manifest digest above.

This confirms publication in that run. It does not confirm a later registry pull, anonymous package access, container startup or a deployment. Publication is conditional on a successful push to `main`; this push run does not exercise the pull-request or manual-dispatch paths.

## Service readiness and monitoring

[Compose](../compose.yaml) builds the API from the local checkout and uses separate upstream Prometheus and Grafana images. Its bridge network, localhost port bindings, monitoring configuration mounts and named data volumes are source configuration. The workflow contains no `docker run`, `docker compose up`, HTTP smoke test or `kubectl` deployment step.

In [the application](../src/main.py), `/healthz` and `/readyz` return fixed JSON responses. The tests confirm those responses in-process; they do not establish dependency readiness. A running container status alone does not confirm that all three services are ready.

Compose Prometheus is configured to scrape `api:8000` every 15 seconds. Kubernetes monitoring uses the API Service as a target. `up=1` for that Service would demonstrate successful scraping of the target, not independent health of both API replicas. The repository contains an availability alert rule; the reviewed CI does not demonstrate rule evaluation or notification delivery.

## Scenarios without evidence in the reviewed run

These are pending verification items, not claims that the scenarios fail or have never been tested elsewhere. Record the tested commit/image digest, environment, command, expected result and actual output before marking an item verified.

| Scenario | Evidence required |
| --- | --- |
| Published image startup | Pull the recorded registry digest, start it, capture health status and HTTP results for `/healthz`, `/readyz` and `/events`; state the tested CPU architecture |
| Fresh Compose stack | Validate Compose configuration, build/start a clean stack and capture API health plus Prometheus `/-/ready` and Grafana `/api/health` responses |
| Monitoring integration | Submit an event, show the counter in Prometheus and the corresponding Grafana panel; retain output tied to the running image |
| Runtime identity and controls | Capture the API process UID and effective runtime controls; verify Kubernetes security settings on the actual Pods |
| kind deployment and replica readiness | Capture rollout status, two ready Pods, their image identities and HTTP results; a Service response alone is insufficient |
| Alert behavior | Show the rule entering the expected state during a controlled outage; notification delivery requires a configured receiver and separate evidence |
| Failure handling and recovery | Exercise a failing lint/test/scan gate, confirm publication is blocked, and verify the intended restart or rollback behavior |
| PR and manual triggers | Inspect runs for those event types, including the expected skipped `publish` job; the reviewed run is a push |
| ARM64 / multi-architecture image | Build and run the relevant image on that architecture; the reviewed CI image is linux/amd64 |

A locally built Compose or kind image is a separate artifact from the scanned GHCR image. Its runtime observations must not be presented as tests of the published digest unless that exact image is used.
