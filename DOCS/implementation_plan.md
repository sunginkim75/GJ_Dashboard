# 경조사 관리 모바일 웹 서비스 구현 계획

구글 스프레드시트와 연동하여 경조사 데이터를 모바일에서 편리하게 검색 및 입력하고, 지정된 구글 ID를 가진 사용자만 로그인하여 접근할 수 있는 모바일 최적화 웹 페이지를 개발합니다.

## User Review Required

> [!IMPORTANT]
> 본 서비스를 구글 스프레드시트 및 구글 로그인과 연동하기 위해 **구글 클라우드 콘솔(Google Cloud Console) 설정**이 필요합니다. 개발 환경 셋업을 위해 다음 정보가 준비되어야 합니다:
> 1. **구글 서비스 계정(Service Account) 키 파일 (`credentials.json`)**: 스프레드시트 읽기/쓰기 권한용
> 2. **OAuth 2.0 클라이언트 ID & 비밀번호**: 구글 로그인 연동용
> 3. **대상 스프레드시트에 서비스 계정 이메일 공유**: 편집자 권한으로 스프레드시트 내 공유 설정 필요
> 4. **서비스 접근 권한을 줄 구글 이메일 목록**: 허가된 구글 ID만 서비스를 이용할 수 있도록 제한

> [!NOTE]
> 구글 API 설정 프로세스가 복잡할 경우, 설정 가이드를 포함하여 진행할 예정입니다.

## Open Questions

> [!IMPORTANT]
> 1. **기존 스프레드시트의 컬럼 구조**: 제공해주신 스프레드시트([Google Sheets](https://docs.google.com/spreadsheets/d/1wwB0_rMS3uQrhRykRp4kdrzV0bWHDqwjniuSuBdztzk/edit))의 시트 이름과 컬럼 헤더(예: 날짜, 이름, 경조사구분, 금액, 관계, 메모 등)가 어떻게 구성되어 있는지 확인이 필요합니다. (혹은 시트가 비어있다면 추천하는 최적의 컬럼 구조로 자동 초기화하여 사용할 수 있습니다.)
> 2. **허용할 구글 이메일 목록**: 접근 가능한 구글 계정 목록을 스프레드시트의 별도 시트(예: `AllowedUsers` 시트)에 관리할지, 아니면 로컬 설정 파일(`config/allowed_users.json`)에 하드코딩 형태로 관리할지 결정이 필요합니다. (스프레드시트 시트 관리 방식이 추후 이메일 추가/삭제 시 편리하므로 이를 추천합니다.)

## Proposed Changes

### 백엔드 및 인증 아키텍처

- **백엔드 (Python FastAPI)**:
  - 구글 스프레드시트 API 연동 (`gspread`, `google-auth` 라이브러리 사용)
  - 구글 OAuth 2.0 토큰 검증 및 사용자 세션 생성 (JWT 기반 혹은 Secure Cookie Session 사용)
  - 로그인된 사용자 세션을 확인하여 검색 및 입력 API 제공
- **프론트엔드 (Vanilla HTML/CSS/JS)**:
  - 모바일 해상도에 최적화된 반응형 웹 (현대적이고 깔끔한 UI/UX, 다크 모드 기반 테마)
  - 구글 로그인 버튼 (Google Identity Services GIS SDK 사용)
  - **검색 화면**: 이름 검색창 및 실시간 필터링, 검색 결과를 카드 형태나 타임라인 형태로 표시
  - **입력 화면**: 이름, 경조사 구분, 금액, 관계, 날짜, 메모 등을 입력하는 직관적인 폼 및 유효성 검사

---

### 구성 요소 목록

#### [NEW] [config/allowed_users.json](file:///d:/01.Sungin_Data/02.Python_Workspace/GJ_Dashboard/config/allowed_users.json)
- 접근이 승인된 구글 이메일 목록을 저장하는 임시/로컬 설정 파일 (또는 스프레드시트와 직접 연동하도록 설정 가능).

#### [NEW] [src/sheets_client.py](file:///d:/01.Sungin_Data/02.Python_Workspace/GJ_Dashboard/src/sheets_client.py)
- `gspread`를 이용하여 구글 스프레드시트 데이터 조회 및 삽입 기능을 캡슐화한 클라이언트 클래스.

#### [NEW] [src/main.py](file:///d:/01.Sungin_Data/02.Python_Workspace/GJ_Dashboard/src/main.py)
- FastAPI 웹 서버 및 REST API 엔드포인트 구현.
- `/api/auth/login` (구글 토큰 검증 및 로그인 처리)
- `/api/events/search` (경조사 데이터 검색)
- `/api/events/add` (신규 경조사 데이터 추가)
- Static 파일 제공 (HTML, CSS, JS)

#### [NEW] [src/static/index.html](file:///d:/01.Sungin_Data/02.Python_Workspace/GJ_Dashboard/src/static/index.html)
- SPA(Single Page Application) 구조로 제작된 메인 웹 페이지.
- 로그인 전: 구글 로그인 유도 화면
- 로그인 후: 검색 탭 및 등록 탭 제공

#### [NEW] [src/static/style.css](file:///d:/01.Sungin_Data/02.Python_Workspace/GJ_Dashboard/src/static/style.css)
- 모바일 최적화 레이아웃, 모던한 다크/라이트 테마, 유려한 애니메이션이 포함된 스타일시트.

#### [NEW] [src/static/app.js](file:///d:/01.Sungin_Data/02.Python_Workspace/GJ_Dashboard/src/static/app.js)
- 구글 로그인 연동 로직, API 호출, 검색 결과 렌더링, 폼 제출 및 UI 전환 관리 로직.

---

## Verification Plan

### Automated Tests
- 스프레드시트 API 연동 단독 테스트를 위한 디버그 스크립트 작성 및 실행 (`Debug/001.debug_test.py` 형태)
- 백엔드 API 작동 테스트 및 구글 OAuth 토큰 검증 로직 단위 테스트

### Manual Verification
- 로컬 웹 서버 구동 후 PC 브라우저 및 모바일 브라우저(개발자 도구 시뮬레이션)를 통한 레이아웃 검증
- 구글 로그인 인증 흐름 테스트
- 실시간 이름 검색 및 경조사 내역 추가 시 스프레드시트에 실시간으로 기록되는지 확인
