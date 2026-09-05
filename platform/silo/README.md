# 공용 S3 호환 스토리지

Silo를 `pve-pod-1`의 전용 500GiB 디스크에서 실행한다. 기존 서비스의 데이터 이전과
버킷 생성은 포함하지 않는다. S3 API는 ClusterIP로 제공하고, 콘솔은 HTTPS로 공개한다.

| 항목 | 구성 |
|---|---|
| 이미지 | `pgsty/silo:RELEASE.2026-09-03T13-18-01Z` 및 manifest digest 고정 |
| 데이터 | Proxmox VM 100의 새 `scsi2`, ext4, `/mnt/objdata` |
| PV/PVC | `silo-data` / `silo/data-silo-0`, `500Gi`, `Retain` |
| S3 | `http://silo.silo.svc.cluster.local:9000` |
| 관리 콘솔 | `https://slio.dead-whale.org` → `silo-console:9001` |
| 인증정보 | 1Password `home-lab / silo-admin` → ExternalSecret → `silo-root` 파일 마운트 |

관리자 계정은 초기 관리 전용이다. 앱 연결 시에는 버킷별 권한을 제한한 별도 계정을
만들고 앱에 관리자 계정을 전달하지 않는다. 공개 버킷과 S3 API 외부 공개는 별도 작업이다.

1Password 항목은 등록된 서비스 계정과 공식 Python SDK로 생성한다. `op` CLI는 사용하지
않는다. 클러스터에서는 기존 home-lab 읽기 전용 Connect 토큰을 이용해 동기화한다.
관리자 비밀번호와 1Password 서비스 계정 토큰은 저장소에 넣지 않는다. 저장소에는 기존
Connect 토큰의 SOPS 암호문만 보관한다.

도메인은 사용자 DNS 등록값인 `slio.dead-whale.org`다. 제품 및 Kubernetes 리소스 이름은
`silo`를 유지한다. 기존 `https-dead-whale` listener와 wildcard 인증서를 재사용한다.

## 적용 전 조건

이 문서는 설치 절차이며 적용 완료 기록이 아니다. 디스크 생성·포맷과 Git push는
운영 변경이므로 승인 후 실행한다. 전체 `platform`을 수동 apply하지 않고,
디스크 준비 이후 이 디렉터리를 포함한 Git 변경을 ArgoCD로 배포한다.

2026.09.05 조회 기준 `pve-1`의 thin pool은 793.8GiB 중 약 123.4GiB를 사용하며,
기존 가상 디스크와 새 500GiB가 모두 차도 약 82.8%이며 약 136.8GiB가 남는다.
기존 80% 기준 대신 이 여유를 수용하여 500GiB로 결정했다. 실행 직전에 다시 확인한다.

```sh
ssh pve-1 'qm status 100; qm config 100 | sed -n -E "/^(scsi[0-9]+|lock|hotplug):/p"; lvs -o lv_name,lv_size,data_percent,metadata_percent'
ssh pve-pod-1 'lsblk -b -o NAME,TYPE,SIZE,SERIAL,FSTYPE,MOUNTPOINTS'
```

`scsi2`나 serial `objdata`가 이미 존재하면 이 절차를 반복하지 않고 기존 상태부터
확인한다. 새 디스크만 `discard=on`으로 연결한다. 기존 `scsi0/scsi1`의 discard
변경과 VM 재시작은 이 설치에 포함하지 않는다.

## 새 디스크 준비

Proxmox에서 빈 SCSI 슬롯을 확인한 뒤 한 번만 실행한다.

```sh
ssh pve-1 'set -eu
if test -n "$(qm config 100 | sed -n "/^scsi2:/p")"; then
  echo "scsi2 already exists; stop" >&2
  exit 1
fi
qm set 100 --scsi2 local-lvm:500,discard=on,iothread=1,ssd=1,serial=objdata'
```

VM이 새 디스크를 인식한 뒤 `ssh pve-pod-1`에서 아래 절차를 실행한다. serial,
정확한 크기, 파티션·파일시스템 서명 부재를 확인한다. 조건이 맞지 않으면 중단하며,
기존 디스크를 포맷하거나 강제 포맷 옵션을 사용하지 않는다.

```sh
set -eu
obj_disk="$(lsblk -bnr -o PATH,SERIAL,TYPE | awk '$2 == "objdata" && $3 == "disk" {print $1}')"
test -n "$obj_disk"
test "$(printf '%s\n' "$obj_disk" | wc -l)" -eq 1
test "$(sudo blockdev --getsize64 "$obj_disk")" -eq 536870912000
test "$(lsblk -nr -o TYPE "$obj_disk" | wc -l)" -eq 1
test -z "$(sudo wipefs --no-act "$obj_disk")"
if sudo findmnt --source "$obj_disk" >/dev/null; then exit 1; fi
test ! -e /mnt/objdata
if awk '$2 == "/mnt/objdata" {found=1} END {exit !found}' /etc/fstab; then exit 1; fi

sudo mkfs.ext4 -L objdata -m 0 "$obj_disk"
obj_uuid="$(sudo blkid -s UUID -o value "$obj_disk")"
test -n "$obj_uuid"
sudo install -d -m 0755 /mnt/objdata
printf 'UUID=%s /mnt/objdata ext4 defaults,nofail,x-systemd.device-timeout=10s 0 2\n' "$obj_uuid" | sudo tee -a /etc/fstab >/dev/null
sudo systemctl daemon-reload
sudo mount /mnt/objdata
test "$(findmnt -rn -o UUID --target /mnt/objdata)" = "$obj_uuid"
sudo chown 1000:1000 /mnt/objdata
printf 'silo-data-v1\n' | sudo tee /mnt/objdata/.silo-volume >/dev/null
sudo chmod 0444 /mnt/objdata/.silo-volume
findmnt /mnt/objdata
df -h /mnt/objdata
```

마커는 실제 디스크를 마운트한 뒤에만 생성한다. initContainer는 마커, 475GiB 이상인
실제 파일시스템, 쓰기 권한, 인증 파일을 검사한다. 부팅 시 디스크가 빠져도 다른
워크로드는 시작할 수 있지만 Silo는 마운트 디렉터리에 잘못 쓰지 않고 시작을 멈춘다.

## 검증과 접속

렌더링 결과에는 복호화된 Secret이 포함되므로 터미널 출력이나 파일로 저장하지 않는다.

```sh
kustomize build --enable-alpha-plugins --enable-exec platform/silo |
  kubectl --kubeconfig /Users/hgkim/.kube/config-k3s apply --dry-run=client -f -
```

GitOps 배포 후 PVC Bound, StatefulSet 1/1 Ready, 디스크 UUID·용량과 마운트,
`/minio/health/live`·`/minio/health/ready` 응답을 확인한다. 임시 버킷에서 객체를
업로드·다운로드하여 SHA-256을 비교하고, Pod 교체 후 같은 객체가 남는지도 검증한다.
검증용 객체와 버킷만 정리한다. 실제 앱 버킷은 별도 작업에서 만든다.

콘솔은 `https://slio.dead-whale.org`에서 로그인한다. 버킷·객체, 사용자·정책·접근키를
관리할 수 있다. 외부 경로를 우회한 점검은 다음처럼 로컬로 연결한다.

```sh
kubectl --kubeconfig /Users/hgkim/.kube/config-k3s -n silo port-forward --address 127.0.0.1 service/silo-console 9001:9001
```

브라우저에서 `http://127.0.0.1:9001`을 사용한다. 자격증명을 명령 인자나 로그에
출력하지 않는다. 관리자 Secret 변경 후에는 Pod 재시작으로 FILE 환경변수를 다시 읽는다.

PV는 자동 prune을 막고 `Retain`으로 보존한다. StatefulSet의 Pod를 교체해도 PVC는
유지된다. Namespace나 PVC 삭제는 서비스 중단을 일으키므로 일상적인 재시작에
사용하지 않는다.

## 재부팅 검증

Proxmox 호스트 재부팅 전에 `qm config 100`에서 `onboot: 1`을 확인한다. 기본값은
`0`이므로 미설정 상태에서는 호스트가 복귀해도 VM이 자동으로 시작하지 않는다.
게스트에서는 `k3s-agent`가 enabled 상태이고 `/mnt/objdata`가 UUID로 `/etc/fstab`에
등록되어 있어야 한다.

재부팅 범위와 작업 시점을 확정한 뒤 실행한다. 호스트 재부팅 시 VM 전체가 중단되며
2노드 Proxmox 클러스터는 잠시 quorum을 잃는다. HA 관리 리소스 유무와 기존 워크로드의
상태를 먼저 확인한다. 재부팅 뒤에는 호스트와 VM boot ID 변화, VM 자동 시작,
디스크 UUID·용량·소유자, k3s-agent active, Kubernetes Node Ready, 기존 Pod 복귀,
Silo 객체 SHA-256 일치, 외부 콘솔 HTTPS와 로그인 성공을 확인한다.

## 근거

- [기존 ADR](../../docs/adr/0001%20shared%20object%20storage.md)
- [공식 릴리스와 이미지 digest](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z)
- [공식 healthcheck 계약](https://silo.pgsty.com/compatibility/feature/healthcheck/)

기존 ADR의 단일 ext4 디스크 구성을 유지한다. Silo는 단일 ext4 디스크를 허용하지만
공식 운영 지침은 XFS를 권장한다. 파일시스템 종류 변경은 기존 디스크를 재포맷해서
진행하지 않는다.
