# Envoy Gateway 설정 시행착오 기록

## 목표
- Kubernetes Gateway API를 사용한 HTTP 트래픽 처리
- Zot Container Registry를 위한 HTTPRoute 설정
- docker-registry.bottle-note.com, docker-registry.kr-filter.com 두 도메인 지원

## 시행착오 요약

### 1. Gateway API CRD 누락
- Envoy Gateway install.yaml에 HTTPRoute CRD가 포함되어 있지만, 기존 클러스터에 일부 CRD만 설치되어 있었음
- 해결: `kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/standard-install.yaml`

### 2. 포트 충돌 (ingress-nginx와)
- ingress-nginx가 80, 443 포트 사용 중
- Gateway도 동일 포트 사용 시 svclb pod 스케줄링 실패
- 해결: Gateway 포트를 8080, 8443으로 변경

### 3. 외부 접근 불가 (노드 문제)
- Envoy Gateway Pod이 pve-pod-1 (amd64, Tailscale 전용)에서 실행됨
- 외부 공인 IP 접근 가능한 노드: instance-node-1,2,3 (arm64)
- 해결 필요: arm64 노드에서 실행되도록 nodeSelector 설정

### 4. nodeSelector 설정 방법
두 가지 Pod이 있음:
1. `envoy-gateway` (컨트롤러) - kustomize patch로 nodeSelector 적용 가능
2. `envoy-*-main-gateway` (트래픽 처리) - Gateway가 동적 생성, EnvoyProxy CRD 또는 GatewayClass parametersRef로 설정 필요

### 5. 시도했던 방법들
- kustomize remote URL 참조 + patch: 컨트롤러만 적용됨
- EnvoyProxy CRD: Gateway가 생성하는 Pod에 nodeSelector 적용 가능
- GatewayClass parametersRef → EnvoyProxy 참조: 동일 효과
- install.yaml 직접 다운로드 후 수정: 모든 리소스 직접 관리 가능

## 다음 단계 (TODO)
1. install.yaml 다운로드하여 직접 관리 (ingress-nginx 방식)
2. Deployment에 nodeSelector 추가: `kubernetes.io/arch: arm64`
3. EnvoyProxy CRD로 Gateway가 생성하는 Envoy Proxy Pod에도 nodeSelector 적용
4. 외부 서버(193.123.252.37)에서 포트 포워딩 설정 필요할 수 있음

## 노드 정보
| 노드 | 아키텍처 | 외부 접근 |
|------|----------|----------|
| instance-node-1,2 | arm64 | 158.179.171.39 |
| instance-node-3 | arm64 | 193.123.252.37 |
| pve-pod-1 | amd64 | Tailscale만 |

## Envoy Gateway 버전
- v1.6.1 (EOL: 2026/05/13)
- arm64, amd64 모두 지원