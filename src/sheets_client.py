import os
import json
import gspread
from google.oauth2.service_account import Credentials

class SheetsClient:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cred_path = os.path.join(base_dir, "config", "credentials.json")
        config_path = os.path.join(base_dir, "config", "config.json")
        
        # 1. 스프레드시트 ID 결정 (환경 변수 우선, 파일 차선)
        self.spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        
        # 설정 파일이 있으면 읽어서 오버라이드/폴백
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if not self.spreadsheet_id:
                        self.spreadsheet_id = config.get("spreadsheet_id")
            except Exception as e:
                print(f"[Warning] Failed to load config.json: {e}")
                
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 연결 상태 정보
        self.client = None
        self.doc = None
        self.db_sheet = None
        self.allowed_users_sheet = None
        self.is_connected = False

    def _connect(self):
        """필요할 때 실제로 구글 스프레드시트에 접속합니다 (지연 연결)."""
        if self.is_connected:
            return
            
        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID가 설정되지 않았습니다. (환경변수 SPREADSHEET_ID 또는 config.json 필요)")
            
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cred_path = os.path.join(base_dir, "config", "credentials.json")
        google_creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        
        # 구글 크리덴셜 결정
        if google_creds_json:
            try:
                # 괄호 기반 최외곽 도려내기 (BOM, 복사 쓰레기 텍스트 방어)
                google_creds_json = google_creds_json.strip()
                start_idx = google_creds_json.find('{')
                end_idx = google_creds_json.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    google_creds_json = google_creds_json[start_idx:end_idx+1]
                
                # 백슬래시 이스케이프 깨짐 해결을 위한 이중 백슬래시화 정규화
                google_creds_json = google_creds_json.replace('\\\\', '\\').replace('\\', '\\\\')
                
                cred_info = json.loads(google_creds_json)
                
                # private_key 내부의 모든 개행 깨짐 및 역슬래시 찌꺼기를 원천 소거하고 올바른 PEM 규격으로 재조립
                if "private_key" in cred_info and isinstance(cred_info["private_key"], str):
                    pk = cred_info["private_key"]
                    header = "-----BEGIN PRIVATE KEY-----"
                    footer = "-----END PRIVATE KEY-----"
                    
                    # 1. 헤더/푸터 제외한 순수 base64 본문 추출
                    pure_b64 = pk
                    if header in pk:
                        pure_b64 = pure_b64.replace(header, "")
                    if footer in pk:
                        pure_b64 = pure_b64.replace(footer, "")
                        
                    # 2. 모든 줄바꿈 및 이스케이프 문자, 역슬래시(\) 소거
                    pure_b64 = pure_b64.replace("\\r", "").replace("\\n", "").replace("\n", "").replace("\r", "")
                    pure_b64 = pure_b64.replace("\\", "")
                    pure_b64 = "".join(pure_b64.split()) # 공백 완벽 제거
                    
                    # 3. 64글자 단위로 자르고 개행을 넣어 정밀 재조립
                    lines = [pure_b64[i:i+64] for i in range(0, len(pure_b64), 64)]
                    cred_info["private_key"] = header + "\n" + "\n".join(lines) + "\n" + footer
                
                creds = Credentials.from_service_account_info(cred_info, scopes=self.scopes)
                print("[SheetsClient] Lazy-connected using environment GOOGLE_CREDENTIALS")
            except Exception as e:
                raise ValueError(f"GOOGLE_CREDENTIALS 환경 변수 파싱 실패: {e}")
        elif os.path.exists(cred_path):
            creds = Credentials.from_service_account_file(cred_path, scopes=self.scopes)
            print(f"[SheetsClient] Lazy-connected using file {cred_path}")
        else:
            raise ValueError("Google Credentials가 존재하지 않습니다. (credentials.json 파일 또는 GOOGLE_CREDENTIALS 환경변수 필요)")
            
        try:
            self.client = gspread.authorize(creds)
            self.doc = self.client.open_by_key(self.spreadsheet_id)
            self.db_sheet = self.doc.worksheets()[0]
            
            # AllowedUsers 시트 찾기
            self.allowed_users_sheet = None
            for ws in self.doc.worksheets():
                if ws.title in ["AllowedUsers", "접근권한"]:
                    self.allowed_users_sheet = ws
                    break
            self.is_connected = True
        except Exception as e:
            self.is_connected = False
            raise RuntimeError(f"Google Sheets 접속 오류: {e}. 스프레드시트 공유 권한이나 ID를 확인해 주세요.")

    def _clean_records(self, records):
        """딕셔너리 키에서 BOM(\ufeff) 및 좌우 공백을 제거하여 깨끗한 딕셔너리 리스트를 만듭니다."""
        clean_list = []
        for r in records:
            clean_r = {}
            for k, v in r.items():
                clean_k = str(k).replace("\ufeff", "").strip()
                clean_r[clean_k] = v
            clean_list.append(clean_r)
        return clean_list
                
    def get_allowed_emails(self):
        """허가된 이메일 목록을 스프레드시트에서 조회합니다."""
        try:
            self._connect()
        except Exception as e:
            print(f"[Error connecting to Sheets] {e}")
            return []
            
        if not self.allowed_users_sheet:
            return []
        try:
            records = self.allowed_users_sheet.get_all_records()
            clean_records = self._clean_records(records)
            emails = []
            for r in clean_records:
                for k, v in r.items():
                    if k.lower() == "email" and v:
                        emails.append(str(v).strip().lower())
            return emails
        except Exception as e:
            print(f"[Error fetching allowed emails] {e}")
            return []
            
    def search_events(self, query: str = "", field: str = "all", show_all: bool = False, tx_type: str = "all"):
        """다중 조건(통합, 이름, 경조사명, 회사, 누구), 전체 보기 및 입출금 구분(받음/보냄)으로 경조사 데이터를 검색합니다."""
        self._connect()
        try:
            records = self.db_sheet.get_all_records()
            clean_records = self._clean_records(records)

            if show_all:
                results = clean_records
            else:
                query = query.strip().lower()
                if not query:
                    return []

                target_fields_map = {
                    "all": ["이름", "경조사명", "회사", "누구"],
                    "이름": ["이름"],
                    "경조사명": ["경조사명"],
                    "회사": ["회사"],
                    "누구": ["누구"],
                }
                search_cols = target_fields_map.get(field, ["이름", "경조사명", "회사", "누구"])

                results = []
                for r in clean_records:
                    for col in search_cols:
                        val = str(r.get(col, "")).strip().lower()
                        if query in val:
                            results.append(r)
                            break

            if tx_type in ["입금", "출금"]:
                results = [r for r in results if str(r.get("입출금", "")).strip() == tx_type]

            return results
        except Exception as e:
            print(f"[Error searching events] {e}")
            raise e

    def _format_row_values(self, num_val, data: dict):
        """헤더 순서에 맞춰 스프레드시트 행 리스트를 생성합니다."""
        headers = ['번호', '날짜', '이름', '경조사명', '회사', '누구', '입출금', '축의금', '참석', '입출금방법', 'Remark', '답례여부', '답례금액']
        row_values = []
        for h in headers:
            if h == "번호":
                row_values.append(num_val)
            else:
                val = data.get(h, "")
                if h in ["축의금", "답례금액"]:
                    if isinstance(val, (int, float)):
                        val = f"{int(val):,}" if val else ""
                    elif isinstance(val, str):
                        clean_str = val.replace(",", "").strip()
                        if clean_str:
                            try:
                                clean_val = int(clean_str)
                                val = f"{clean_val:,}" if clean_val > 0 else ("0" if h == "축의금" else "")
                            except ValueError:
                                pass
                        else:
                            val = ""
                row_values.append(val)
        return row_values

    def add_event(self, data: dict):
        """새로운 경조사 이벤트를 스프레드시트에 추가합니다."""
        self._connect()
        try:
            records = self.db_sheet.get_all_records()
            clean_records = self._clean_records(records)
            last_num = 0
            if clean_records:
                try:
                    last_num = int(clean_records[-1].get("번호", 0))
                except ValueError:
                    last_num = len(clean_records)

            new_num = last_num + 1
            row_values = self._format_row_values(new_num, data)

            self.db_sheet.append_row(row_values)
            return {"success": True, "번호": new_num}
        except Exception as e:
            print(f"[Error adding event] {e}")
            raise e

    def update_event(self, event_num: int, data: dict):
        """기존 경조사 이벤트를 번호(번호 컬럼) 기준으로 찾아 수정합니다."""
        self._connect()
        try:
            col_a = self.db_sheet.col_values(1)
            target_row_idx = None
            for idx, val in enumerate(col_a, start=1):
                if idx == 1:
                    continue
                if str(val).strip() == str(event_num).strip():
                    target_row_idx = idx
                    break

            if not target_row_idx:
                raise ValueError(f"해당 번호({event_num})의 경조사 내역을 시트에서 찾을 수 없습니다.")

            row_values = self._format_row_values(event_num, data)
            self.db_sheet.update(range_name=f"A{target_row_idx}:M{target_row_idx}", values=[row_values])
            return {"success": True, "번호": event_num}
        except Exception as e:
            print(f"[Error updating event] {e}")
            raise e

    def get_last_update_date(self):
        """DB 시트의 가장 마지막 행의 날짜 컬럼 값을 읽어옵니다."""
        try:
            self._connect()
            records = self.db_sheet.get_all_records()
            if not records:
                return "데이터 없음"
            clean_records = self._clean_records(records)
            last_record = clean_records[-1]
            return last_record.get("날짜", "알 수 없음")
        except Exception as e:
            print(f"[Error getting last update date] {e}")
            return "알 수 없음"
