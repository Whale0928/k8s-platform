# 공용 스토리지 디스크

`objdata.yaml`은 SeaweedFS 전용 500GiB local PV를 관리한다.

- Proxmox: `pve-1`, VM 100, `scsi2`, `local-lvm:vm-100-disk-2`
- 게스트: `pve-pod-1`, `/mnt/objdata`, ext4
- UUID: `b0d226ad-c184-4ac9-81fe-741f59943a7d`
- PV/PVC: `seaweedfs-data` / `seaweedfs/data-seaweedfs-0`

2026.09.08 Released 상태의 기존 `silo-data` PV 객체만 제거하고 같은 디스크를
새 PV에 연결했다. 디스크를 재포맷하지 않았으며 새 데이터는 `seaweedfs/` 아래에
보관한다. 기존 Silo 내부 메타데이터는 별도로 보존한다.

`Retain`과 `Prune=false`로 디스크를 보호한다. VM의 `onboot: 1`과 UUID 기반
fstab 마운트는 유지한다. SSH는 `ssh -J home-lap-node-2 pve-pod-1`로 연결한다.

배포와 운영 절차는 [SeaweedFS 구성](../seaweedfs/README.md)을 참고한다.
