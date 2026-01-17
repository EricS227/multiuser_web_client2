"""
WAHA (WhatsApp HTTP API) Service
Handles WhatsApp messaging through WAHA
"""

import os
import httpx
from typing import Optional, Dict, Any

class WAHAService:
    """Service for interacting with WAHA API"""

    def __init__(self):
        self.enabled = os.getenv("WAHA_ENABLED", "false").lower() == "true"
        self.base_url = os.getenv("WAHA_API_URL", "http://localhost:3000")
        self.api_key = os.getenv("WAHA_API_KEY", "")
        self.session_name = os.getenv("WAHA_SESSION_NAME", "default")

        if self.enabled:
            print(f"WAHA Service enabled - URL: {self.base_url}, Session: {self.session_name}")
        else:
            print("WAHA Service disabled")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    async def start_session(self) -> Optional[Dict]:
        """Start a new WhatsApp session"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sessions/start",
                    headers=self._get_headers(),
                    json={"name": self.session_name}
                )
                if response.status_code in [200, 201]:
                    return response.json()
                print(f"WAHA start session error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"WAHA start session exception: {e}")
            return None

    async def stop_session(self) -> Optional[Dict]:
        """Stop the WhatsApp session"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sessions/stop",
                    headers=self._get_headers(),
                    json={"name": self.session_name}
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            print(f"WAHA stop session exception: {e}")
            return None

    async def get_session_status(self) -> Optional[Dict]:
        """Get session status"""
        if not self.enabled:
            return {"status": "disabled"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/sessions/{self.session_name}",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    return response.json()
                return {"status": "not_found"}
        except Exception as e:
            print(f"WAHA get status exception: {e}")
            return {"status": "error", "message": str(e)}

    async def get_qrcode(self) -> Optional[Dict]:
        """Get QR code for authentication"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/sessions/{self.session_name}/auth/qr",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            print(f"WAHA get QR exception: {e}")
            return None

    async def send_text_message(self, to_number: str, message: str) -> Optional[Dict]:
        """Send a text message via WhatsApp"""
        if not self.enabled:
            print("WAHA not enabled, cannot send message")
            return None

        # Format number (remove + and add @c.us)
        chat_id = to_number.replace("+", "").replace(" ", "")
        if not chat_id.endswith("@c.us"):
            chat_id = f"{chat_id}@c.us"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendText",
                    headers=self._get_headers(),
                    json={
                        "session": self.session_name,
                        "chatId": chat_id,
                        "text": message
                    }
                )
                if response.status_code in [200, 201]:
                    print(f"WAHA: Message sent to {to_number}")
                    return response.json()
                print(f"WAHA send message error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"WAHA send message exception: {e}")
            return None

    async def send_image(self, to_number: str, image_url: str, caption: str = "") -> Optional[Dict]:
        """Send an image via WhatsApp"""
        if not self.enabled:
            return None

        chat_id = to_number.replace("+", "").replace(" ", "")
        if not chat_id.endswith("@c.us"):
            chat_id = f"{chat_id}@c.us"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendImage",
                    headers=self._get_headers(),
                    json={
                        "session": self.session_name,
                        "chatId": chat_id,
                        "file": {"url": image_url},
                        "caption": caption
                    }
                )
                if response.status_code in [200, 201]:
                    return response.json()
                return None
        except Exception as e:
            print(f"WAHA send image exception: {e}")
            return None

    async def send_document(self, to_number: str, doc_url: str, filename: str) -> Optional[Dict]:
        """Send a document via WhatsApp"""
        if not self.enabled:
            return None

        chat_id = to_number.replace("+", "").replace(" ", "")
        if not chat_id.endswith("@c.us"):
            chat_id = f"{chat_id}@c.us"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sendFile",
                    headers=self._get_headers(),
                    json={
                        "session": self.session_name,
                        "chatId": chat_id,
                        "file": {"url": doc_url},
                        "filename": filename
                    }
                )
                if response.status_code in [200, 201]:
                    return response.json()
                return None
        except Exception as e:
            print(f"WAHA send document exception: {e}")
            return None

    async def get_chats(self) -> Optional[list]:
        """Get list of chats"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/{self.session_name}/chats",
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            print(f"WAHA get chats exception: {e}")
            return None

    async def logout(self) -> Optional[Dict]:
        """Logout from WhatsApp"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/sessions/logout",
                    headers=self._get_headers(),
                    json={"name": self.session_name}
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            print(f"WAHA logout exception: {e}")
            return None


# Singleton instance
waha_service = WAHAService()
