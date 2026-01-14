# -*- coding: utf-8 -*-
"""
Script to test sending WhatsApp message with correct UTF-8 encoding
"""
import sys
import io
# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json

def send_test_message():
    """Send a test message via Evolution API with proper UTF-8 encoding"""

    url = "http://localhost:8080/message/sendText/Endpoint%20Security"

    headers = {
        "apikey": "mude-esta-chave-para-producao",
        "Content-Type": "application/json; charset=utf-8"
    }

    # Follow-up message asking for more info
    payload = {
        "number": "5541999954068",
        "text": "Desculpe a demora! Estamos com um pequeno problema tecnico. Pode me informar qual sistema operacional voce usa?",
        "delay": 0
    }

    try:
        # Ensure JSON is encoded as UTF-8
        response = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers=headers
        )

        print(f"Status Code: {response.status_code}")

        resp_json = response.json()
        print(f"Response: {resp_json}")

        # Check what was actually sent
        if 'message' in resp_json and 'conversation' in resp_json['message']:
            actual_text = resp_json['message']['conversation']
            print(f"\n=== COMPARACAO ===")
            print(f"Texto desejado: {payload['text']}")
            print(f"Texto enviado:  {actual_text}")
            print(f"Encodings match: {payload['text'] == actual_text}")

        if response.status_code in [200, 201]:
            print("\nMensagem enviada com sucesso!")
        else:
            print(f"\nErro ao enviar: {response.text}")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    send_test_message()
