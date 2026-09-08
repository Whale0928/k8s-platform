# ADR 0002: 공용 오브젝트 스토리지를 SeaweedFS로 전환한다

- 상태: Accepted, 배포 구성은 검증 전
- 날짜: 2026.09.08
- 대체: [ADR 0001](0001%20shared%20object%20storage.md)

## Context

사용자는 Silo의 유지보수 기반과 프로젝트 규모를 재평가하고 SeaweedFS를 선택했다.
웹 UI와 ClickHouse 연동을 새 구성의 요구사항으로 삼는다. 기존 ADR에서 언급한
SeaweedFS의 버전별 문제는 현재 버전에서 다시 확인하며 과거 판단을 그대로 적용하지 않는다.

## Decision

먼저 Silo의 StatefulSet, Service, HTTPRoute, ExternalSecret, SecretStore와 namespace를
제거한다. 기존 검증용 데이터만 삭제하고 500GiB 디스크와 PV는 전환용으로 보존한다.
PV 선언은 `platform/storage/objdata.yaml`에서 관리한다.

인증정보는 사용자가 만든 1Password `home-lab / SeaweedFS Admin` 항목을 사용한다.
등록된 서비스 계정과 SDK로 확인하며 `op` CLI를 사용하지 않는다. 사용자가 기존
도메인을 제거했으므로 새 도메인을 임의로 만들거나 기존 도메인을 재사용하지 않는다.

SeaweedFS의 버전, 단일 호스트 구성, 데이터 디렉터리, S3 인증, Admin UI 인증과
외부 노출 범위는 공식 문서와 실행 검증을 거쳐 별도 배포 변경으로 확정한다.

## Consequences

정리와 새 배포 사이에는 공용 S3 서비스가 없다. 기존 Silo 내부 메타데이터와
파일시스템은 남으며 새 데이터 형식과 혼용하지 않는다. PV의 기존 claimRef는
새 PVC 계약이 확정될 때 교체한다. DB 백업 및 기존 서비스 데이터 이전은 포함하지 않는다.
