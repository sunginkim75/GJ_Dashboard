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







