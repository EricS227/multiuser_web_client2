#!/usr/bin/env python3
"""
Evolution API Setup Helper
Automated setup script for Evolution API integration
"""
import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv, set_key

load_dotenv()


class EvolutionSetup:
    def __init__(self):
        self.base_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
        self.api_key = os.getenv("EVOLUTION_API_KEY", "B6D711FCDE4D4FD5936544120E713976")
        self.instance_name = os.getenv("EVOLUTION_INSTANCE_NAME", "chatapp")

    async def check_evolution_api(self):
        """Check if Evolution API is running"""
        print("\n🔍 Checking Evolution API...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.base_url)
                if response.status_code == 200:
                    print(f"✅ Evolution API is running at {self.base_url}")
                    return True
                else:
                    print(f"❌ Evolution API returned status {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to Evolution API: {e}")
            print(f"\n💡 Start Evolution API with:")
            print(f"   docker-compose -f docker-compose-evolution.yml up -d")
            return False

    async def create_instance(self):
        """Create WhatsApp instance"""
        print(f"\n📱 Creating instance '{self.instance_name}'...")

        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        payload = {
            "instanceName": self.instance_name,
            "token": self.api_key,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }

        try:
            url = f"{self.base_url}/instance/create"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in [200, 201]:
                    data = response.json()
                    print(f"✅ Instance created successfully!")
                    return data
                elif response.status_code == 400:
                    print(f"⚠️  Instance may already exist")
                    return await self.get_qrcode()
                else:
                    print(f"❌ Error: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None

    async def get_qrcode(self):
        """Get QR code for authentication"""
        print(f"\n📲 Getting QR Code for '{self.instance_name}'...")

        headers = {"apikey": self.api_key}

        try:
            url = f"{self.base_url}/instance/connect/{self.instance_name}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ QR Code retrieved!")

                    if "base64" in data:
                        print(f"\n🔗 QR Code Base64:")
                        print(f"   {data['base64'][:100]}...")
                        print(f"\n💡 Open this in browser to see QR code:")
                        print(f"   data:image/png;base64,{data.get('base64', '')}")

                    if "code" in data:
                        print(f"\n📋 QR Code string:")
                        print(f"   {data['code'][:50]}...")

                    return data
                else:
                    print(f"❌ Error: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None

    async def check_status(self):
        """Check instance connection status"""
        print(f"\n🔍 Checking instance status...")

        headers = {"apikey": self.api_key}

        try:
            url = f"{self.base_url}/instance/connectionState/{self.instance_name}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    state = data.get("state", "unknown")

                    if state == "open":
                        print(f"✅ Instance is CONNECTED!")
                    elif state == "close":
                        print(f"⚠️  Instance is DISCONNECTED - scan QR code")
                    else:
                        print(f"ℹ️  Instance state: {state}")

                    return data
                else:
                    print(f"❌ Error: {response.status_code}")
                    return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None

    async def configure_webhook(self):
        """Configure webhook for receiving messages"""
        webhook_url = os.getenv("EVOLUTION_WEBHOOK_URL", "http://localhost:8000/webhook/evolution")

        print(f"\n🪝 Configuring webhook: {webhook_url}")

        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

        payload = {
            "url": webhook_url,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "CONNECTION_UPDATE",
                "QRCODE_UPDATED"
            ],
            "enabled": True
        }

        try:
            url = f"{self.base_url}/webhook/set/{self.instance_name}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in [200, 201]:
                    print(f"✅ Webhook configured successfully!")
                    return response.json()
                else:
                    print(f"❌ Error: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None

    def update_env_file(self):
        """Update .env file with Evolution settings"""
        print(f"\n📝 Updating .env file...")

        env_file = ".env"

        if not os.path.exists(env_file):
            print(f"⚠️  .env file not found, creating new one")
            with open(env_file, 'w') as f:
                f.write("")

        set_key(env_file, "EVOLUTION_ENABLED", "true")
        set_key(env_file, "EVOLUTION_API_URL", self.base_url)
        set_key(env_file, "EVOLUTION_API_KEY", self.api_key)
        set_key(env_file, "EVOLUTION_INSTANCE_NAME", self.instance_name)

        print(f"✅ .env file updated")


async def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║         Evolution API Setup Helper                         ║
║         FastAPI WhatsApp Integration                       ║
╚═══════════════════════════════════════════════════════════╝
    """)

    setup = EvolutionSetup()

    # Step 1: Check if Evolution API is running
    if not await setup.check_evolution_api():
        return

    # Step 2: Create instance
    instance_data = await setup.create_instance()
    if not instance_data:
        return

    # Step 3: Get QR Code
    qr_data = await setup.get_qrcode()

    if qr_data:
        print("\n" + "="*60)
        print("📱 NEXT STEPS:")
        print("="*60)
        print("1. Open WhatsApp on your phone")
        print("2. Go to: Settings > Linked Devices")
        print("3. Tap 'Link a Device'")
        print("4. Scan the QR code shown above")
        print("="*60)

        input("\n⏸️  Press Enter after scanning QR code...")

    # Step 4: Check connection status
    await setup.check_status()

    # Step 5: Configure webhook
    await setup.configure_webhook()

    # Step 6: Update .env
    setup.update_env_file()

    print("""
╔═══════════════════════════════════════════════════════════╗
║              Setup Complete! ✅                            ║
╚═══════════════════════════════════════════════════════════╝

Your Evolution API is now configured!

Next steps:
1. Restart your FastAPI server
2. Send a message to your WhatsApp number
3. The chatbot will respond automatically

Test with:
  python -m uvicorn backend.main:app --reload

Send test message:
  curl -X POST http://localhost:8000/test-bot \\
    -H "Content-Type: application/json" \\
    -d '{"phone_number": "5541999999999", "message": "Olá!"}'

Documentation: EVOLUTION_API_INTEGRATION.md
    """)


if __name__ == "__main__":
    asyncio.run(main())
