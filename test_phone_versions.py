"""
Script para testar diferentes versões de CONFIG_SESSION_PHONE_VERSION
até encontrar uma que gera QR Code
"""
import subprocess
import time
import requests
import json

API_URL = "http://localhost:8080"
API_KEY = "mude-esta-chave-para-producao"
INSTANCE_NAME = "numero_novo"

# Versões para testar (do mais recente ao mais antigo)
VERSIONS_TO_TEST = [
    "2.2410.1",
    "2.3000.0",
    "2.24.6.77",
    "2.2342.12",
    "2.2346.52",
    "2.2335.6",
    "2.2228.12",
]

def update_docker_compose(version):
    """Atualiza a versão no docker-compose-evolution.yml"""
    with open("docker-compose-evolution.yml", "r", encoding="utf-8") as f:
        content = f.read()

    # Substitui a versão
    import re
    content = re.sub(
        r'CONFIG_SESSION_PHONE_VERSION=[\d\.]+',
        f'CONFIG_SESSION_PHONE_VERSION={version}',
        content
    )

    with open("docker-compose-evolution.yml", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ docker-compose atualizado com versão {version}")

def restart_evolution():
    """Reinicia o container Evolution API"""
    print("🔄 Reiniciando Evolution API...")
    subprocess.run(["docker-compose", "-f", "docker-compose-evolution.yml", "restart", "evolution-api"],
                   check=True, capture_output=True)
    time.sleep(15)  # Aguarda inicialização
    print("✅ Evolution API reiniciado")

def delete_instance():
    """Deleta a instância existente"""
    try:
        response = requests.delete(
            f"{API_URL}/instance/delete/{INSTANCE_NAME}",
            headers={"apikey": API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Instância {INSTANCE_NAME} deletada")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Erro ao deletar instância: {e}")

def create_instance():
    """Cria nova instância"""
    try:
        response = requests.post(
            f"{API_URL}/instance/create",
            headers={
                "apikey": API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "instanceName": INSTANCE_NAME,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True
            },
            timeout=10
        )

        if response.status_code == 200 or response.status_code == 201:
            print(f"✅ Instância {INSTANCE_NAME} criada")
            time.sleep(5)
            return True
        elif "already in use" in response.text:
            print(f"⚠️ Instância já existe")
            return True
        else:
            print(f"❌ Erro ao criar instância: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao criar instância: {e}")
        return False

def check_qr_code():
    """Verifica se QR Code foi gerado"""
    try:
        for attempt in range(3):
            response = requests.get(
                f"{API_URL}/instance/connect/{INSTANCE_NAME}",
                headers={"apikey": API_KEY},
                timeout=10
            )

            data = response.json()
            print(f"   Tentativa {attempt + 1}: {data}")

            if data.get("count", 0) > 0 or data.get("code") or data.get("pairingCode"):
                return True

            time.sleep(3)

        return False
    except Exception as e:
        print(f"❌ Erro ao verificar QR Code: {e}")
        return False

def main():
    print("=" * 60)
    print("TESTE AUTOMÁTICO DE VERSÕES - CONFIG_SESSION_PHONE_VERSION")
    print("=" * 60)
    print()

    for version in VERSIONS_TO_TEST:
        print(f"\n{'=' * 60}")
        print(f"🧪 TESTANDO VERSÃO: {version}")
        print(f"{'=' * 60}")

        # 1. Atualizar docker-compose
        update_docker_compose(version)

        # 2. Reiniciar container
        restart_evolution()

        # 3. Deletar instância antiga
        delete_instance()

        # 4. Criar nova instância
        if not create_instance():
            print(f"❌ Falha ao criar instância com versão {version}")
            continue

        # 5. Verificar QR Code
        print(f"🔍 Verificando se QR Code foi gerado...")
        if check_qr_code():
            print()
            print("=" * 60)
            print(f"✅✅✅ SUCESSO! VERSÃO {version} FUNCIONA! ✅✅✅")
            print("=" * 60)
            print()
            print(f"Acesse: http://localhost:8080/manager/")
            print(f"Ou abra: qrcode-whatsapp.html")
            print()
            return version
        else:
            print(f"❌ Versão {version} não gerou QR Code")

    print()
    print("=" * 60)
    print("❌ NENHUMA VERSÃO FUNCIONOU")
    print("=" * 60)
    print("Possíveis soluções:")
    print("1. Verificar logs: docker logs evolution-api")
    print("2. Desabilitar proxy temporariamente")
    print("3. Tentar versão mais antiga da Evolution API")
    return None

if __name__ == "__main__":
    working_version = main()
    if working_version:
        print(f"\n✅ Configure manualmente: CONFIG_SESSION_PHONE_VERSION={working_version}")
