# ArgoCD Image Updater

컨테이너 레지스트리의 새 이미지 태그를 감지하여 ArgoCD Application을 자동으로 업데이트합니다.

## 구성 요소

| 파일 | 설명 |
|------|------|
| `00-crd.yaml` | ImageUpdater CRD (v1.0.x 필수) |
| `10-rbac.yaml` | ServiceAccount, ClusterRole, ClusterRoleBinding |
| `20-deployment.yaml` | Image Updater Deployment |
| `30-configmap.yaml` | 레지스트리 및 ArgoCD 서버 설정 |
| `image-updater-secret.sops.yaml` | 인증 정보 (SOPS 암호화) |

## ImageUpdater CR 사용법

v1.0.x부터 Application annotation 대신 **ImageUpdater CR**로 설정합니다.

### 기본 예제 (Kustomize)

```yaml
apiVersion: argocd-image-updater.argoproj.io/v1alpha1
kind: ImageUpdater
metadata:
  name: my-updater
  namespace: argocd
spec:
  namespace: argocd

  # 업데이트 결과 반영 방식
  writeBackConfig:
    method: "argocd"  # argocd: 파라미터 오버라이드 / git: Git 커밋

  # 대상 Application 설정
  applicationRefs:
    - namePattern: "bottlenote-production"  # Application 이름 패턴 (와일드카드 지원)
      images:
        - alias: "api"                       # 이미지 별칭 (고유해야 함)
          imageName: "docker-registry.bottle-note.com/bottle-note/api:1.0.0"
          commonUpdateSettings:
            updateStrategy: "semver"         # semver, latest, digest, name
            allowTags: "regexp:^[0-9]+\\.[0-9]+\\.[0-9]+$"  # 허용 태그 패턴
          manifestTargets:
            kustomize:
              name: "docker-registry.bottle-note.com/bottle-note/api"
```

### Helm 예제

```yaml
apiVersion: argocd-image-updater.argoproj.io/v1alpha1
kind: ImageUpdater
metadata:
  name: helm-updater
  namespace: argocd
spec:
  namespace: argocd
  writeBackConfig:
    method: "argocd"
  applicationRefs:
    - namePattern: "my-helm-app"
      images:
        - alias: "backend"
          imageName: "myregistry.com/backend:1.0.0"
          commonUpdateSettings:
            updateStrategy: "semver"
          manifestTargets:
            helm:
              name: "image.repository"   # values.yaml 경로
              tag: "image.tag"
```

### Git Write-back 예제

```yaml
apiVersion: argocd-image-updater.argoproj.io/v1alpha1
kind: ImageUpdater
metadata:
  name: git-updater
  namespace: argocd
spec:
  namespace: argocd
  writeBackConfig:
    method: "git"
    gitConfig:
      branch: "main"
      writeBackTarget: "kustomization:./deploy/overlays/production"
  applicationRefs:
    - namePattern: "my-app-*"
      images:
        - alias: "app"
          imageName: "myregistry.com/app:1.0.0"
```

### 여러 Application 일괄 관리

```yaml
apiVersion: argocd-image-updater.argoproj.io/v1alpha1
kind: ImageUpdater
metadata:
  name: production-updater
  namespace: argocd
spec:
  namespace: argocd

  # 전역 설정 (모든 앱에 적용)
  commonUpdateSettings:
    updateStrategy: "semver"
    ignoreTags: ["latest", "dev", "test"]

  writeBackConfig:
    method: "argocd"

  applicationRefs:
    # 패턴으로 여러 앱 매칭
    - namePattern: "*-production"
      labelSelectors:
        matchLabels:
          environment: "production"
      images:
        - alias: "app"
          imageName: "myregistry.com/app:1.0.0"

    # 개별 앱 지정
    - namePattern: "special-app"
      images:
        - alias: "main"
          imageName: "myregistry.com/special:2.0.0"
          commonUpdateSettings:
            updateStrategy: "digest"  # 이 앱만 다른 전략 사용
```

## 업데이트 전략

| 전략 | 설명 | 사용 예 |
|------|------|---------|
| `semver` | 시맨틱 버전 기준 최신 | `1.0.0` → `1.0.1` → `1.1.0` |
| `latest` | 가장 최근 푸시된 태그 | CI/CD 빌드 번호 |
| `digest` | 동일 태그의 새 다이제스트 감지 | `latest` 태그 추적 |
| `name` | 알파벳순 최신 | 날짜 기반 태그 `2024-01-15` |

## 로그 확인

```bash
# 실시간 로그
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-image-updater -f

# ImageUpdater CR 상태 확인
kubectl get imageupdaters -n argocd
kubectl describe imageupdater my-updater -n argocd
```

## 트러블슈팅

### Pod가 시작되지 않음

```bash
# CRD 설치 확인
kubectl get crd imageupdaters.argocd-image-updater.argoproj.io

# RBAC 권한 확인
kubectl auth can-i list imageupdaters --as=system:serviceaccount:argocd:argocd-image-updater
```

### 이미지 업데이트가 안 됨

1. ImageUpdater CR이 있는지 확인
2. `namePattern`이 Application 이름과 매칭되는지 확인
3. 레지스트리 인증 정보 확인
4. 로그에서 에러 메시지 확인

## 참고 문서

- [ArgoCD Image Updater 공식 문서](https://argocd-image-updater.readthedocs.io/)
- [v1.0.x Migration Guide](https://argocd-image-updater.readthedocs.io/en/stable/configuration/migration/)
