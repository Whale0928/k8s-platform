# 오브젝트 스토리지 디스크 전환

2026.09.08 Silo에서 SeaweedFS로 전환하기로 결정하여 Silo 배포를 제거한다.
500GiB 디스크는 재포맷하거나 삭제하지 않는다.

- Proxmox: `pve-1`, VM 100, `scsi2`, `local-lvm:vm-100-disk-2`
- 게스트: `pve-pod-1`, `/mnt/objdata`, ext4
- 파일시스템 UUID: `b0d226ad-c184-4ac9-81fe-741f59943a7d`
- PV: `silo-data`, `Retain`, 자동 prune 방지

PV 이름은 기존 객체를 보존하기 위해 유지한다. Silo namespace와 PVC 제거 후에는
`Released` 상태가 정상이다. SeaweedFS 배포 시 사용할 PVC와 데이터 경로를 확정한 뒤
claimRef를 교체한다. 연결 중인 PV를 임의로 재사용하지 않는다.

제거 전 S3 목록에서 이전 설치 검증용 1MiB 객체 하나만 확인했고 해당 객체와 버킷을
삭제하여 버킷이 없는 상태를 확인했다. 파일시스템의 Silo 내부 메타데이터는 보존한다.
새 배포 시 별도 데이터 디렉터리를 사용하거나 내용을 확인한 뒤 정리한다.

1Password는 `home-lab / SeaweedFS Admin` 항목을 사용한다. `username`, `password`,
`accessKey`, `secretKey` 필드가 존재하는 것을 확인했으며 값은 저장소에 기록하지 않는다.
기존 `silo-admin` 항목과 외부 DNS는 사용자가 이미 삭제했다. `op` CLI는 사용하지 않는다.

기존 VM의 `onboot: 1`과 디스크 UUID 기반 자동 마운트 설정은 유지한다.
2026.09.05 호스트 재부팅 후 VM 자동 시작, k3s Ready 복귀와 파일 보존을 검증했다.
2026.09.08 정리 시 로컬에서 호스트 SSH 연결은 불가능하므로 디스크 내용 변경과
재부팅은 실행하지 않는다. Kubernetes API를 통한 배포 제거만 수행한다.
