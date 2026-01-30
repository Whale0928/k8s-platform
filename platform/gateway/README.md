# Envoy Gateway

Kubernetes Gateway API + Envoy Gateway.
ingress-nginx와 병렬 운영으로 점진적 마이그레이션.

## 파일

| 파일 | 설명 |
|------|------|
| `kustomization.yaml` | Envoy Gateway v1.2.6 + nodeSelector patch |
| `envoyproxy.yaml` | Envoy Proxy Pod 설정 (arm64, replicas:2) |
| `gatewayclass.yaml` | GatewayClass 정의 |
| `gateway.yaml` | Main Gateway (8080/8443) |

## 포트

| 서비스 | 포트 | 용도 |
|--------|------|------|
| ingress-nginx | 80, 443 | 프로덕션 |
| envoy-gateway | 8080, 8443 | 테스트 |

## 활성화

`platform/kustomization.yaml`:
```yaml
resources:
  - gateway  # 주석 해제
```

## ClusterIssuer

- `letsencrypt-gateway-staging` (테스트)
- `letsencrypt-gateway` (프로덕션)
