let selectedChannelId = null;
let lastChannelTimestamp = null;
let lastMessageTimestamp = null;
let channelPollInterval = null;
let messagePollInterval = null;

const POLL_INTERVAL = 2000; // Poll every 2 seconds

function startPolling() {
    // Stop any existing polling
    stopPolling();
    
    // Start polling for new channels
    channelPollInterval = setInterval(pollNewChannels, POLL_INTERVAL);
    
    // If a channel is selected, start polling for new messages
    if (selectedChannelId) {
        messagePollInterval = setInterval(() => pollNewMessages(selectedChannelId), POLL_INTERVAL);
    }
}

function stopPolling() {
    if (channelPollInterval) clearInterval(channelPollInterval);
    if (messagePollInterval) clearInterval(messagePollInterval);
    channelPollInterval = null;
    messagePollInterval = null;
}

async function pollNewChannels() {
    try {
        const url = lastChannelTimestamp 
            ? `/api/channels?after=${encodeURIComponent(lastChannelTimestamp)}`
            : '/api/channels';
            
        const response = await fetch(url);
        const channels = await handleFetchErrors(response);
        
        if (channels.length > 0) {
            channels.forEach(channel => {
                appendChannel(channel);
                lastChannelTimestamp = channel.created_at;
            });
        }
    } catch (error) {
        console.error('Error polling channels:', error);
    }
}

async function pollNewMessages(channelId) {
    try {
        const url = lastMessageTimestamp 
            ? `/api/channels/${channelId}/messages?after=${encodeURIComponent(lastMessageTimestamp)}`
            : `/api/channels/${channelId}/messages`;
            
        const response = await fetch(url);
        const messages = await handleFetchErrors(response);
        
        if (messages.length > 0) {
            messages.forEach(msg => {
                appendMessage(msg);
                lastMessageTimestamp = msg.created_at;
            });
        }
    } catch (error) {
        console.error('Error polling messages:', error);
    }
}

function appendMessage(msg) {
    const messageListEl = document.getElementById("message-list");
    const msgDiv = document.createElement("div");
    msgDiv.className = "message-item";
    msgDiv.innerHTML = `
        <div class="message-content">
            <strong>${msg.user_email}:</strong> ${msg.content}
        </div>
        <div class="message-timestamp">${formatTimestamp(msg.created_at)}</div>
    `;
    messageListEl.appendChild(msgDiv);
    messageListEl.scrollTop = messageListEl.scrollHeight;
}

function appendChannel(channel) {
    const channelListEl = document.getElementById("channel-list");
    // Check if channel already exists
    if (document.querySelector(`[data-channel-id="${channel.id}"]`)) {
        return;
    }
    const channelDiv = document.createElement("div");
    channelDiv.className = "channel-item";
    channelDiv.setAttribute("data-channel-id", channel.id);
    channelDiv.addEventListener("click", () => {
        selectChannel(channel.id, channel.name);
    });
    channelDiv.innerText = channel.name || `Channel #${channel.id}`;
    channelListEl.appendChild(channelDiv);
}

function handleSignOut() {
    fetch('/api/auth/logout', { method: 'POST' })
        .then(response => {
            if (response.ok) {
                stopPolling();
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
    startPolling();

    // Initialize sign out button
    const signOutBtn = document.getElementById('sign-out-btn');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', handleSignOut);
    }
});

// ========== Channel List ==========

function initChannelList() {
    fetch("/api/channels")
        .then(handleFetchErrors)
        .then((channels) => {
            const channelListEl = document.getElementById("channel-list");
            channelListEl.innerHTML = "";
            channels.forEach((ch) => {
                appendChannel(ch);
                if (ch.created_at > (lastChannelTimestamp || '')) {
                    lastChannelTimestamp = ch.created_at;
                }
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
    
    // Reset message timestamp when switching channels
    lastMessageTimestamp = null;
    
    // Restart polling with new channel
    stopPolling();
    startPolling();
    
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
            .then((response) => {
                showChannelError("");
                form.reset();
                if (response.data) {
                    appendChannel(response.data);
                    lastChannelTimestamp = response.data.created_at;
                }
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
                appendMessage(msg);
                if (msg.created_at > (lastMessageTimestamp || '')) {
                    lastMessageTimestamp = msg.created_at;
                }
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
            sendMessage(messageInput.value.trim());
        }
    });

    // Keep the regular form submit handler as fallback for the Send button
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        sendMessage(messageInput.value.trim());
    });
}

function sendMessage(content) {
    if (!selectedChannelId) {
        showMessageError("Select a channel first.");
        return;
    }

    if (!content) {
        return;
    }

    fetch(`/api/channels/${selectedChannelId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            content: content,
            user_id: 1 // TODO: Get from current user
        }),
    })
        .then(handleFetchErrors)
        .then((response) => {
            if (response.data) {
                appendMessage(response.data);
                lastMessageTimestamp = response.data.created_at;
            }
            document.getElementById("message-form").reset();
            showMessageError("");
        })
        .catch((err) => {
            showMessageError(err.message);
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

