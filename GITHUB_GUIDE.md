# GitHub에 프로젝트 올리기 가이드

## 1단계: Git 저장소 초기화 (로컬)

```bash
# Git 저장소 초기화
git init

# Git 사용자 정보 설정 (처음 한 번만)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## 2단계: 파일 추가 및 커밋

```bash
# 모든 파일 추가
git add .

# 커밋
git commit -m "Initial commit: 태양광 인버터 시뮬레이터 v2.0"
```

## 3단계: GitHub 계정 만들기 (아직 없다면)

1. https://github.com 접속
2. "Sign up" 클릭
3. 이메일, 비밀번호, 사용자명 입력
4. 무료 계정으로 가입

## 4단계: GitHub에 새 저장소 만들기

1. GitHub 로그인
2. 우측 상단 "+" 버튼 → "New repository" 클릭
3. Repository name 입력 (예: `inverter_simulator_v2`)
4. Public 또는 Private 선택
5. "Create repository" 클릭
6. **중요**: "Initialize this repository with a README" 체크 해제 (이미 README.md가 있으므로)

## 5단계: 로컬 저장소와 GitHub 연결

GitHub에서 생성된 저장소 페이지에서 나오는 명령어를 사용:

```bash
# 원격 저장소 추가 (YOUR_USERNAME과 YOUR_REPO_NAME을 실제 값으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 메인 브랜치 이름 설정 (최신 Git은 main 사용)
git branch -M main

# GitHub에 푸시
git push -u origin main
```

## 6단계: 인증 (첫 푸시 시)

GitHub에 푸시할 때 인증이 필요합니다:

### 방법 1: Personal Access Token (권장)
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" 클릭
3. 권한 선택: `repo` 체크
4. 토큰 생성 후 복사
5. 푸시 시 비밀번호 대신 토큰 입력

### 방법 2: GitHub CLI 사용
```bash
# GitHub CLI 설치 후
gh auth login
```

## 전체 명령어 요약

```bash
# 1. Git 초기화
git init

# 2. 사용자 정보 설정 (처음 한 번만)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 3. 파일 추가
git add .

# 4. 커밋
git commit -m "Initial commit: 태양광 인버터 시뮬레이터 v2.0"

# 5. 원격 저장소 연결 (GitHub에서 저장소 생성 후)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 6. 푸시
git push -u origin main
```

## 주의사항

- PDF 파일은 용량이 클 수 있으므로 `.gitignore`에 추가했을 수 있습니다
- 민감한 정보(API 키, 비밀번호 등)는 절대 커밋하지 마세요
- `.gitignore` 파일을 확인하여 불필요한 파일이 커밋되지 않도록 하세요

PUSH 테스트 
