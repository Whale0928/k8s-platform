# SeaweedFS 공용 오브젝트 스토리지

SeaweedFS 4.45를 `pve-pod-1`의 500GiB local PV에서 실행한다. 이미지 태그와
multi-arch digest를 함께 고정한다. StatefulSet 한 개 안에서 저장소 서버와 Admin을
각각 컨테이너로 실행하며 ClickHouse 배포 설정은 변경하지 않는다.

| 항목 | 값 |
|---|---|
| Admin UI | `https://seaweed.dead-whale.org` |
| S3 endpoint | `http://seaweedfs-s3.seaweedfs.svc.cluster.local:8333` |
| 기본 버킷 | `default` |
| ClickHouse 전용 버킷 | `cheese-lake-clickhouse` |
| region / addressing | `us-east-1` / path style |
| 데이터 | `/mnt/objdata/seaweedfs`, ext4, PV `seaweedfs-data` |
| PVC | `seaweedfs/data-seaweedfs-0`, 500Gi |

## 인증정보

`home-lab / SeaweedFS Admin`에는 사용자가 등록한 관리자 로그인, 기본 버킷용
`accessKey`·`secretKey`와 `bucket`·`endpoint`·`region`·`addressingStyle`을 저장한다.
기존 로그인 정보와 웹사이트는 유지한다.

`cheese-lake / SeaweedFS ClickHouse`에는 전용 접근키, 버킷, endpoint, region,
path style과 향후 사용 가능한 `clickhouse/` prefix를 저장한다. 버킷 생성과 연결정보
등록만 수행하며 ClickHouse 데이터 연동·이관·TTL 정책은 적용하지 않는다.

1Password 갱신에는 기존 `OP_SERVICE_ACCOUNT_TOKEN`과 공식 Python SDK를 사용한다.
`op` CLI는 사용하지 않는다. 클러스터의 ExternalSecret은 두 볼트의 기존 Connect
토큰과 SecretStore를 이용해 JSON 인증 설정을 생성한다. 평문 인증정보는 Git에 없다.
각 S3 접근키는 자기 버킷의 Read/Write/List만 허용하며, 기본 버킷 키에는 Tagging도
허용한다. 익명 접근과 다른 버킷 접근은 허용하지 않는다.

S3 IAM 설정의 원본은 1Password와 ExternalSecret이다. `s3.iam.readOnly=true`로
S3 IAM API에서 별도 변경하지 않게 한다. 키 변경 뒤에는 ExternalSecret 동기화와
SeaweedFS Pod 재시작 후 다시 검증한다. 관리자 암호는 환경변수로 읽는다.

## 저장소 구성

Master, Volume, Filer는 Pod 내부 loopback으로만 통신한다. Filer metadata는
`/data/seaweedfs/filer`의 LevelDB2에, Master·Volume·Admin 데이터는 각각 별도
디렉터리에 보존한다. 외부 Gateway에는 Admin만 연결하고 S3는 ClusterIP로 제공한다.
NetworkPolicy는 클러스터에서 S3 포트, Envoy namespace에서 Admin 포트만 허용한다.

Volume은 1GiB 단위, 최대 450개로 제한하고 파일시스템에 20GiB 미만이 남으면 쓰기를
제한한다. 볼륨 파일은 미리 전체 용량을 할당하지 않는다. initContainer는 디스크 마커와
475GiB 이상의 실제 파일시스템, 인증파일을 확인하여 잘못된 경로에 쓰는 것을 막는다.

디스크 UUID는 `b0d226ad-c184-4ac9-81fe-741f59943a7d`이며 재포맷하지 않았다.
기존 Silo 메타데이터는 별도 경로에 보존하고 SeaweedFS 데이터와 혼용하지 않는다.
VM 자동 시작과 UUID 기반 fstab 마운트도 유지한다. SSH 접속은 다음 경로를 사용한다.

```sh
ssh -J home-lap-node-2 pve-1
ssh -J home-lap-node-2 pve-pod-1
```

버킷 최초 생성은 서버가 Ready가 된 뒤 아래 명령을 실행한다. `/buckets/` 쓰기는
fsync를 사용하고 볼륨은 한 개씩 늘린다. 이 설정에는 TTL이 없다.

```sh
kubectl --kubeconfig /Users/hgkim/.kube/config-k3s -n seaweedfs exec -i seaweedfs-0 -c server -- weed shell -master=127.0.0.1:9333 -filer=127.0.0.1:8888 <<'EOF'
fs.configure -locationPrefix=/buckets/ -volumeGrowthCount=1 -fsync=true -apply
s3.bucket.create -name=default -owner=default-bucket
s3.bucket.create -name=cheese-lake-clickhouse -owner=cheese-lake-clickhouse
EOF
```

자동 vacuum·balance·erasure coding과 telemetry는 비활성화한다. 삭제 공간 회수 정책은
사용량과 운영 요구를 확인한 뒤 별도 결정한다. 단일 호스트와 디스크이므로 복제본은 없다.

## 검증 범위

로컬 고정 이미지에서 관리자 로그인, 두 버킷의 업로드·다운로드·목록·삭제,
다른 버킷 및 익명 접근 차단, 7MiB multipart 전송을 검증했다.
배포 후에는 Secret 동기화, PVC Bound, Pod 2/2 Ready, HTTPS 로그인, 파일 왕복과
Pod 재생성 후 보존을 확인한다. 검증 객체만 삭제하고 기본 버킷 두 개는 유지한다.

ClickHouse 26.7.3.19의 기존 치즈레이크 MergeTree 테이블 10개가 `default` 로컬
정책을 사용하는 것을 조회했다. ClickHouse 설정·테이블·데이터를 변경하거나
ClickHouse Pod를 재시작하지 않는다.

## 공식 근거

- [SeaweedFS 4.45](https://github.com/seaweedfs/seaweedfs/releases/tag/4.45)
- [S3 API](https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API)
- [Admin UI](https://github.com/seaweedfs/seaweedfs/wiki/Admin-UI)
