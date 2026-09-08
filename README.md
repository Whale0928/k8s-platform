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
│   │   Public IP     │  │   Public IP     │  │   Public IP     │ │
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

| Component          | Purpose                          | Node Affinity                      |
|--------------------|----------------------------------|------------------------------------|
| ArgoCD             | GitOps 배포 자동화 + Discord 알림 | arm64 (repo-server, redis는 amd64) |
| HAProxy            | 원본 IP 보존용 TCP ingress (80/443) | instance-node-1, instance-node-2 |
| Envoy Gateway      | Gateway API 기반 트래픽 라우팅 (80/443) | arm64                         |
| Cert-Manager       | SSL 인증서 자동 관리 (DNS-01)     | -                                  |
| External-Secrets   | 1Password 시크릿 동기화           | amd64                              |
| Image Updater      | 컨테이너 이미지 자동 업데이트      | amd64                              |
| Container-Registry | OCI 컨테이너 레지스트리 (Zot)     | amd64                              |
| Uptime Kuma        | 서비스 상태 모니터링               | amd64                              |
| Redis Operator     | Redis Replication/Cluster 관리   | arm64/amd64 (멀티아치)              |
| Monitoring         | 통합 모니터링 (LGTM Stack)        | 비활성화                            |

### Redis Operator 참고사항

- **Opstree redis-operator v0.24.0** 기반, CRD: `RedisReplication`, `RedisCluster`, `RedisSentinel`
- 현재 bottlenote-development에 `RedisReplication` (master 1 + replica 2) 구성
- **Sentinel 미적용 상태**: Master Pod 장애 시 StatefulSet이 Pod를 재생성하지만 자동 failover(Replica 승격)는 되지 않음. 쓰기 불가 시간이 발생할 수 있음
- 자동 failover가 필요하면 `RedisSentinel` CRD를 추가 배포해야 함

## Structure

```
k8s-platform/
├── apps/                    # ArgoCD Applications
│   ├── argocd.yaml         # ArgoCD 자체 관리
│   └── platform.yaml       # 플랫폼 인프라 통합
├── argocd/                  # ArgoCD 설정 (OAuth, RBAC, Notifications)
└── platform/                # 플랫폼 인프라
    ├── cert-manager/       # SSL 인증서 (DNS-01 ClusterIssuer)
    ├── gateway/            # Envoy Gateway (리스너, 인증서, 패치)
    ├── monitoring/         # LGTM Stack (비활성화)
    ├── external-secrets/   # 1Password Connect (amd64)
    ├── image-manager/      # ArgoCD Image Updater
    ├── container-registry/ # Zot OCI Registry (amd64)
    ├── coredns/            # CoreDNS 설정
    └── redis-operator/     # Redis Operator (Opstree v0.24.0)
```

## Traffic Flow

```
Client -> DNS -> Public IP (Oracle Cloud arm64 nodes)
  -> HAProxy (TCP passthrough + PROXY Protocol v2)
    -> Envoy Gateway (ClusterIP, TLS termination)
      -> HTTPRoute matching
        -> Backend Service (ClusterIP)
```

## Gateway Listeners & Certificates

| Listener | Hostname | Certificate | DNS Provider |
|----------|----------|-------------|--------------|
| https-bottle-note-root | bottle-note.com | wildcard-bottle-note-tls | Route53 |
| https-bottle-note | *.bottle-note.com | wildcard-bottle-note-tls | Route53 |
| https-bottle-note-dev | *.development.bottle-note.com | wildcard-dev-bottle-note-tls | Route53 |
| https-bottle-note-product | *.product.bottle-note.com | wildcard-product-bottle-note-tls | Route53 |
| https-dead-whale | *.dead-whale.org | wildcard-dead-whale-tls | Cloudflare |
| https-kr-filter | *.kr-filter.com | wildcard-kr-filter-tls | Cloudflare |
| https-profanity-kr-filter | *.profanity.kr-filter.com | wildcard-profanity-kr-filter-tls | Cloudflare |

## Managed Services

| Service | Domain | Namespace |
|---------|--------|-----------|
| Bottlenote API (prod) | api.product.bottle-note.com | bottlenote-production |
| Bottlenote Admin API (prod) | admin-api.bottle-note.com | bottlenote-production |
| Bottlenote Admin Dashboard (prod) | admin.bottle-note.com | bottlenote-production |
| Bottlenote Frontend (prod) | bottle-note.com | bottlenote-production |
| Bottlenote API (dev) | api.development.bottle-note.com | bottlenote-development |
| Bottlenote Admin API (dev) | admin-api.development.bottle-note.com | bottlenote-development |
| Bottlenote Admin Dashboard (dev) | admin.development.bottle-note.com | bottlenote-development |
| Bottlenote Frontend (dev) | development.bottle-note.com | bottlenote-development |
| Profanity Filter API | api.profanity.kr-filter.com | profanity-production |
| Docker Registry | docker-registry.bottle-note.com | container-registry |

## Node Workload Distribution

### arm64 nodes (Oracle Cloud)

- Envoy Gateway (외부 트래픽 진입점, 80/443)
- ArgoCD 핵심 컴포넌트 (server, controller)
- 공인 IP가 필요한 서비스

### amd64 nodes (Proxmox Homelab)

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
