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
                
        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID가 설정되지 않았습니다. (환경변수 SPREADSHEET_ID 또는 config.json 필요)")
            
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 2. 구글 크리덴셜 결정 (환경 변수 우선, 파일 차선)
        google_creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        
        if google_creds_json:
            # Vercel 환경 변수에 설정된 JSON 문자열 사용
            try:
                cred_info = json.loads(google_creds_json)
                creds = Credentials.from_service_account_info(cred_info, scopes=scopes)
                print("[SheetsClient] Loaded credentials from environment variable GOOGLE_CREDENTIALS")
            except Exception as e:
                raise ValueError(f"GOOGLE_CREDENTIALS 환경 변수 파싱 실패: {e}")
        elif os.path.exists(cred_path):
            # 로컬 파일 사용
            creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
            print(f"[SheetsClient] Loaded credentials from file {cred_path}")
        else:
            raise ValueError("Google Credentials가 존재하지 않습니다. (config/credentials.json 파일 또는 GOOGLE_CREDENTIALS 환경변수 필요)")
            
        self.client = gspread.authorize(creds)
        self.doc = self.client.open_by_key(self.spreadsheet_id)
        
        # 첫 번째 시트 (경조사 DB)
        self.db_sheet = self.doc.worksheets()[0]
        
        # AllowedUsers 시트 찾기
        self.allowed_users_sheet = None
        for ws in self.doc.worksheets():
            if ws.title in ["AllowedUsers", "접근권한"]:
                self.allowed_users_sheet = ws
                break
                
    def get_allowed_emails(self):
        """허가된 이메일 목록을 스프레드시트에서 조회합니다."""
        if not self.allowed_users_sheet:
            return []
        try:
            records = self.allowed_users_sheet.get_all_records()
            emails = []
            for r in records:
                for k, v in r.items():
                    if k.lower() == "email" and v:
                        emails.append(str(v).strip().lower())
            return emails
        except Exception as e:
            print(f"[Error fetching allowed emails] {e}")
            return []
            
    def search_events(self, query: str):
        """이름을 기준으로 경조사 데이터를 검색합니다."""
        try:
            records = self.db_sheet.get_all_records()
            query = query.strip().lower()
            if not query:
                return []
                
            results = []
            for r in records:
                name = str(r.get("이름", "")).strip().lower()
                if query in name:
                    results.append(r)
            return results
        except Exception as e:
            print(f"[Error searching events] {e}")
            return []
            
    def add_event(self, data: dict):
        """새로운 경조사 이벤트를 스프레드시트에 추가합니다."""
        try:
            records = self.db_sheet.get_all_records()
            last_num = 0
            if records:
                try:
                    last_num = int(records[-1].get("번호", 0))
                except ValueError:
                    last_num = len(records)
            
            new_num = last_num + 1
            
            # 헤더 순서에 맞춰 값 리스트 작성
            # 번호, 날짜, 이름, 경조사명, 회사, 누구, 입출금, 축의금, 참석, 입출금방법, Remark
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
            return {"success": False, "error": str(e)}
