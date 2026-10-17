# Architecture & engineering decisions

[← Project README](../README.md)

## Boundaries and data flow

The project has two **local** runtime environments and one **remote** build/publish pipeline:

1. **Docker Compose:** FastAPI, Prometheus and Grafana run as separate containers on a user-defined bridge network. Prometheus scrapes `api:8000`; ports are loopback-bound.
2. **GitHub Actions → GHCR:** `app_test` gates `build_scan`, which builds a local Docker image, generates an SBOM, scans it, and uploads a TAR artifact. `publish` runs only on successful pushes to `main`, downloads the TAR and pushes the already-scanned image under a full-commit-SHA tag.
3. **kind (Kubernetes in Docker):** A separately built local image (`secure-api:k8s-v1`) is loaded to the kind node. Two FastAPI Pod replicas are managed by a Deployment and reached through a ClusterIP Service. Prometheus and Grafana run in their own Pods with ConfigMap-mounted configurations.

**These are not three apps in one container.** The FastAPI runtime image contains the API. Prometheus and Grafana use their upstream container images.

## Runtime traffic

~~~text
Client --kubectl port-forward--> Kubernetes ClusterIP Service (:8000)
                                      |
                              selects app=secure-platform
                                      |
                               FastAPI Pod x 2
                               /healthz, /readyz
                               /events, /metrics

Prometheus Pod --HTTP scrape--> secure-platform-service:8000
      |
      +--> time-series data / up{job="infrastructure-api"}
      +--> APIMetricsUnavailable rule (no notifier configured)

Grafana Pod --> prometheus-service.secure-platform.svc.cluster.local:9090
~~~

Service DNS and Pod selection are distinct concepts. Service names provide stable discovery even when Pods are replaced and Pod IPs change. A successful `up=1` currently demonstrates reachability of the Service scrape target, **not independently healthy replicas**. For accurate per-Pod metrics, migrate to Kubernetes SD, a headless Service or Prometheus Operator targets.

## Kubernetes resource inventory

| Manifest | Resources | Purpose |
|---|---|---|
| `k8s/namespace.yaml` | Namespace | Isolates the lab's namespaced resources |
| `k8s/deployment.yaml` | Deployment | Two API replicas, liveness/readiness, CPU/memory requests & limits, hardened security context |
| `k8s/service.yaml` | ClusterIP Service | Stable in-cluster API endpoint |
| `k8s/monitoring/prometheus-monitoring.yaml` | ConfigMap, Deployment, Service | Prometheus config, availability rule, scrape endpoint |
| `k8s/monitoring/grafana-dashboard.yaml` | ConfigMap, Deployment, Service | Provisioned Grafana dashboard and Prometheus datasource |

### Health and rollout behavior

- `/readyz` determines whether a Pod can receive traffic through its Service.
- `/healthz` checks the container's ongoing health for restart decisions.
- Deployment's two replicas and default rolling-update strategy reduce planned disruption, but do **not** establish guaranteed zero downtime.
- Kubernetes rollout operations are manual. The repository does not include a GitOps controller or a CI deployment job.

## Why these choices?

| Choice | What it demonstrates | Trade-off |
|---|---|---|
| FastAPI and Pydantic | Small, testable API with strict input validation | Demo event data is not durable |
| Docker Compose | Local stack that can be started quickly | Does not model Kubernetes orchestration |
| Alpine Python runtime | Reduced detected findings in a specific security scan | musl compatibility must be validated for dependencies; future vulnerabilities remain possible |
| Trivy severity gate | Release blocking on HIGH/CRITICAL findings | Scanner results need context and regular updates |
| Build artifact passed between GitHub jobs | Same image is scanned and published | TAR artifact adds storage/time overhead |
| kind | Kubernetes API/behavior without EKS costs | Cluster is local and ephemeral |
| ClusterIP + port-forward | Restricts casual external reachability | Not a production ingress/TLS setup |
| Prometheus + Grafana | Instrumentation and visualization | Service-level scrape does not cover replicas independently |

## Reproduction / troubleshooting

~~~bash
# Verify active context before applying anything:
kubectl config current-context
kubectl --context kind-secure-platform -n secure-platform get deploy,pods,svc

# Diagnose unsuccessful pods:
kubectl --context kind-secure-platform -n secure-platform describe pod <pod-name>
kubectl --context kind-secure-platform -n secure-platform logs deployment/secure-platform-deployment

# Verify API rollout:
kubectl --context kind-secure-platform -n secure-platform rollout status deployment/secure-platform-deployment
~~~

Common mistakes in this lab:
- **Port-forward failure:** `-p HOST:CONTAINER`, or `kubectl port-forward LOCAL:REMOTE`; the API listens on container port 8000.
- **Pod has no image:** Local kind nodes do not automatically see images in Docker Desktop; `kind load docker-image` first, and match the node architecture.
- **Deployment selector immutable:** Once created, `spec.selector` cannot be changed in place. Keep Deployment selector, Pod labels and Service selector consistent.
- **Prometheus returns `up=0`:** Check `/targets` and make sure the Kubernetes ConfigMap uses `secure-platform-service:8000` instead of the Docker Compose hostname `api:8000`.
- **Grafana has no data:** Its datasource must point to `prometheus-service` (or its fully qualified DNS name), not `localhost` from inside the Grafana Pod.

## Operational constraints

The existing Kubernetes manifests do not provide persistent volumes for Prometheus or Grafana. Data can be lost if a Pod is replaced. The Prometheus alert rule is loaded but there is no notification delivery system. Monitoring images have no documented availability guarantees and the Grafana/Prometheus manifests have fewer workload hardening controls than the API Deployment.

**Next hardening steps:** independent Pod scraping, stronger security contexts and resource requests on monitoring workloads, ServiceAccount token controls, Kubernetes Secrets and admin-password management, persistent volumes, a multi-architecture immutable image publication strategy and (if desired) an explicit deployment pipeline.

See [Security review](SECURITY.md) for the security-specific backlog.
