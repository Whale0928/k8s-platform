# Gateway (Envoy Gateway)

## 현재 상태

Envoy Gateway가 Gateway API(HTTPRoute) 기반으로 트래픽을 처리하며,
nginx-ingress와 공존 중이다.

| 프로토콜 | 포트 | 비고 |
|----------|------|------|
| HTTP | 8080 | nginx 80 충돌 방지 |
| HTTPS | 444 | nginx 443 충돌 방지 (임시) |

와일드카드 인증서는 DNS-01(Cloudflare)로 발급되며, 포트와 무관하게 갱신된다.

## 포트 충돌 이슈

K3s ServiceLB는 동일 노드에서 같은 IP:port를 두 LoadBalancer 서비스가 바인딩할 수 없다.
nginx-ingress가 80/443을 점유 중이므로 envoy는 8080/444를 사용 중이다.

### 영향받는 서비스 (nginx-ingress 의존)

- bottlenote
- profanity
- container-registry

위 서비스들이 nginx Ingress 리소스를 사용 중이므로 즉시 제거 불가.

## 마이그레이션 계획

목표: nginx-ingress 완전 제거, envoy가 80/443을 직접 수신.

1. 기존 서비스를 Ingress → HTTPRoute로 하나씩 전환
2. 모든 서비스 전환 완료 확인
3. nginx-ingress 제거
4. envoy 포트 변경: 8080 → 80, 444 → 443
5. HTTP-01 ClusterIssuer 제거 (cluster-issuer.yaml, gateway-issuer.yaml)

## 파일 구성

| 파일 | 설명 |
|------|------|
| gateway.yaml | Gateway 리소스 (리스너 정의) |
| gatewayclass.yaml | GatewayClass 정의 |
| envoyproxy.yaml | EnvoyProxy 설정 (arm64 노드 배치 등) |
| certificate.yaml | 와일드카드 인증서 (DNS-01, Cloudflare) |
| kustomization.yaml | Kustomize 구성 |
