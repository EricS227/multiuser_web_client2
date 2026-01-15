"""
Evolution API integration service for WhatsApp messaging
Modern replacement for Twilio with full WhatsApp features
"""
import os
import httpx
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class EvolutionAPIService:
    """Service to interact with Evolution API"""

    def __init__(self):
        self.base_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
        self.api_key = os.getenv("EVOLUTION_API_KEY", "")
        self.instance_name = os.getenv("EVOLUTION_INSTANCE_NAME", "chatapp")
        self.enabled = os.getenv("EVOLUTION_ENABLED", "false").lower() == "true"

        if self.enabled:
            print(f"Evolution API enabled - URL: {self.base_url}, Instance: {self.instance_name}")
        else:
            print("Evolution API disabled - Set EVOLUTION_ENABLED=true in .env to enable")

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "apikey": self.api_key
        }

    async def create_instance(self) -> Optional[dict]:
        """
        Create a new WhatsApp instance

        Returns:
            Instance data including QR code or None if failed
        """
        if not self.enabled:
            return None

        try:
            url = f"{self.base_url}/instance/create"

            payload = {
                "instanceName": self.instance_name,
                "token": self.api_key,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())

                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"Evolution API: Instance created - {self.instance_name}")
                    return result
                else:
                    print(f"Evolution API error creating instance: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"Evolution API exception: {e}")
            return None

    async def get_instance_status(self) -> Optional[dict]:
        """Check instance connection status"""
        if not self.enabled:
            return {"state": "disabled"}

        try:
            url = f"{self.base_url}/instance/connectionState/{self.instance_name}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers())

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"state": "error", "message": response.text}

        except Exception as e:
            return {"state": "error", "message": str(e)}

    async def get_qrcode(self) -> Optional[dict]:
        """
        Get QR code for WhatsApp authentication

        Returns:
            QR code data (base64 image) or None
        """
        if not self.enabled:
            return None

        try:
            url = f"{self.base_url}/instance/connect/{self.instance_name}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._get_headers())

                if response.status_code == 200:
                    result = response.json()
                    print(f"Evolution API: QR Code retrieved for {self.instance_name}")
                    return result
                else:
                    print(f"Evolution API QR code error: {response.status_code}")
                    return None

        except Exception as e:
            print(f"Evolution API QR code exception: {e}")
            return None

    async def send_text_message(self, to_number: str, message: str) -> Optional[dict]:
        """
        Send WhatsApp text message via Evolution API

        Args:
            to_number: Phone number (format: 5541999999999)
            message: Message text

        Returns:
            Response dict or None if failed
        """
        if not self.enabled:
            print("Evolution API not enabled")
            return None

        try:
            # Clean phone number (remove + and whatsapp: prefix)
            clean_number = to_number.replace("+", "").replace("whatsapp:", "").strip()

            url = f"{self.base_url}/message/sendText/{self.instance_name}"

            payload = {
                "number": clean_number,
                "text": message,
                "delay": 0
            }

            # Encode payload as UTF-8 JSON to ensure proper character handling
            json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, content=json_data, headers=self._get_headers())

                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"Evolution API: Message sent to {to_number}")
                    return result
                else:
                    print(f"Evolution API send error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            print(f"Evolution API send exception: {e}")
            return None

    async def send_media(self, to_number: str, media_url: str, caption: str = "") -> Optional[dict]:
        """
        Send WhatsApp media (image, video, document)

        Args:
            to_number: Phone number
            media_url: URL of media file
            caption: Optional caption

        Returns:
            Response dict or None
        """
        if not self.enabled:
            return None

        try:
            clean_number = to_number.replace("+", "").replace("whatsapp:", "").strip()

            url = f"{self.base_url}/message/sendMedia/{self.instance_name}"

            payload = {
                "number": clean_number,
                "mediaUrl": media_url,
                "caption": caption
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())

                if response.status_code in [200, 201]:
                    print(f"Evolution API: Media sent to {to_number}")
                    return response.json()
                else:
                    print(f"Evolution API media error: {response.status_code}")
                    return None

        except Exception as e:
            print(f"Evolution API media exception: {e}")
            return None

    async def set_webhook(self, webhook_url: str, events: list = None) -> Optional[dict]:
        """
        Configure webhook to receive messages

        Args:
            webhook_url: Your webhook URL (e.g., https://yourdomain.com/webhook/evolution)
            events: List of events to listen (default: all message events)

        Returns:
            Webhook configuration or None
        """
        if not self.enabled:
            return None

        if events is None:
            events = [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "CONNECTION_UPDATE",
                "QRCODE_UPDATED"
            ]

        try:
            url = f"{self.base_url}/webhook/set/{self.instance_name}"

            payload = {
                "url": webhook_url,
                "webhook_by_events": False,
                "webhook_base64": False,
                "events": events,
                "enabled": True
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=self._get_headers())

                if response.status_code in [200, 201]:
                    print(f"Evolution API: Webhook configured - {webhook_url}")
                    return response.json()
                else:
                    print(f"Evolution API webhook error: {response.status_code}")
                    return None

        except Exception as e:
            print(f"Evolution API webhook exception: {e}")
            return None

    async def logout(self) -> Optional[dict]:
        """Logout from WhatsApp instance"""
        if not self.enabled:
            return None

        try:
            url = f"{self.base_url}/instance/logout/{self.instance_name}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(url, headers=self._get_headers())

                if response.status_code == 200:
                    print(f"Evolution API: Instance logged out - {self.instance_name}")
                    return response.json()
                else:
                    return {"status": "error", "message": response.text}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def delete_instance(self) -> Optional[dict]:
        """Delete WhatsApp instance"""
        if not self.enabled:
            return None

        try:
            url = f"{self.base_url}/instance/delete/{self.instance_name}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(url, headers=self._get_headers())

                if response.status_code == 200:
                    print(f"Evolution API: Instance deleted - {self.instance_name}")
                    return response.json()
                else:
                    return {"status": "error", "message": response.text}

        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global instance
evolution_service = EvolutionAPIService()
