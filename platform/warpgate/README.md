# Warpgate (중앙 bastion)

warp-tech/warpgate 기반 중앙 접근 관제. 인증 + 타겟 화이트리스트로 내부 리소스 접근을
제어한다. 소스 IP 기반 제어는 이 클러스터에서 불가능(hostNetwork → ClusterIP SNAT)하며,
그 대체가 이 구성의 목적이다.

## 접속 경로

| 프로토콜 | 외부 | haproxy | Warpgate 리스너 |
|----------|------|---------|-----------------|
| 웹 UI | warpgate.dead-whale.org:443 | SNI 분기 | 8888 |
| PostgreSQL | warpgate.dead-whale.org:5432 | postgres-tcp | 55432 |
| SSH | warpgate.dead-whale.org:2222 | ssh-tcp | 2222 |

PostgreSQL 접속 형식 (TLS 필수):

```
postgresql://<유저>#<타겟명>:<비밀번호>@warpgate.dead-whale.org:5432/<db>?sslmode=require
```

## 구성 요소

- Deployment: `ghcr.io/warp-tech/warpgate` 단일 replica (SQLite — 절대 늘리지 말 것)
- initContainer가 최초 기동 시 `unattended-setup` 실행, 매 기동 시 cert-manager
  인증서(`warpgate-tls`)를 `/data`로 복사
- admin 비밀번호: 1Password home-lab 볼트 `warpgate-admin` → ExternalSecret
- Connect 토큰: home-lab 볼트 읽기 전용, sops 암호화 (`op-token-secret.sops.yaml`)

## 운영 메모

- **설정 파일은 PVC 안에 있다** (`/data/warpgate.yaml`). 리스너/포트 변경은
  `kubectl exec`로 수정 후 `kubectl rollout restart deploy/warpgate -n warpgate`.
  사용자/타겟/세션은 SQLite DB에 있으므로 설정 파일과 무관.
- **인증서 갱신(약 60일)** 후에는 파드 재시작이 필요하다. 자동 반영되지 않는다.
- **PROXY protocol 결합**: haproxy의 warpgate backend `send-proxy-v2`와
  warpgate.yaml 각 리스너의 `proxy_protocol: true`는 반드시 함께 켜고 끈다.
  한쪽만 바뀌면 해당 리스너 접속이 전부 실패한다.
- **production 타겟은 admin role만 허용한다.** 처음에는 "등록하지 않는다"가 원칙이었으나
  2026.08.22에 admin 전용 타겟(`cheese-lake-prod`, `cheese-lake-clickhouse-prod`)으로
  등록했다. Allow roles에 `service`/`users`를 체크하는 순간 자동화가 운영 DB에 닿는다.
- **Warpgate가 지원하지 않는 DB**(ClickHouse, Redis 등)는 호환 포트로 우회한다.
  ClickHouse는 PostgreSQL 호환 포트 9005를 열어 Postgres 타겟으로 등록했다.
  상세는 Documents/sync/프로젝트/Warpgate 중앙 접근 관제/Warpgate 운영 가이드.
- OCI 방화벽(서브넷 Security List)에서 5432/2222 개방 여부가 외부 접근을 최종 결정한다.
