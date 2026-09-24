import base64
import json
import requests

BASE_URL = "http://127.0.0.1:8000"


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload mà không cần verify signature."""
    try:
        payload_part = token.split(".")[1]
        # Thêm padding nếu thiếu
        padding = 4 - len(payload_part) % 4
        payload_part += "=" * (padding % 4)
        return json.loads(base64.urlsafe_b64decode(payload_part))
    except Exception:
        return {}


class ApiClient:
    def __init__(self):
        self.token = None
        self.role = None
        self.username = None

    def login(self, username, password):
        try:
            r = requests.post(
                f"{BASE_URL}/auth/login",
                data={"username": username, "password": password},
            )
        except requests.exceptions.ConnectionError:
            return False, "Không kết nối được server. Hãy chắc chắn backend đang chạy."

        if r.status_code == 200:
            self.token = r.json()["access_token"]
            payload = _decode_jwt_payload(self.token)
            self.role = payload.get("role", "").upper()
            self.username = payload.get("username") or str(payload.get("sub", username))
            return True, None
        try:
            return False, r.json().get("detail", "Lỗi đăng nhập")
        except Exception:
            return False, "Lỗi đăng nhập không xác định"

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, path, params=None):
        return requests.get(f"{BASE_URL}{path}", headers=self._headers(), params=params)

    def post(self, path, json=None):
        return requests.post(f"{BASE_URL}{path}", headers=self._headers(), json=json)

    def put(self, path, json=None):
        return requests.put(f"{BASE_URL}{path}", headers=self._headers(), json=json)

    def delete(self, path):
        return requests.delete(f"{BASE_URL}{path}", headers=self._headers())


api_client = ApiClient()
