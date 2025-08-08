"""
import subprocess
import time
from threading import Thread


def ensure_ngrok_running(port=8000, max_retries=3):
    for attempt in range(max_retries):
        url = get_ngrok_url()
        if url:
            print(f"Ngrok já está rodando: {url}")
            return url
        
        print(f"tentativa {attempt + 1}: iniciando ngrok...")
              
        try:
            subprocess.Popen(['ngrok', 'http', str(port)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            time.sleep(5)

            url = get_ngrok_url()
            if url:
                print(f"Ngrok iniciado com sucesso: {url}")
                return url
"""