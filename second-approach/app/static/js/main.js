let selectedChannelId = null;

document.addEventListener("DOMContentLoaded", () => {
  initChannelList();
  initChannelForm();
  initMessageForm();
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
  loadChannelMessages(channelId);
}

// ========== Channel Creation ==========

function initChannelForm() {
  const form = document.getElementById("channel-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.getElementById("channel-name").value.trim();
    const creatorId = document.getElementById("channel-creator-id").value;

    fetch("/api/channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        creator_id: parseInt(creatorId, 10),
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
          <p><strong>User ${msg.user_id}:</strong> ${msg.content}</p>
          <p><small>${msg.created_at}</small></p>
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
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!selectedChannelId) {
      showMessageError("Select a channel first.");
      return;
    }

    const userId = document.getElementById("message-user-id").value;
    const content = document.getElementById("message-content").value.trim();

    fetch(`/api/channels/${selectedChannelId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: parseInt(userId, 10),
        content,
      }),
    })
      .then(handleFetchErrors)
      .then(() => {
        showMessageError("");
        form.reset();
        loadChannelMessages(selectedChannelId);
      })
      .catch((err) => {
        showMessageError(err.message);
      });
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

