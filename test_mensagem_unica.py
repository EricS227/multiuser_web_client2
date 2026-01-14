"""
Script para enviar UMA ÚNICA mensagem de teste natural
Usa depois de conectar o WhatsApp
"""
import os
from dotenv import load_dotenv
import asyncio
import sys

# Adiciona o diretório backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from evolution_service import evolution_service

load_dotenv()

async def enviar_teste_unico():
    """Envia apenas 1 mensagem natural de teste"""

    # Número para testar (VOCÊ MESMO - não spam!)
    seu_numero = input("Digite SEU número (com DDD, ex: 5541999999999): ")

    # Mensagem NATURAL (não robótica)
    mensagem = "Oi! Tudo bem? Testando o WhatsApp aqui 😊"

    print(f"\n📱 Enviando mensagem de teste...")
    print(f"Para: {seu_numero}")
    print(f"Mensagem: {mensagem}\n")

    confirmacao = input("Confirma o envio? (s/n): ")

    if confirmacao.lower() != 's':
        print("❌ Cancelado")
        return

    # Temporariamente desabilita warmup mode
    os.environ["WARMUP_MODE"] = "false"

    # Envia a mensagem
    resultado = await evolution_service.send_text_message(seu_numero, mensagem)

    if resultado:
        print("✅ Mensagem enviada com sucesso!")
        print("⏰ Aguarde 5 minutos antes de enviar outra")
    else:
        print("❌ Falha ao enviar. Verifique se está conectado.")

    # Reativa warmup mode
    os.environ["WARMUP_MODE"] = "true"

if __name__ == "__main__":
    print("=" * 50)
    print("TESTE DE MENSAGEM ÚNICA - MODO SEGURO")
    print("=" * 50)
    print("\n⚠️  IMPORTANTE:")
    print("- Envie APENAS para SEU PRÓPRIO número")
    print("- Aguarde 5 minutos antes de enviar outra")
    print("- Nos primeiros 3 dias: máximo 1 mensagem/dia\n")

    asyncio.run(enviar_teste_unico())
