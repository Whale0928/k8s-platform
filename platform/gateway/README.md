# Gateway (Envoy Gateway)

## 현재 상태

HAProxy가 공개 노드의 80/443 TCP 트래픽을 PROXY Protocol v2로 전달하고,
Envoy Gateway가 TLS 종료와 Gateway API(HTTPRoute) 라우팅을 처리한다.
와일드카드 인증서는 DNS-01(Cloudflare, Route53)로 발급/갱신된다.

| 프로토콜 | 포트 |
|----------|------|
| HTTP | 80 |
| HTTPS | 443 |

## 파일 구성

| 파일 | 설명 |
|------|------|
| gateway.yaml | Gateway 리소스 (HTTP 리스너 정의) |
| gatewayclass.yaml | GatewayClass 정의 |
| envoyproxy.yaml | EnvoyProxy 설정 (arm64 노드 배치 등) |
| haproxy-daemonset.yaml | 공개 노드에 배치하는 HAProxy DaemonSet |
| haproxy.cfg | TCP passthrough 및 PROXY Protocol v2 설정 |
| client-traffic-policy.yaml | PROXY Protocol 수신 및 XFF 정제 정책 |
| certificate.yaml | 와일드카드 인증서 (DNS-01) |
| kustomization.yaml | Kustomize 구성 |
| patches/ | 도메인별 HTTPS 리스너 패치 |
