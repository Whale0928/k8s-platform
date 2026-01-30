# Envoy Gateway

Kubernetes Gateway API + Envoy Gateway.
ingress-nginx와 병렬 운영으로 점진적 마이그레이션.

## 현재 상태

| 컴포넌트 | 상태 | 비고 |
|----------|------|------|
| Gateway | Programmed | main-gateway |
| Envoy Proxy | 2 replicas | arm64 노드 |
| GatewayClass | Accepted | envoy |

## 네트워크 구성

| 서비스 | External IP | 포트 | 용도 |
|--------|-------------|------|------|
| ingress-nginx | 100.77.210.2, 100.88.239.24 | 80, 443 | 프로덕션 |
| envoy-gateway | 100.77.210.2, 100.88.239.24 | 8080 | 테스트 |

## 파일

| 파일 | 설명 |
|------|------|
| `kustomization.yaml` | Envoy Gateway v1.2.6 + arm64 nodeSelector patch |
| `envoyproxy.yaml` | Envoy Proxy Pod 설정 (arm64, replicas:2, anti-affinity) |
| `gatewayclass.yaml` | GatewayClass → EnvoyProxy 연결 |
| `gateway.yaml` | Main Gateway (HTTP 8080) |

## ClusterIssuer

| Issuer | 용도 | Challenge 경로 |
|--------|------|---------------|
| `letsencrypt-prod` | NGINX Ingress | HTTP-01 → :80 |
| `letsencrypt-gateway` | Gateway API | HTTP-01 → :8080 |

## 테스트 방법

```bash
# 1. Gateway 상태 확인
kubectl get gateway -n envoy-gateway-system

# 2. Envoy Pod 확인
kubectl get pods -n envoy-gateway-system

# 3. 서비스 IP 확인
kubectl get svc -n envoy-gateway-system

# 4. HTTPRoute 테스트 (예: uptime-kuma)
kubectl apply -f - <<EOF
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: test-route
  namespace: uptime-kuma
spec:
  parentRefs:
  - name: main-gateway
    namespace: envoy-gateway-system
  hostnames:
  - test.example.com
  rules:
  - backendRefs:
    - name: uptime-kuma
      port: 80
EOF

# 5. 테스트 요청
curl -H "Host: test.example.com" http://100.77.210.2:8080
```

## HTTPS 활성화 (TODO)

인증서 설정 후 gateway.yaml에 HTTPS 리스너 추가:

```yaml
listeners:
  - name: https
    protocol: HTTPS
    port: 8443
    tls:
      mode: Terminate
      certificateRefs:
        - kind: Secret
          name: example-tls
          namespace: envoy-gateway-system
    allowedRoutes:
      namespaces:
        from: All
```

## 마이그레이션 순서

1. ✅ Gateway 설치 (8080 포트)
2. ⬜ 테스트 서비스로 HTTPRoute 검증
3. ⬜ HTTPS 리스너 추가 (8443)
4. ⬜ 낮은 우선순위 서비스 전환
5. ⬜ 프로덕션 서비스 전환
6. ⬜ 포트 스왑 (8080→80, 8443→443)
7. ⬜ NGINX Ingress 제거

## 트러블슈팅

### CRD 버전 충돌
기존 Gateway API CRD와 Envoy Gateway CRD 버전 불일치 시:
```bash
kubectl delete crd backendtlspolicies.gateway.networking.k8s.io tlsroutes.gateway.networking.k8s.io
argocd app sync platform
```

### Pod이 amd64 노드에 배치됨
EnvoyProxy CRD의 nodeSelector 확인:
```bash
kubectl get envoyproxy -n envoy-gateway-system -o yaml | grep -A5 nodeSelector
```
