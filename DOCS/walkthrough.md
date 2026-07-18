# 프로젝트 개발 히스토리 및 작업 로그 (Walkthrough)

## 2026-07-18
- **내용**: 경조사 관리 시스템 프로젝트 초기화, 가이드 작성 및 Vercel 배포 준비
- **작업 상세**:
  - `config/version.json` 초기 버전 설정 (v0.1.0) -> v0.2.0 업데이트
  - `DOCS/walkthrough.md` 문서 관리 시작
  - `DOCS/implementation_plan.md` 구현 계획 수립 (아티팩트 포함)
  - `DOCS/google_setup_guide.md` 구글 연동 가이드 문서 생성 및 안내
  - 기존 `Wave Surfer` 프로젝트 폴더에서 Google 서비스 계정 키(`google_key.json`)를 탐색하여 `config/credentials.json`으로 복사 완료
  - `requirements.txt` 생성 및 파이썬 가상환경(`venv`) 생성, 패키지 설치 완료 (v0.2.0)
  - 구글 API 연동 단독 테스트 스크립트(`Debug/001.debug_test.py`, `Debug/002.debug_test.py`) 작성 및 실행하여 스프레드시트 접근/추가 검증 완료
  - `src/sheets_client.py`: 구글 시트 연동 및 Vercel용 환경 변수(`GOOGLE_CREDENTIALS`, `SPREADSHEET_ID`) 로드 기능 개발 완료
  - `src/main.py`: JWT 기반 무상태(Stateless) 세션 암호화, 구글 로그인 토큰 검증, 검색/추가 API 구현 완료
  - `src/static/index.html`, `src/static/style.css`, `src/static/app.js`: 모바일 반응형 및 다크 럭셔리 스타일 기반의 단일 페이지 웹앱 개발 완료
  - `vercel.json`: Vercel Serverless Functions 파이썬 백엔드 빌드 및 라우팅 설정 파일 작성 완료
  - `Debug/003.debug_test.py`: JWT 발급 및 서명 만료 검증 단독 테스트 통과
  - `.gitignore`: 보안 파일(`credentials.json`, `config.json`)의 GitHub 노출 방지 처리 완료
  - **GitHub 연동 및 업로드 완료**: 로컬 저장소 빌드 후 원격 저장소(`https://github.com/sunginkim75/GJ_Dashboard`)로 전체 소스코드 Push 완료
  - **버그 수정 (v0.2.1)**: Vercel의 Serverless 환경(읽기 전용 컨테이너)에서 FastAPI의 정적 파일 마운트 작업이 권한 충돌을 일으켜 발생하는 500 크래시 버그 수정 완료 (Vercel 환경일 경우 마운트 과정 우회 처리)
  - **버그 수정 (v0.2.2)**: Vercel 파이썬 런타임이 `src/main.py` 실행 시 모듈 로드 경로 불일치로 `ModuleNotFoundError: No module named 'src'` 에러를 내며 크래시되는 현상 수정 완료 (임포트 경로에 부모 및 현재 폴더 강제 매핑 및 폴백 예외처리 적용)
  - **안정성 강화 (v0.2.3)**: 서버가 켜질 때 구글 API 연동을 즉시 시도하던 방식에서, 실제 사용자가 요청할 때 연결하도록 접속 방식을 **지연 연동(Lazy Connection)**으로 리팩토링 완료. (구글 연동 권한 및 환경 변수가 완전하지 않아도 서버 자체는 안전하게 켜지도록 보장)
  - **안정성 강화 (v0.2.4)**: 서버 기동 시 발생할 수 있는 모든 정적 자산(static) 마운트 예외를 예외 래퍼로 차단하여 구동 실패 방지 조치 완료.
  - **버그 수정 (v0.2.5)**: Vercel의 `JWT_SECRET` 환경변수가 비어 있거나 누락되어 로그인 시 발생하는 `HMAC key must not be empty` 서버 에러를 디폴트 보안 비밀키로 안전하게 우회 처리 완료.
  - **버그 수정 (v0.2.6)**: 구글 스프레드시트 헤더 행의 UTF-8 BOM(\ufeff) 및 숨은 공백으로 인해 검색 매칭이 0건으로 실패하는 현상 해결을 위한 헤더 정제화 래퍼(`_clean_records`) 적용 완료.
  - **버그 수정 (v0.2.7)**: Vercel의 `GOOGLE_CREDENTIALS` 환경변수 입력 시 복사 오차로 발생하는 JSON 구조 오류(JSONDecodeError)를 자동 복구하도록 중괄호 `{}` 기준 자동 정제 가위(Bracket Trimmer) 필터 로직 구현 및 장착 완료.
  - **버그 수정 (v0.2.8)**: Vercel 환경에서 환경 변수 문자열 내의 백슬래시(`\`)가 단독 해석되어 이스케이프 깨짐(`Invalid \escape`) 에러를 야기하는 현상을 이중 백슬래시(`\\`) 변환으로 원천 정규화 보완 조치 완료.
  - **버그 수정 (v0.2.9)**: 이중 백슬래시로 정화된 `\n` 기호를 구글 `cryptography` 라이브러리가 유효한 PEM 인증서로 로드할 수 있도록 파싱 완료 시점 이후에 진짜 개행 문자(LF)로 복구하여 연동 성공 처리 완료.
  - **안정성 강화 (v0.3.0)**: 구글 `private_key` 본문 내 불규칙한 다중 백슬래시 이탈을 차단하기 위해, 키의 base64 알맹이 영역에 있는 모든 백슬래시 찌꺼기를 원천 삭제한 뒤 RFC 7468 표준 PEM 규격(64글자 개행 배분)으로 강제 재조립하는 최종 무결성 필터 적용 완료.
  - **버그 수정 (v0.3.1)**: 모달 등록 창 내부의 `select-editable` 부모 컨테이너의 높이(height) 누락으로 인해 드롭다운 버튼과 입력 창이 찌그러지는 CSS 버그 수정 완료 (48px 명시 지정).
  - **버그 수정 (v0.3.2)**: 모바일/PC 테마 기본값으로 인해 드롭다운의 목록 글자색이 어둡게 렌더링되던 가독성 버그를 흰색 글자 강제 지정으로 해결하고, 선택 상자 겉에 노출되는 텍스트를 투명(transparent) 처리하여 입력 필드 placeholder와의 텍스트 중첩 버그를 완벽 해결.
  - **기능 추가 (v0.3.3)**: 경조사 장부 헤더 로고 옆에 프로그램 버전 뱃지(version-badge) 및 구글 스프레드시트 최종 데이터 기록 일자 뱃지(sync-badge)를 실시간 반영하는 UI 기능 추가 완료 (새로운 등록 성공 시 실시간으로 마지막 입력 날짜 갱신 처리 연동).
  - **메이저 UI 마이그레이션 (v0.4.0)**: 불안정한 CSS 절대좌표 겹치기 방식의 편집형 드롭다운 박스를 HTML5 웹 표준 기술인 **`<datalist>`** 자동완성 입력창으로 전면 전환하여 글자 겹침 및 화살표 가려짐 문제를 원천 차단하고, 전체 드롭다운 옵션 목록(입출금 방법 등 포함)에 다크모드 가독성 흰색 폰트 스타일을 통합 적용 완료.
  - **버그 수정 (v0.4.1)**: 모바일(좁은 화면) 기기에서 최상단 헤더 타이틀과 메타 뱃지들이 수평 정렬 충돌로 깨지던 현상을 수직 누적 구조(Flex Column Wrapper)로 반응형 레이아웃 정돈하여 완벽한 줄맞춤 실현.




















