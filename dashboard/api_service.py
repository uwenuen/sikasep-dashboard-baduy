import os
import requests
from dotenv import load_dotenv

load_dotenv()


class SiKasepAPI:
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "").rstrip("/")
        self.identifier = os.getenv("API_ADMIN_IDENTIFIER")
        self.password = os.getenv("API_ADMIN_PASSWORD")
        self.token = None

    # =====================================================
    # LOGIN
    # =====================================================
    def login(self):
        """Login ke API SI-KASEP dan menyimpan JWT Token"""

        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={
                    "identifier": self.identifier,
                    "password": self.password
                },
                timeout=10
            )

            if response.status_code != 200:
                print("Login API gagal :", response.status_code)
                return False

            data = response.json()

            self.token = (
                data.get("token")
                or data.get("access_token")
                or data.get("data", {}).get("token")
                or data.get("data", {}).get("access_token")
            )

            return self.token is not None

        except Exception as e:
            print("Tidak dapat login ke API :", e)
            return False

    # =====================================================
    # HEADER
    # =====================================================
    def _get_headers(self):

        if self.token is None:

            if not self.login():
                return None

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    # =====================================================
    # GENERIC GET
    # =====================================================
    def _get(self, endpoint):

        headers = self._get_headers()

        if headers is None:
            return None

        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=15
            )

            print("=" * 60)
            print("GET :", endpoint)
            print("STATUS :", response.status_code)
            print("BODY :", response.text)
            print("=" * 60)

            if response.status_code == 200:
                return response.json()

            print(
                f"GET {endpoint} gagal :",
                response.status_code
            )

            return None

        except Exception as e:

            print(f"GET {endpoint} error :", e)

            return None

    # =====================================================
    # GENERIC POST
    # =====================================================
    def _post(self, endpoint, payload=None):

        headers = self._get_headers()

        if headers is None:
            return None

        try:

            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers=headers,
                timeout=15
            )

            if response.status_code in [200, 201]:

                return response.json()

            print(
                f"POST {endpoint} gagal :",
                response.status_code
            )

            return None

        except Exception as e:

            print(f"POST {endpoint} error :", e)

            return None

    # =====================================================
    # DASHBOARD
    # =====================================================
    def get_dashboard_summary(self):
        return self._get("/dashboard/summary")

    # =====================================================
    # CITIZENS
    # =====================================================
    def get_citizens(self):
        return self._get("/citizens")

    # =====================================================
    # SCREENINGS
    # =====================================================
    def get_screenings(self):
        return self._get("/screenings")

    # =====================================================
    # CADRES
    # =====================================================
    def get_cadres(self):
        return self._get("/cadres")

    # =====================================================
    # REGIONS
    # =====================================================
    def get_regions(self):
        return self._get("/regions")

    # =====================================================
    # MEDICATIONS
    # =====================================================
    def get_medications(self):
        return self._get("/medications")

    # =====================================================
    # REFERRALS
    # =====================================================
    def get_referrals(self):
        return self._get("/referrals")

    # =====================================================
    # EDUCATIONS
    # =====================================================
    def get_educations(self):
        return self._get("/educations")

    # =====================================================
    # SETTINGS
    # =====================================================
    def get_settings(self):
        return self._get("/settings")

    # =====================================================
    # REPORT SCREENING
    # =====================================================
    def get_screening_report(self):
        return self._get("/reports/screening")
    
    def download_screening_pdf(self, params=None):
        """
        Download PDF laporan skrining??????
        """

        url = f"{self.base_url}/reports/screening.pdf"

        headers = self._get_headers()

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                return response.content

            print("STATUS :", response.status_code)
            print("BODY :", response.text)

            return None

        except requests.exceptions.RequestException as e:
            print(e)
            return None