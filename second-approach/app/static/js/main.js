let selectedChannelId = null;
let socket = null;

function socketJoinChannel(channelId) {
  socket.emit("join_channel", { channel_id: channelId });
  console.log(`[CLIENT] Emitted join_channel for channel ${channelId}`);
}

function handleSignOut() {
  fetch('/api/auth/logout', { method: 'POST' })
    .then(response => {
      if (response.ok) {
        // Broadcast the logout event to other tabs
        socket.emit('user_logout');
        // Redirect to login page
        window.location.href = '/login';
      }
    })
    .catch(error => {
      console.error('Error signing out:', error);
    });
}

document.addEventListener("DOMContentLoaded", () => {
  initChannelList();
  initChannelForm();
  initMessageForm();

  // Initialize sign out button
  const signOutBtn = document.getElementById('sign-out-btn');
  if (signOutBtn) {
    signOutBtn.addEventListener('click', handleSignOut);
  }

  socket = io({
    reconnection: true,
    reconnectionDelay: 2000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5
  });

  socket.on('connect', () => {
      console.log("Socket connected:", socket.id);
      // Rejoin current channel if any
      if (selectedChannelId) {
        socketJoinChannel(selectedChannelId);
      }
  });
  
  socket.on("error", (data) => {
    console.log("[CLIENT] Socket error:", data);
    showChannelError(data.message);
    // Reset channel selection on error
    selectedChannelId = null;
    document.getElementById("message-form").style.display = "none";
  });

  socket.on("joined_channel_ok", (data) => {
    console.log("[CLIENT] Successfully joined channel:", data);
    // Only show message form after successfully joining
    document.getElementById("message-form").style.display = "block";
  });
  
  socket.on("user_joined", (data) => {
    console.log("[CLIENT] user_joined event:", data);
  });

  // Handle logout events from other tabs
  socket.on("logout_broadcast", () => {
    console.log("[CLIENT] Received logout broadcast, redirecting to login");
    window.location.href = '/login';
  });

  socket.on("new_message", (msg) => {
    console.log("[CLIENT] new_message received:", msg);
    
    // Only update if we're in the correct channel
    if (selectedChannelId === msg.channel_id) {
      const messageListEl = document.getElementById("message-list");
      const msgDiv = document.createElement("div");
      msgDiv.className = "message-item";
      msgDiv.innerHTML = `
        <div class="message-content">
          <strong>User ${msg.user_id}:</strong> ${msg.content}
        </div>
        <div class="message-timestamp">${formatTimestamp(msg.created_at)}</div>
      `;
      messageListEl.appendChild(msgDiv);
      
      // Auto-scroll to the bottom of the message list
      messageListEl.scrollTop = messageListEl.scrollHeight;
    }
  });

  socket.on("new_channel", (channel) => {
    console.log("[CLIENT] new_channel received:", channel);
    
    // Add the new channel to the channel list
    const channelListEl = document.getElementById("channel-list");
    const channelDiv = document.createElement("div");
    channelDiv.className = "channel-item";
    channelDiv.setAttribute("data-channel-id", channel.id);
    channelDiv.addEventListener("click", () => {
      selectChannel(channel.id, channel.name);
    });
    channelDiv.innerText = channel.name || `Channel #${channel.id}`;
    channelListEl.appendChild(channelDiv);
  });

  socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    handleConnectionError();
  });
});

// ========== Channel List ==========

function initChannelList() {
  fetch("/api/channels")
    .then(handleFetchErrors)
    .then((channels) => {
      const channelListEl = document.getElementById("channel-list");
      channelListEl.innerHTML = "";
      channels.forEach((ch) => {
        const channelDiv = document.createElement("div");
        channelDiv.className = "channel-item";
        channelDiv.innerText = ch.name || `Channel #${ch.id}`;
        channelDiv.addEventListener("click", () => {
          selectChannel(ch.id, ch.name);
        });
        channelListEl.appendChild(channelDiv);
      });
    })
    .catch((err) => {
      showChannelError(err.message);
    });
}

function selectChannel(channelId, channelName) {
  selectedChannelId = channelId;
  document.getElementById("channel-title").innerText =
    channelName ? `Channel: ${channelName}` : `Channel ID: ${channelId}`;
  document.getElementById("message-form").style.display = "block";
  
  // First join the channel's socket room
  socketJoinChannel(channelId);
  // Then load messages
  loadChannelMessages(channelId);
}

// ========== Channel Creation ==========

function initChannelForm() {
  const form = document.getElementById("channel-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.getElementById("channel-name").value.trim();

    fetch("/api/channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        is_dm: false,
      }),
    })
      .then(handleFetchErrors)
      .then(() => {
        showChannelError("");
        form.reset();
        initChannelList();
      })
      .catch((err) => {
        showChannelError(err.message);
      });
  });
}

// ========== Message List ==========

function loadChannelMessages(channelId) {
  fetch(`/api/channels/${channelId}/messages`)
    .then(handleFetchErrors)
    .then((messages) => {
      const messageListEl = document.getElementById("message-list");
      messageListEl.innerHTML = "";
      messages.forEach((msg) => {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message-item";
        msgDiv.innerHTML = `
          <div class="message-content">
            <strong>User ${msg.user_id}:</strong> ${msg.content}
          </div>
          <div class="message-timestamp">${formatTimestamp(msg.created_at)}</div>
        `;
        messageListEl.appendChild(msgDiv);
      });
    })
    .catch((err) => {
      showMessageError(err.message);
    });
}

// ========== Post Message Form ==========

function initMessageForm() {
  const form = document.getElementById("message-form");
  const messageInput = document.getElementById("message-content");

  // Handle keydown events for Return and Shift+Return
  messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      // Shift+Return: Insert newline
      if (event.shiftKey) {
        return; // Let the default behavior handle newline insertion
      }
      
      // Return: Send message
      event.preventDefault();
      const content = messageInput.value.trim();
      
      // Don't send empty messages
      if (!content) {
        return;
      }

      socket.emit('send_message', {
        channel_id: selectedChannelId,
        content: content
      });
      console.log('[CLIENT] Emitted send_message:', content);

      // Clear the form and any error message
      showMessageError("");
      form.reset();
    }
  });

  // Keep the regular form submit handler as fallback for the Send button
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!selectedChannelId) {
      showMessageError("Select a channel first.");
      return;
    }

    const content = messageInput.value.trim();

    if (!content) {
      return;
    }

    socket.emit('send_message', {
      channel_id: selectedChannelId,
      content: content
    });
    console.log('[CLIENT] Emitted send_message:', content);

    showMessageError("");
    form.reset();
  });
}

// ========== Error Handling ==========

function handleFetchErrors(response) {
  if (!response.ok) {
    return response.json().then((data) => {
      throw new Error(data.message || `HTTP error ${response.status}`);
    });
  }
  return response.json();
}

function showChannelError(msg) {
  document.getElementById("channel-error").innerText = msg;
}

function showMessageError(msg) {
  document.getElementById("message-error").innerText = msg;
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

