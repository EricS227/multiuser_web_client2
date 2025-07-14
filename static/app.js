let token = "";
let selectedConversation = null;
let ws = null;

function connectWebSocket() {
  ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const msgDiv = document.createElement("div");
    msgDiv.textContent = `${data.sender}: ${data.message || data.content}`;
    document.getElementById("messages").appendChild(msgDiv);
  };
}

async function login() {
  const res = await fetch("http://localhost:8000/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      username: "agent@example.com",
      password: "123456",
    }),
  });

  if (!res.ok) {
    alert("Falha no login");
    return;
  }

  const data = await res.json();
  token = data.access_token;
  connectWebSocket();
  loadConversations();
}

async function loadConversations() {
  const res = await fetch("http://localhost:8000/conversations", {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    alert("Erro ao carregar conversas: " + res.status);
    return;
  }

  const conversations = await res.json();
  const container = document.getElementById("conversations");
  container.innerHTML = "";

  conversations.forEach((conv) => {
    const btn = document.createElement("button");
    btn.textContent = `Cliente: ${conv.customer_number}`;
    btn.onclick = () => {
      selectedConversation = conv;
      document.getElementById("messages").innerHTML = "";
    };
    container.appendChild(btn);
  });
}

async function sendMessage() {
  const input = document.getElementById("messageInput");
  const text = input.value;
  if (!selectedConversation || !text) return;

  const res = await fetch(`http://localhost:8000/conversations/${selectedConversation.id}/reply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message: text }),
  });

  if (!res.ok) {
    alert("Erro ao enviar mensagem");
  } else {
    input.value = "";
  }
}
