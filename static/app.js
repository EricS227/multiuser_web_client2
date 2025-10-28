let token = "";
let selectedConversation = null;
let ws = null;

function connectWebSocket() {
  ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Handle different message types
    if (data.type === "new_escalation") {
      handleNewEscalation(data);
    } else {
      // Regular message handling
      const msgDiv = document.createElement("div");
      msgDiv.textContent = `${data.sender}: ${data.message || data.content}`;
      document.getElementById("messages").appendChild(msgDiv);
    }
    
    // Auto-scroll messages
    const messagesContainer = document.getElementById("messages");
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  };
  
  ws.onopen = () => {
    console.log("WebSocket connected");
  };
  
  ws.onclose = () => {
    console.log("WebSocket disconnected, attempting to reconnect...");
    setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
  };
}

function handleNewEscalation(data) {
  // Show browser notification
  if (Notification.permission === "granted") {
    new Notification("Nova conversa escalada!", {
      body: `${data.customer_name}: ${data.message.substring(0, 50)}...`,
      icon: "/favicon.ico"
    });
  }
  
  // Play notification sound (optional)
  try {
    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmMeBjOR2e3Jdy0EJHfI8N2QQAoUXrPq66hVFApGnt/yvmMeBjOR2OzJdy0EJHfH8N2QQAoUXrPq66hVFApHn+DyvmMeBjOR2O3Jdy0EJHfH8N2QQAoUXbPq66hVFApGnt/yv2MeBjOR2OzJdy0EJHbH8N2QQAoUXbPp66hWFApGnt/yv2MeBjOR2OzJdywEJHbH8N2QQAoUXbPp66hWFApGnt/yv2MeBjOR2OzJdywEJHbH8N2QQAoUXbPp66hWFApGnt/yv2MeBjOR2OzJdywEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdywEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdywEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAoUXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkTXbPp66hWFAlGnt/yv2MeBjOR2OzJdiwEJHbH8N2QQAkT')
    audio.play();
  } catch (e) {
    // Ignore audio errors
  }
  
  // Update conversations list to show new conversation
  loadConversations();
  
  // Flash the browser tab title
  flashTitle("Nova Conversa!", 3000);
}

function flashTitle(message, duration) {
  const originalTitle = document.title;
  document.title = message;
  setTimeout(() => {
    document.title = originalTitle;
  }, duration);
}

async function login() {
  const res = await fetch("http://localhost:8000/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      username: "admin@test.com", // Using the default admin user
      password: "senha123",
    }),
  });

  if (!res.ok) {
    alert("Falha no login");
    return;
  }

  const data = await res.json();
  token = data.access_token;
  
  // Request notification permission
  if ("Notification" in window && Notification.permission === "default") {
    await Notification.requestPermission();
  }
  
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
