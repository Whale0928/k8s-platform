# ClickHouse 프로젝트 계정 권한

계정과 권한은 SQL 로 관리한다. `default` 계정에 `CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1`
이 걸려 있어 그 계정으로만 `GRANT` 를 실행할 수 있다 (`clickhouse.yaml` 참조).

선언적으로 적용되는 파일이 아니라 **무엇을 왜 줬는지 남기는 기록**이다. 서버를 다시
세울 때 이 순서로 다시 실행한다.

## 원칙

프로젝트 계정은 자기 데이터베이스에만 권한을 갖는다. 시스템 테이블은 **개별로** 연다.
서버 전체를 드러내는 테이블은 열지 않는다.

- `system.tables`, `filesystem*()` — 저장 용량과 행 수. 화면의 저장소 묶음이 쓴다
- `system.parts` — 파티션당 파트 수, 비활성 파트, 파트가 놓인 디스크
- **`system.asynchronous_metrics` 는 주지 않는다.** 서버 전체 지표라 같은 서버의 다른
  프로젝트와 호스트 상황이 드러난다. 필요한 값은 `system.parts` 로 직접 센다

## 적용 기록

### 2026-09-06 · system.parts

```sql
GRANT SELECT ON system.parts TO development_cheese_lake;
```

**왜 열었나.** 디스크가 차면 ClickHouse 는 INSERT 를 거부하고 진행 중인 병합이 깨진다.
그 전조인 파티션당 파트 수를 읽을 방법이 없었다. 앞으로 S3 계층형 스토리지를 도입하면
파트가 어느 볼륨에 있는지(`disk_name`)도 여기서만 알 수 있다.

**시야가 넓어지지 않는 것을 실측으로 확인했다.** 부여 뒤 이 계정으로
`SELECT DISTINCT database FROM system.parts` 를 돌리면 `development_cheese_lake` 하나만
나오고, 같은 서버의 `production_cheese_lake` 파트는 0 건이다. ClickHouse 가 접근 권한으로
행을 걸러 준다. 공식 문서에 이 동작이 적혀 있지 않아 실제로 재서 확인했다
(서버 26.7.3.19).

**그때 실측값** (기준선으로 남긴다): 파티션당 파트 수 최대 12, 활성 파트 96 개 2.50 GiB,
비활성 파트 418 개, 디스크는 `default` 하나.

**아직 열지 않은 것.** `system.merges` · `system.mutations` 는 병합 적체를 직접 보는
자리다. 비활성 파트 수로 대신 가늠할 수 있어 미뤘다. 필요해지면 같은 방식으로
개별 부여하고 이 문서에 적는다.
