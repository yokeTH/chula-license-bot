import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, TypedDict, cast

from bs4 import BeautifulSoup, Tag
from rnet import Client, Emulation

# Network debug
# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://licenseportal.it.chula.ac.th"
URL_LOGIN = f"{BASE_URL}/"
URL_BORROW = f"{BASE_URL}/Home/Borrow"


class LicenseConfig(TypedDict):
    id: str
    days: int


LICENSES: Dict[str, LicenseConfig] = {
    "adobe": {"id": "5", "days": 6},
    "foxit": {"id": "7", "days": 89},
    "zoom": {"id": "2", "days": 119},
}


class PortalClient:
    def __init__(self, email: str, password: str) -> None:
        self.email: str = email
        self.password: str = password

        self.client = Client(
            emulation=Emulation.Safari26,
            cookie_store=True,
        )

    @staticmethod
    def _is_redirect(resp: Any) -> bool:
        hist = getattr(resp, "history", None)
        if hist:
            return True
        status = getattr(resp, "status", None)
        return status in (301, 302, 303, 307, 308)

    def _get_form_payload(
        self, html: str, form_action: Optional[str] = None
    ) -> Dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        payload: Dict[str, str] = {}

        container: Any = soup
        if form_action:
            found_form = soup.find("form", action=form_action)
            if found_form:
                container = found_form

        for inp in container.find_all("input"):
            if isinstance(inp, Tag):
                name = inp.get("name")
                value = inp.get("value", "")

                if isinstance(name, str):
                    if isinstance(value, str):
                        payload[name] = value
                    elif value is None:
                        payload[name] = ""
                    else:
                        payload[name] = str(value)

        for sel in container.find_all("select"):
            if not isinstance(sel, Tag):
                continue
            name = sel.get("name")
            if not isinstance(name, str):
                continue

            selected = sel.find("option", selected=True)
            if isinstance(selected, Tag):
                val = selected.get("value", "")
                payload[name] = "" if val is None else str(val)
                continue

            first = sel.find("option")
            if isinstance(first, Tag):
                val = first.get("value", "")
                payload[name] = "" if val is None else str(val)
            else:
                payload[name] = ""

        return payload

    async def login(self) -> None:
        logging.info("Logging in...")

        landing = await self.client.get(URL_LOGIN)
        landing.raise_for_status()

        payload = self._get_form_payload(await landing.text())
        if "__RequestVerificationToken" not in payload:
            raise ValueError("CSRF token missing from login page")

        payload.update(
            {
                "UserName": self.email,
                "Password": self.password,
                "LanguageCode": "Thai",
            }
        )

        login = await self.client.post(
            URL_LOGIN, form=cast(Dict[str, str | int | float | bool], payload)
        )

        login_text = await login.text()

        if "UserName" in login_text and "Password" in login_text:
            raise PermissionError("Login failed. Check credentials.")

    async def borrow(self, license_key: str) -> bool:
        if license_key not in LICENSES:
            logging.error(f"Unknown license key: {license_key}")
            return False

        config = LICENSES[license_key]
        days = config["days"]
        license_id = config["id"]

        logging.info(f"Borrowing: {license_key} (Duration: {days} days)")

        page = await self.client.get(URL_BORROW)
        page.raise_for_status()

        payload = self._get_form_payload(await page.text(), form_action="/Home/Borrow")

        if "__RequestVerificationToken" not in payload:
            logging.error("CSRF token missing on borrow page")
            return False

        now = datetime.now()
        payload.update(
            {
                "ProgramLicenseID": license_id,
                "BorrowDateStr": now.strftime("%d/%m/%Y"),
                "ExpiryDateStr": (now + timedelta(days=days)).strftime("%d/%m/%Y"),
            }
        )

        borrow = await self.client.post(
            URL_BORROW,
            form=cast(Dict[str, str | int | float | bool], payload),
        )
        borrow.raise_for_status()

        if self._is_redirect(borrow):
            return True

        body = await borrow.text()
        if "The field UserPrincipalName is required" in body:
            logging.error("Server rejected payload (Missing UserPrincipalName)")
        else:
            logging.error(
                f"Borrow failed. Status: {getattr(borrow, 'status', 'unknown')}"
            )

        return False
