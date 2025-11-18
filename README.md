# k8s-platform

Personal Kubernetes platform infrastructure for all projects.

## Components

| Component     | Purpose              |
|---------------|----------------------|
| ArgoCD        | GitOps 배포 자동화        |
| Ingress Nginx | 트래픽 라우팅 및 로드밸런싱      |
| Cert-Manager  | SSL 인증서 자동 관리        |
| Monitoring    | 통합 모니터링 (LGTM Stack) |

## Structure

```
k8s-platform/
├── apps/                    # ArgoCD Applications
│   ├── argocd.yaml         # ArgoCD 자체 관리
│   └── platform.yaml       # 플랫폼 인프라 통합 (cert-manager, ingress-nginx, monitoring)
├── argocd/                  # ArgoCD 설정 (OAuth, RBAC)
└── platform/                # 플랫폼 인프라
    ├── cert-manager/       # SSL 인증서
    ├── ingress-nginx/      # Ingress Controller
    └── monitoring/         # LGTM Stack
```

## Usage

Deploy via ArgoCD:

```bash
kubectl apply -k apps/
```

## Managed Projects

- [bottle-note](https://github.com/bottle-note/environment-variables)
