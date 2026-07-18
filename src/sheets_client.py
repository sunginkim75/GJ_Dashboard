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
            
    def search_events(self, query: str):
        """이름을 기준으로 경조사 데이터를 검색합니다."""
        self._connect()
        try:
            records = self.db_sheet.get_all_records()
            clean_records = self._clean_records(records)
            query = query.strip().lower()
            if not query:
                return []
                
            results = []
            for r in clean_records:
                name = str(r.get("이름", "")).strip().lower()
                if query in name:
                    results.append(r)
            return results
        except Exception as e:
            print(f"[Error searching events] {e}")
            raise e
            
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
            
            # 헤더 순서에 맞춰 값 리스트 작성
            headers = ['번호', '날짜', '이름', '경조사명', '회사', '누구', '입출금', '축의금', '참석', '입출금방법', 'Remark']
            
            row_values = []
            for h in headers:
                if h == "번호":
                    row_values.append(new_num)
                else:
                    val = data.get(h, "")
                    if h == "축의금" and isinstance(val, (int, float)):
                        val = f"{val:,}"
                    elif h == "축의금" and isinstance(val, str):
                        try:
                            clean_val = int(val.replace(",", "").strip())
                            val = f"{clean_val:,}"
                        except ValueError:
                            pass
                    row_values.append(val)
                    
            self.db_sheet.append_row(row_values)
            return {"success": True, "번호": new_num}
        except Exception as e:
            print(f"[Error adding event] {e}")
            raise e
