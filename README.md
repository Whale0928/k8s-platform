# k8s-platform

Personal Kubernetes platform infrastructure for all projects.

## Components

| Component | Purpose |
|-----------|---------|
| ArgoCD | GitOps 배포 자동화 |
| Ingress Nginx | 트래픽 라우팅 및 로드밸런싱 |
| Cert-Manager | SSL 인증서 자동 관리 |
| Monitoring | 통합 모니터링 (LGTM Stack) |

## Structure

```
k8s-platform/
├── argocd/
├── cert-manager/
├── ingress-nginx/
├── cluster-issuer/
└── monitoring/
```

## Usage

Deploy via ArgoCD:

```bash
kubectl apply -f argocd-app.yaml
```

## Managed Projects

- [bottle-note](https://github.com/bottle-note/environment-variables)
