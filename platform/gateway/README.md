# Envoy Gateway 설정

## 개요
Kubernetes Gateway API + Envoy Gateway를 사용한 HTTP 트래픽 처리.
ingress-nginx와 병렬 운영하여 점진적 마이그레이션 지원.

## 구성 파일

| 파일 | 설명 |
|------|------|
| `kustomization.yaml` | 리소스 오케스트레이션 |
| `00-namespace.yaml` | envoy-gateway-system 네임스페이스 |
| `10-envoyproxy.yaml` | Envoy Proxy Pod 설정 (nodeSelector) |
| `20-gatewayclass.yaml` | GatewayClass 정의 |
| `30-gateway.yaml` | Main Gateway (8080/8443) |

## 포트 설정

| 서비스 | 포트 | 용도 |
|--------|------|------|
| ingress-nginx | 80, 443 | 기존 프로덕션 |
| envoy-gateway | 8080, 8443 | 테스트/마이그레이션 |

마이그레이션 완료 후 Envoy Gateway를 80/443으로 전환.

## 노드 배치

ARM64 노드(instance-node-1,2,3)에 배치하여 공인 IP 접근 가능하도록 설정:
- `envoy-gateway` 컨트롤러: kustomize patch로 nodeSelector 적용
- `envoy-*` 프록시 Pod: EnvoyProxy CRD로 nodeSelector 적용

## 활성화

`platform/kustomization.yaml`에서 주석 해제:
```yaml
resources:
  - gateway  # 주석 해제
```

## 테스트

```bash
# Gateway 상태 확인
kubectl get gateway -n envoy-gateway-system

# Envoy Proxy Pod 확인
kubectl get pods -n envoy-gateway-system -l app.kubernetes.io/name=envoy

# 외부 IP 확인
kubectl get svc -n envoy-gateway-system

# HTTPRoute 테스트
curl -H "Host: test.example.com" http://<ENVOY-IP>:8080
```

## ClusterIssuer

Gateway API용 Let's Encrypt Issuer 사용:
- `letsencrypt-gateway-staging` (테스트)
- `letsencrypt-gateway` (프로덕션)

## 시행착오 기록 (이전)

### 1. Gateway API CRD 누락
- 해결: kustomization에 standard-install.yaml 포함

### 2. 포트 충돌 (ingress-nginx와)
- 해결: Gateway 포트를 8080, 8443으로 변경

### 3. 외부 접근 불가 (노드 문제)
- 해결: EnvoyProxy CRD + kustomize patch로 arm64 nodeSelector 적용

### 4. cert-manager Gateway API 미지원
- 해결: cert-manager v1.16.3 업그레이드 + feature gate 활성화
