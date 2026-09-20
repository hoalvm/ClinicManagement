import requests

BASE_URL = "http://127.0.0.1:8000"

class ApiClient:
    def __init__(self):
        self.token = None

    def login(self, username, password):
        try:
            r = requests.post(
                f"{BASE_URL}/auth/login",
                data={"username": username, "password": password}
            )
        except requests.exceptions.ConnectionError:
            return False, "Không kết nối được server. Hãy chắc chắn backend đang chạy."

        if r.status_code == 200:
            self.token = r.json()["access_token"]
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