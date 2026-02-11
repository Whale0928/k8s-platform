# k8s-platform

Personal Kubernetes platform infrastructure for all projects.

## Cluster Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     K3s Cluster (Tailscale VPN)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│   │ instance-node-1 │  │ instance-node-2 │  │ instance-node-3 │ │
│   │   Oracle Cloud  │  │   Oracle Cloud  │  │   Oracle Cloud  │ │
│   │ control-plane   │  │ control-plane   │  │ control-plane   │ │
│   │     arm64       │  │     arm64       │  │     arm64       │ │
│   │   Public IP ✓   │  │   Public IP ✓   │  │   Public IP ✓   │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│   ┌─────────────────┐  ┌─────────────────┐                      │
│   │    pve-pod-1    │  │    pve-pod-2    │                      │
│   │ Proxmox Homelab │  │ Proxmox Homelab │                      │
│   │     worker      │  │     worker      │                      │
│   │     amd64       │  │     amd64       │                      │
│   │ Tailscale Only  │  │ Tailscale Only  │                      │
│   └─────────────────┘  └─────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Components

| Component          | Purpose                     | Node Affinity                     |
|--------------------|-----------------------------|-----------------------------------|
| ArgoCD             | GitOps 배포 자동화 + Discord 알림  | arm64 (repo-server, redis는 amd64) |
| Ingress Nginx      | 트래픽 라우팅 및 로드밸런싱             | arm64 (Public IP 필요)              |
| Envoy Gateway      | Gateway API 기반 트래픽 관리 `[진행중]` | arm64                             |
| Cert-Manager       | SSL 인증서 자동 관리               | -                                 |
| External-Secrets   | 1Password 시크릿 동기화           | amd64                             |
| Image Updater      | 컨테이너 이미지 자동 업데이트            | amd64                             |
| Container-Registry | OCI 컨테이너 레지스트리 (Zo          | amd64                             |
| Uptime Kuma        | 서비스 상태 모니터링                 | amd64                             |
| Monitoring         | 통합 모니터링 (LGTM Stack)        | 비활성화                              |

## Structure

```
k8s-platform/
├── apps/                    # ArgoCD Applications
│   ├── argocd.yaml         # ArgoCD 자체 관리
│   └── platform.yaml       # 플랫폼 인프라 통합
├── argocd/                  # ArgoCD 설정 (OAuth, RBAC, Notifications)
└── platform/                # 플랫폼 인프라
    ├── cert-manager/       # SSL 인증서
    ├── ingress-nginx/      # Ingress Controller (arm64)
    ├── gateway/            # Envoy Gateway [진행중]
    ├── monitoring/         # LGTM Stack (비활성화)
    ├── external-secrets/   # 1Password Connect (amd64)
    ├── image-manager/      # ArgoCD Image Updater
    ├── container-registry/ # Zot OCI Registry (amd64)
    └── uptime-kuma/        # 서비스 모니터링 (amd64)
```

## Node Workload Distribution

### arm64 노드 (Oracle Cloud)

- Ingress Controller (외부 트래픽 진입점)
- Envoy Gateway (Gateway API, 8080 포트)
- ArgoCD 핵심 컴포넌트 (server, controller)
- 공인 IP가 필요한 서비스

### amd64 노드 (Proxmox Homelab)

- ArgoCD repo-server, redis
- ArgoCD Image Updater
- 1Password Connect
- Zot Container Registry
- Uptime Kuma
- 내부 통신 전용 서비스

## Usage

Deploy via ArgoCD:

```bash
kubectl apply -k apps/
```

## New Node Setup (Homelab)

Tailscale VPN 환경에서 새 노드 추가 시 필수 설정:

```bash
# 1. config.yaml 생성
sudo mkdir -p /etc/rancher/k3s
echo "flannel-iface: tailscale0" | sudo tee /etc/rancher/k3s/config.yaml

# 2. Tailscale netfilter 설정
sudo tailscale set --netfilter-mode=nodivert

# 3. k3s-agent 설치 (Tailscale IP 사용)
curl -sfL https://get.k3s.io | K3S_URL=https://<server>:6443 K3S_TOKEN=<token> \
  INSTALL_K3S_EXEC="agent --node-ip=<tailscale-ip>" sh -
```

## Managed Projects

- [bottle-note](https://github.com/bottle-note/environment-variables)
- [profanity-filter](https://github.com/Whale0928/profanity-filter)
