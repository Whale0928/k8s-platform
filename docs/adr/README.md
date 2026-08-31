# Architecture Decision Records

k8s-platform의 아키텍처 결정 기록. [Nygard 형식](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)(결정 하나를 Context·Decision·Consequences 세 절로 적는 ADR 표준 서식)을 따른다.

각 문서는 결정 자체보다 **왜 그 결정을 했는지**와 **버린 대안이 왜 부적합했는지**를 남긴다. 나중에 전제가 바뀌면 새 ADR로 대체(supersede)하고 이전 문서는 지우지 않는다.

플랫폼 인프라(홈랩 하이퍼바이저, 클러스터 공용 컴포넌트)의 결정을 여기 적는다. 개별 프로젝트의 결정은 각 저장소의 ADR에 남긴다.

## 목록

| # | 제목 | 상태 |
|---|---|---|
| [0001](0001%20shared%20object%20storage.md) | 공용 오브젝트 스토리지를 pve-1에 세운다 | Accepted |
