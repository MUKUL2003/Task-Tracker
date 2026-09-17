# Task Tracker — Kubernetes Infrastructure Project

A deliberately small application (FastAPI + PostgreSQL) used as a vehicle to build and operate a real, multi-node Kubernetes cluster from scratch. The app itself is intentionally minimal — a task list with a REST API — so the actual subject of this project is everything underneath it: cluster networking, workload security, scaling, packaging, and image distribution.

Everything runs on a local [kind](https://kind.sigs.k8s.io/) cluster (3 nodes: 1 control-plane + 2 workers), built up incrementally, with each layer added and verified on its own before moving to the next.

## What this project actually demonstrates

**Cluster & networking**
- Multi-node kind cluster with a custom CNI ([Calico](https://www.tigera.io/project-calico/)) replacing the default `kindnetd`, specifically to enable `NetworkPolicy` enforcement
- `nginx-ingress` controller with path-based routing and URL rewriting, exposed via `NodePort` (required once Calico replaced the default CNI, since Calico doesn't implement `hostPort` forwarding out of the box)
- Two `NetworkPolicy` resources restricting backend and frontend pods to only accept traffic from the ingress controller — verified by confirming direct pod-to-pod traffic is actually blocked, not just assumed

**Workload configuration**
- `ConfigMap` and `Secret` for environment-specific and sensitive configuration, injected as env vars
- `PersistentVolumeClaim` so Postgres data survives pod restarts and rescheduling
- Readiness and liveness probes driving self-healing and safe rollout behavior
- `HorizontalPodAutoscaler` scaling the backend on real CPU metrics via `metrics-server`

**Security**
- Dedicated `ServiceAccount` per workload, with no `Role` bound and `automountServiceAccountToken: false` — verified directly by confirming no API token exists inside any container's filesystem, and that each ServiceAccount can perform zero API actions

**Image delivery**
- A local Docker registry (not `kind load docker-image`) with containerd on every node configured to pull from it — the same pull-based mechanism a real cluster uses against a real registry

**Packaging**
- The full manifest set converted into a Helm chart (`task-tracker-chart/`), parameterizing image references, replica counts, and resource limits through `values.yaml`

## Architecture

```
Browser
  │
  ▼
localhost:8080 (kind control-plane node, NodePort)
  │
  ▼
nginx-ingress controller ── path: /api/*  ──► backend-service ──► backend pods (FastAPI) ──► postgres-service ──► postgres pod
                       └── path: /*       ──► frontend-service ──► frontend pods (static HTML/JS)
```

Calico enforces NetworkPolicy across all pod-to-pod traffic; kube-proxy handles Service routing; metrics-server feeds the backend's HPA.

## Repository structure

```
backend/            FastAPI app + Dockerfile
frontend/            Static HTML/JS + Dockerfile
k8s/                  Raw manifests, applied individually (kept for reference)
task-tracker-chart/   Helm chart covering the same resources, parameterized
kind-config.yaml       Cluster topology, CNI, and port mapping config
```

The `k8s/` manifests and the Helm chart currently describe the same system — the chart is the direction this project is moving toward as the single source of deployment truth.

## Running it locally

```bash
kind create cluster --name tasktracker --config kind-config.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/custom-resources.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# build + push images to the local registry, then either:
kubectl apply -f k8s/           # raw manifests
# or
helm install task-tracker ./task-tracker-chart -n task-tracker --create-namespace -f values.yaml -f values-secrets.yaml
```

App available at `http://localhost:8080`.

## Roadmap

- [x] Multi-node cluster, Ingress, ConfigMap/Secret, PVC, probes, HPA
- [x] Calico + NetworkPolicy
- [x] RBAC (ServiceAccounts, verified zero-permission)
- [x] Local image registry
- [x] Helm chart
- [ ] Observability — Prometheus, Grafana dashboards, Alertmanager
- [ ] GitOps — ArgoCD syncing the Helm chart from this repo