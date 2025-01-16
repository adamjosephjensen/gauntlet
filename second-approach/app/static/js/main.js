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
            
        const response = await fetch(url, { credentials: 'include' });
        if (response.status === 401) {
            window.location.href = '/api/auth/login';
            return;
        }
        const data = await handleFetchErrors(response);
        
        // Handle deleted channels
        if (data.deleted_channel_ids && data.deleted_channel_ids.length > 0) {
            data.deleted_channel_ids.forEach(channelId => {
                const channelEl = document.querySelector(`[data-channel-id="${channelId}"]`);
                if (channelEl) {
                    channelEl.remove();
                    // If this was the selected channel, clear the messages
                    if (selectedChannelId === channelId) {
                        selectedChannelId = null;
                        document.getElementById("channel-title").innerText = "Select a channel";
                        document.getElementById("message-list").innerHTML = "";
                        document.getElementById("message-form").style.display = "none";
                    }
                }
            });
        }
        
        // Handle new channels
        if (data.channels && data.channels.length > 0) {
            data.channels.forEach(channel => {
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
            
        const response = await fetch(url, { credentials: 'include' });
        if (response.status === 401) {
            window.location.href = '/api/auth/login';
            return;
        }
        const data = await handleFetchErrors(response);
        
        // Handle deleted messages
        if (data.deleted_message_ids && data.deleted_message_ids.length > 0) {
            data.deleted_message_ids.forEach(messageId => {
                const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
                if (messageEl) messageEl.remove();
            });
        }
        
        // Handle new messages
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
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
    msgDiv.setAttribute('data-message-id', msg.id);
    
    // Get current user info from a data attribute we'll add to the body
    const currentUserId = document.body.getAttribute('data-user-id');
    const isOwnMessage = currentUserId && parseInt(currentUserId) === msg.user_id;
    
    msgDiv.innerHTML = `
        <div class="message-content">
            <strong>${msg.user_email}:</strong> ${msg.content}
            ${isOwnMessage ? `<button class="delete-message-btn" aria-label="Delete message">×</button>` : ''}
        </div>
        <div class="message-timestamp">${formatTimestamp(msg.created_at)}</div>
    `;

    // Add delete button click handler if it's the user's message
    if (isOwnMessage) {
        const deleteBtn = msgDiv.querySelector('.delete-message-btn');
        deleteBtn.addEventListener('click', () => deleteMessage(msg.id));
    }

    messageListEl.appendChild(msgDiv);
    messageListEl.scrollTop = messageListEl.scrollHeight;
}

async function deleteMessage(messageId) {
    if (!selectedChannelId) return;

    try {
        const response = await fetch(`/api/channels/${selectedChannelId}/messages/${messageId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok) {
            // Remove the message from the UI
            const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
            if (messageEl) messageEl.remove();
        } else if (response.status === 401) {
            // Redirect to login if unauthorized
            window.location.href = '/login';
        } else {
            const data = await response.json();
            showMessageError(data.error || 'Failed to delete message');
        }
    } catch (error) {
        console.error('Error deleting message:', error);
        showMessageError('Failed to delete message');
    }
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
    
    // Get current user info from a data attribute we'll add to the body
    const currentUserId = document.body.getAttribute('data-user-id');
    const isCreator = currentUserId && parseInt(currentUserId) === channel.creator_id;
    
    // Create channel name span
    const channelName = document.createElement("span");
    channelName.innerText = channel.name || `Channel #${channel.id}`;
    channelName.style.flex = "1";
    channelDiv.appendChild(channelName);
    
    // Add delete button if user is the creator
    if (isCreator) {
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "delete-channel-btn";
        deleteBtn.setAttribute("aria-label", "Delete channel");
        deleteBtn.innerHTML = "×";
        deleteBtn.onclick = (e) => {
            e.stopPropagation(); // Prevent channel selection when clicking delete
            deleteChannel(channel.id);
        };
        channelDiv.appendChild(deleteBtn);
    }
    
    // Add click handler for channel selection
    channelName.addEventListener("click", () => {
        selectChannel(channel.id, channel.name);
    });
    
    channelListEl.appendChild(channelDiv);
}

async function deleteChannel(channelId) {
    try {
        const response = await fetch(`/api/channels/${channelId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok) {
            // Remove the channel from the UI
            const channelEl = document.querySelector(`[data-channel-id="${channelId}"]`);
            if (channelEl) {
                channelEl.remove();
                // If this was the selected channel, clear the messages
                if (selectedChannelId === channelId) {
                    selectedChannelId = null;
                    document.getElementById("channel-title").innerText = "Select a channel";
                    document.getElementById("message-list").innerHTML = "";
                    document.getElementById("message-form").style.display = "none";
                }
            }
        } else if (response.status === 401) {
            window.location.href = '/api/auth/login';
        } else {
            const data = await response.json();
            showChannelError(data.error || 'Failed to delete channel');
        }
    } catch (error) {
        console.error('Error deleting channel:', error);
        showChannelError('Failed to delete channel');
    }
}

function handleSignOut() {
    fetch('/api/auth/logout', { method: 'POST' })
        .then(response => {
            if (response.ok) {
                stopPolling();
                window.location.href = '/api/auth/login';
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
    fetch("/api/channels", { credentials: 'include' })
        .then(handleFetchErrors)
        .then((data) => {
            const channelListEl = document.getElementById("channel-list");
            channelListEl.innerHTML = "";
            if (data.channels) {
                data.channels.forEach((ch) => {
                    appendChannel(ch);
                    if (ch.created_at > (lastChannelTimestamp || '')) {
                        lastChannelTimestamp = ch.created_at;
                    }
                });
            }
        })
        .catch((err) => {
            if (err.status === 401) {
                window.location.href = '/api/auth/login';
            } else {
                showChannelError(err.message);
            }
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
    fetch(`/api/channels/${channelId}/messages`, { credentials: 'include' })
        .then(handleFetchErrors)
        .then((data) => {
            const messageListEl = document.getElementById("message-list");
            messageListEl.innerHTML = "";
            if (data.messages) {
                data.messages.forEach((msg) => {
                    appendMessage(msg);
                    if (msg.created_at > (lastMessageTimestamp || '')) {
                        lastMessageTimestamp = msg.created_at;
                    }
                });
            }
        })
        .catch((err) => {
            if (err.status === 401) {
                window.location.href = '/api/auth/login';
            } else {
                showMessageError(err.message);
            }
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
        credentials: 'include',
        body: JSON.stringify({
            content: content
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
            if (err.status === 401) {
                window.location.href = '/login';
            } else {
                showMessageError(err.message);
            }
        });
}

// ========== Error Handling ==========

function handleFetchErrors(response) {
    if (!response.ok) {
        return response.json().then((data) => {
            const error = new Error(data.error || `HTTP error ${response.status}`);
            error.status = response.status;
            throw error;
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

