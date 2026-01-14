"""
WPPConnect integration service for WhatsApp messaging
Replaces Twilio with free WPPConnect API
"""
import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class WPPConnectService:
    """Service to interact with WPPConnect API"""

    def __init__(self):
        self.base_url = os.getenv("WPPCONNECT_URL", "http://localhost:21465")
        self.secret_key = os.getenv("WPPCONNECT_SECRET_KEY", "My53cr3tKY")
        self.session_name = os.getenv("WPPCONNECT_SESSION", "mySession")
        self.enabled = os.getenv("WPPCONNECT_ENABLED", "false").lower() == "true"

        if self.enabled:
            print(f"WPPConnect enabled - URL: {self.base_url}, Session: {self.session_name}")
        else:
            print("WPPConnect disabled - Set WPPCONNECT_ENABLED=true in .env to enable")

    async def send_message(self, to_number: str, message: str) -> Optional[dict]:
        """
        Send WhatsApp message via WPPConnect

        Args:
            to_number: Phone number (format: +5541999999999)
            message: Message text

        Returns:
            Response dict or None if failed
        """
        if not self.enabled:
            print("WPPConnect not enabled")
            return None

        try:
            # Clean phone number (remove + and whatsapp: prefix)
            clean_number = to_number.replace("+", "").replace("whatsapp:", "").strip()

            # WPPConnect expects format: 5541999999999@c.us
            formatted_number = f"{clean_number}@c.us"

            url = f"{self.base_url}/api/{self.session_name}/send-message"

            payload = {
                "phone": formatted_number,
                "message": message,
                "isGroup": False
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.secret_key}"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 200 or response.status_code == 201:
                    result = response.json()
                    print(f"WPPConnect: Message sent to {to_number}")
                    return result
                else:
                    print(f"WPPConnect error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"WPPConnect exception: {e}")
            return None

    async def get_status(self) -> dict:
        """Check WPPConnect session status"""
        if not self.enabled:
            return {"status": "disabled"}

        try:
            url = f"{self.base_url}/api/{self.session_name}/status-session"
            headers = {"Authorization": f"Bearer {self.secret_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": response.text}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def start_session(self) -> dict:
        """Start WPPConnect session and get QR code"""
        if not self.enabled:
            return {"status": "disabled"}

        try:
            url = f"{self.base_url}/api/{self.session_name}/start-session"

            payload = {
                "webhook": os.getenv("WPPCONNECT_WEBHOOK_URL", "http://localhost:8000/webhook/wppconnect"),
                "waitQrCode": True
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.secret_key}"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": response.text}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def close_session(self) -> dict:
        """Close WPPConnect session"""
        if not self.enabled:
            return {"status": "disabled"}

        try:
            url = f"{self.base_url}/api/{self.session_name}/close-session"
            headers = {"Authorization": f"Bearer {self.secret_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": response.text}

        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global instance
wppconnect_service = WPPConnectService()
