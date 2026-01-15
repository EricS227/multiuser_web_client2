# Guia de Recuperação - Conta WhatsApp Banida

## 🆘 Ações Imediatas

### 1. Identifique o Tipo de Ban

Abra o WhatsApp e veja a mensagem exata:

- **"Temporariamente banido"** → Ban temporário (12-48h)
- **"Banido por spam"** → Ban por comportamento suspeito
- **"Permanentemente banido"** → Ban definitivo

### 2. Se for Ban Temporário

**Aguarde o período completo:**
- NÃO tente conectar durante o período
- NÃO use bots ou automação
- Após desbloqueio:
  - Use normalmente por 7 dias
  - Não conecte em Evolution API ainda
  - Apenas uso manual

### 3. Se for Ban por Spam

**Tente apelar (chance baixa):**

1. Acesse: https://www.whatsapp.com/contact/
2. Escolha: "Ajuda com minha conta"
3. Selecione: "Minha conta foi banida"
4. Preencha:
   - **Número**: Seu número completo
   - **Explicação**: "Uso comercial legítimo, não envio spam, peço revisão"
   - **E-mail**: Seu e-mail para resposta

**Aguarde:** Resposta em 24-72h (se responderem)

### 4. Se for Ban Permanente

**Não há solução** - Você precisará:
- Usar outro número
- Ou criar WhatsApp Business API oficial

## 📱 Solução: Novo Número com Proteção

### Opção 1: Chip Virtual (Recomendado)

**Provedores brasileiros:**
- **Oi Chip Simples**: R$ 10/mês - www.oi.com.br
- **TIM Beta**: R$ 5/mês - www.tim.com.br
- **Claro Controle**: R$ 40/mês - www.claro.com.br

**Provedores internacionais (mais seguros):**
- **Twilio**: $1/número/mês - www.twilio.com
- **Vonage**: $0.90/mês - www.vonage.com

### Opção 2: WhatsApp Business API Oficial

**Vantagens:**
- ✅ Sem risco de ban
- ✅ Aprovado pelo WhatsApp
- ✅ Suporte oficial
- ✅ Múltiplos usuários

**Provedores:**
- **360Dialog**: €49/mês - www.360dialog.com
- **Twilio**: Pago por mensagem - www.twilio.com
- **Meta (oficial)**: Contato comercial - business.whatsapp.com

**Desvantagens:**
- ❌ Pago
- ❌ Processo de aprovação
- ❌ Requer CNPJ

## 🔐 Como Evitar Novo Ban

### 1. Configure ANTES de Conectar

**Já fizemos:**
- ✅ Proxy configurado (64.137.96.74:6641)
- ✅ Evolution API atualizada
- ✅ Instância segura criada

### 2. Protocolo de Aquecimento (IMPORTANTE)

**Dia 1-3: Apenas Receber**
- Configure webhook
- Receba mensagens (não envie)
- Responda MANUALMENTE se necessário

**Dia 4-7: Envio Mínimo**
- Máximo 10 mensagens/dia
- Intervalo de 5 minutos entre mensagens
- Apenas para quem enviou primeiro

**Dia 8-14: Aumento Gradual**
- Máximo 20 mensagens/dia
- Intervalo de 3 minutos
- Continue priorizando quem envia primeiro

**Dia 15+: Uso Normal**
- Máximo 50 mensagens/dia
- Intervalo de 1 minuto
- Evite mensagens em massa

### 3. Regras de Ouro

**NUNCA faça:**
- ❌ Enviar para quem não pediu
- ❌ Mensagens em massa
- ❌ Copiar/colar texto idêntico
- ❌ Enviar links encurtados
- ❌ Usar palavras de spam ("GRÁTIS", "GANHE", "CLIQUE")
- ❌ Conectar em múltiplos dispositivos
- ❌ Mudar de IP frequentemente

**SEMPRE faça:**
- ✅ Use proxy residencial
- ✅ Aguarde aquecimento
- ✅ Personalize mensagens
- ✅ Espere usuário iniciar conversa
- ✅ Respeite horário comercial
- ✅ Tenha opt-out fácil ("pare" = parar)

### 4. Rate Limiting no Código

Vou adicionar proteção automática no código:

```python
# backend/evolution_service.py
import time
from datetime import datetime, timedelta

class EvolutionAPIService:
    def __init__(self):
        self.last_send_time = {}
        self.min_interval = 60  # 60 segundos entre mensagens

    async def send_text_message(self, to_number, message):
        # Rate limiting
        now = time.time()
        if to_number in self.last_send_time:
            elapsed = now - self.last_send_time[to_number]
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                print(f"⏳ Rate limit: aguardando {wait_time:.0f}s antes de enviar")
                await asyncio.sleep(wait_time)

        # Enviar mensagem
        result = await self._send_message(to_number, message)

        # Atualizar timestamp
        self.last_send_time[to_number] = time.time()

        return result
```

## 📊 Monitoramento

### Sinais de Alerta

Se você notar isso, PARE imediatamente:

- ⚠️ Mensagens demorando muito para enviar
- ⚠️ Mensagens não entregues
- ⚠️ Aviso de "comportamento incomum"
- ⚠️ QR Code desconectando sozinho
- ⚠️ Contatos reportando suas mensagens

### Dashboard de Segurança

Monitore diariamente:
- Mensagens enviadas/dia
- Taxa de entrega
- Tempo entre mensagens
- Reclamações de spam

## 🆘 Contatos de Emergência

**WhatsApp Suporte:**
- Web: https://www.whatsapp.com/contact/
- E-mail: support@whatsapp.com

**Evolution API:**
- Discord: https://discord.gg/evolutionapi
- GitHub: https://github.com/EvolutionAPI/evolution-api/issues

**Este Projeto:**
- Documentação: DEPLOYMENT.md
- Configuração: .env

## ✅ Checklist Novo Número

Antes de conectar novo número:

- [ ] Proxy configurado e testado
- [ ] Número novo (nunca usado em bot)
- [ ] Evolution API atualizada
- [ ] Rate limiting ativado
- [ ] Webhook configurado
- [ ] Aquecimento planejado (15 dias)
- [ ] Monitoramento configurado
- [ ] Plano B definido

## 📞 Próximos Passos

1. **Aguardar 24-48h** (se ban temporário)
2. **Apelar** (se achar que foi engano)
3. **Conseguir novo número**
4. **Seguir protocolo de aquecimento**
5. **Testar gradualmente**

**Lembre-se:** É melhor ir devagar e ter sucesso do que rápido e ser banido novamente!
