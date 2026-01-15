#!/usr/bin/env python3
"""
Script para verificar se Evolution API está configurada corretamente
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def check_evolution():
    print("\n" + "="*60)
    print("🔍 VERIFICAÇÃO EVOLUTION API - FAST_API2")
    print("="*60 + "\n")

    # 1. Verificar variáveis de ambiente
    print("📋 1. Verificando variáveis de ambiente...")

    enabled = os.getenv("EVOLUTION_ENABLED", "false")
    api_url = os.getenv("EVOLUTION_API_URL", "")
    api_key = os.getenv("EVOLUTION_API_KEY", "")
    instance = os.getenv("EVOLUTION_INSTANCE_NAME", "")
    webhook = os.getenv("EVOLUTION_WEBHOOK_URL", "")

    print(f"   EVOLUTION_ENABLED: {enabled}")
    print(f"   EVOLUTION_API_URL: {api_url}")
    print(f"   EVOLUTION_API_KEY: {'*' * 20 if api_key else 'NÃO CONFIGURADO'}")
    print(f"   EVOLUTION_INSTANCE_NAME: {instance}")
    print(f"   EVOLUTION_WEBHOOK_URL: {webhook}")

    if enabled.lower() != "true":
        print("\n   ❌ EVOLUTION_ENABLED=false")
        print("   👉 Mude para EVOLUTION_ENABLED=true no .env\n")
        return

    if not api_url:
        print("\n   ❌ EVOLUTION_API_URL não configurado")
        print("   👉 Adicione EVOLUTION_API_URL=http://localhost:8080 no .env\n")
        return

    print("   ✅ Variáveis de ambiente OK\n")

    # 2. Verificar se Evolution API está respondendo
    print("📡 2. Verificando conexão com Evolution API...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                print(f"   ✅ Evolution API respondendo em {api_url}")
            else:
                print(f"   ⚠️  Evolution API retornou status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Não conseguiu conectar à Evolution API: {e}")
        print(f"   👉 Verifique se Evolution API está rodando em {api_url}\n")
        return

    print()

    # 3. Verificar instância
    print(f"📱 3. Verificando instância '{instance}'...")
    try:
        headers = {"apikey": api_key}
        url = f"{api_url}/instance/connectionState/{instance}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                state = data.get("state", "unknown")

                if state == "open":
                    print(f"   ✅ Instância CONECTADA! Estado: {state}")
                elif state == "close":
                    print(f"   ⚠️  Instância DESCONECTADA. Estado: {state}")
                    print(f"   👉 Execute: python setup_evolution.py para gerar QR code")
                else:
                    print(f"   ℹ️  Instância em estado: {state}")
            elif response.status_code == 404:
                print(f"   ❌ Instância '{instance}' não existe")
                print(f"   👉 Execute: python setup_evolution.py para criar")
            else:
                print(f"   ⚠️  Erro ao verificar instância: {response.status_code}")
                print(f"   Resposta: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    print()

    # 4. Verificar FastAPI
    print("🚀 4. Verificando FastAPI...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("   ✅ FastAPI rodando em http://localhost:8000")
            else:
                print(f"   ⚠️  FastAPI retornou status {response.status_code}")
    except Exception as e:
        print(f"   ❌ FastAPI não está rodando: {e}")
        print(f"   👉 Execute: uvicorn backend.main:app --reload")

    print()

    # 5. Resumo
    print("="*60)
    print("📊 RESUMO")
    print("="*60)
    print("\n✅ Tudo OK? Próximos passos:")
    print("   1. Se instância desconectada: python setup_evolution.py")
    print("   2. Se FastAPI não rodando: uvicorn backend.main:app --reload")
    print("   3. Testar webhook: Envie mensagem WhatsApp para o número conectado")
    print("\n📖 Documentação completa: EVOLUTION_API_INTEGRATION.md\n")

if __name__ == "__main__":
    asyncio.run(check_evolution())
