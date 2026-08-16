/**
 * Captain Habitat Frontend Logic
 * Supports mobile browser dictation, Gboard text, SSE streaming, thread persistence,
 * live tool actions, and Heart operational learning.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const threadDrawer = document.getElementById('threadDrawer');
  const drawerBackdrop = document.getElementById('drawerBackdrop');
  const toggleDrawerBtn = document.getElementById('toggleDrawerBtn');
  const closeDrawerBtn = document.getElementById('closeDrawerBtn');
  const threadList = document.getElementById('threadList');
  const newThreadBtn = document.getElementById('newThreadBtn');
  const quickNewBtn = document.getElementById('quickNewBtn');
  const stopGenBtn = document.getElementById('stopGenBtn');

  const feedContainer = document.getElementById('feedContainer');
  const feedContent = document.getElementById('feedContent');
  const composerForm = document.getElementById('composerForm');
  const composerInput = document.getElementById('composerInput');
  const sendBtn = document.getElementById('sendBtn');
  const fileInput = document.getElementById('fileInput');
  const attachmentPreview = document.getElementById('attachmentPreview');
  const attachmentName = document.getElementById('attachmentName');
  const removeAttachmentBtn = document.getElementById('removeAttachmentBtn');

  const heartDialog = document.getElementById('heartDialog');
  const openHeartBtn = document.getElementById('openHeartBtn');
  const closeHeartBtn = document.getElementById('closeHeartBtn');
  const heartList = document.getElementById('heartList');
  const newHeartText = document.getElementById('newHeartText');
  const saveHeartBtn = document.getElementById('saveHeartBtn');

  // State
  let activeThreadId = localStorage.getItem('active_captain_thread_id') || null;
  let activeAttachment = null;
  let isGenerating = false;
  let autoScrollUserPaused = false;
  let currentEventSourceController = null;

  // --- DRAWER CONTROLS ---
  function openDrawer() {
    threadDrawer.classList.add('open');
    drawerBackdrop.classList.add('open');
  }

  function closeDrawer() {
    threadDrawer.classList.remove('open');
    drawerBackdrop.classList.remove('open');
  }

  toggleDrawerBtn.addEventListener('click', openDrawer);
  closeDrawerBtn.addEventListener('click', closeDrawer);
  drawerBackdrop.addEventListener('click', closeDrawer);

  // --- AUTO SCROLL MANAGEMENT ---
  feedContainer.addEventListener('scroll', () => {
    const distanceToBottom = feedContainer.scrollHeight - feedContainer.scrollTop - feedContainer.clientHeight;
    autoScrollUserPaused = distanceToBottom > 80;
  });

  function scrollToBottom() {
    if (!autoScrollUserPaused) {
      feedContainer.scrollTop = feedContainer.scrollHeight;
    }
  }

  // --- COMPOSER & DRAFT MANAGEMENT (Gboard Compatibility) ---
  composerInput.addEventListener('input', () => {
    // Auto expand textarea
    composerInput.style.height = 'auto';
    composerInput.style.height = Math.min(composerInput.scrollHeight, 140) + 'px';

    // Preserve draft in localStorage
    if (activeThreadId) {
      localStorage.setItem(`draft_${activeThreadId}`, composerInput.value);
    }
  });

  function restoreDraft() {
    if (activeThreadId) {
      const draft = localStorage.getItem(`draft_${activeThreadId}`) || '';
      composerInput.value = draft;
      composerInput.style.height = 'auto';
      if (draft) {
        composerInput.style.height = Math.min(composerInput.scrollHeight, 140) + 'px';
      }
    } else {
      composerInput.value = '';
    }
  }

  // File Upload Attachment
  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      attachmentName.innerText = `Uploading ${file.name}...`;
      attachmentPreview.style.display = 'flex';

      const resp = await fetch('/captain-api/upload', {
        method: 'POST',
        body: file
      });
      if (resp.ok) {
        const res = await resp.json();
        activeAttachment = { filename: res.filename, original_name: file.name, path: res.path };
        attachmentName.innerText = `📎 ${file.name}`;
      } else {
        alert('Upload failed');
        clearAttachment();
      }
    } catch (err) {
      console.error(err);
      clearAttachment();
    }
  });

  removeAttachmentBtn.addEventListener('click', clearAttachment);

  function clearAttachment() {
    activeAttachment = null;
    fileInput.value = '';
    attachmentPreview.style.display = 'none';
  }

  // --- THREAD MANAGEMENT API ---
  async function loadThreadsList() {
    try {
      const resp = await fetch('/captain-api/threads');
      if (!resp.ok) return;
      const data = await resp.json();
      renderThreadsList(data.threads || []);
      
      // Auto-select initial thread or create one if empty
      if (!activeThreadId && data.threads && data.threads.length > 0) {
        selectThread(data.threads[0].id);
      } else if (!activeThreadId) {
        createNewThread();
      } else {
        loadActiveThread();
      }
    } catch (err) {
      console.error(err);
    }
  }

  function renderThreadsList(threads) {
    if (threads.length === 0) {
      threadList.innerHTML = '<div class="list-empty">No conversations yet</div>';
      return;
    }

    threadList.innerHTML = '';
    threads.forEach(t => {
      const el = document.createElement('div');
      el.className = `thread-item ${t.id === activeThreadId ? 'active' : ''}`;
      
      const dateStr = new Date(t.updated_at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      
      el.innerHTML = `
        <div class="thread-info">
          <span class="thread-title-text">${t.title || 'Conversation'}</span>
          <span class="thread-meta">${dateStr} • ${t.message_count} msgs</span>
        </div>
        <button class="thread-del-btn" title="Delete thread" data-id="${t.id}">✕</button>
      `;

      el.addEventListener('click', (e) => {
        if (e.target.classList.contains('thread-del-btn')) {
          e.stopPropagation();
          deleteThread(t.id);
        } else {
          selectThread(t.id);
          closeDrawer();
        }
      });

      threadList.appendChild(el);
    });
  }

  async function createNewThread() {
    try {
      const resp = await fetch('/captain-api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Conversation' })
      });
      if (resp.ok) {
        const thread = await resp.json();
        selectThread(thread.id);
        loadThreadsList();
      }
    } catch (err) {
      console.error(err);
    }
  }

  function selectThread(threadId) {
    activeThreadId = threadId;
    localStorage.setItem('active_captain_thread_id', threadId);
    restoreDraft();
    loadActiveThread();
    loadThreadsList();
  }

  async function deleteThread(threadId) {
    if (!confirm('Delete this conversation thread?')) return;
    try {
      await fetch(`/captain-api/threads/${threadId}`, { method: 'DELETE' });
      if (activeThreadId === threadId) {
        activeThreadId = null;
        localStorage.removeItem('active_captain_thread_id');
      }
      loadThreadsList();
    } catch (err) {
      console.error(err);
    }
  }

  newThreadBtn.addEventListener('click', () => { createNewThread(); closeDrawer(); });
  quickNewBtn.addEventListener('click', () => { createNewThread(); });

  // --- RENDER THREAD MESSAGES ---
  async function loadActiveThread() {
    if (!activeThreadId) return;

    try {
      const resp = await fetch(`/captain-api/threads/${activeThreadId}`);
      if (!resp.ok) return;
      const thread = await resp.json();
      renderMessages(thread.messages || []);
    } catch (err) {
      console.error(err);
    }
  }

  function renderMessages(messages) {
    feedContent.innerHTML = '';
    if (messages.length === 0) {
      feedContent.innerHTML = `
        <div class="message-bubble captain">
          <span class="message-speaker">CAPTAIN HABITAT</span>
          <div class="message-body">Captain Habitat initialized and ready. Speak or type your intent to begin execution.</div>
        </div>
      `;
      return;
    }

    messages.forEach(msg => {
      appendMessageToFeed(msg);
    });
    scrollToBottom();
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks: ```lang ... ```
    escaped = escaped.replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/gi, (match, lang, code) => {
      return `<pre class="code-block"><code class="lang-${lang}">${code}</code></pre>`;
    });

    // Inline code: `code`
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Bold & Italic
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Images: ![alt](url)
    escaped = escaped.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="message-inline-image" style="max-width:100%; border-radius:8px; margin:0.5rem 0;" loading="lazy">');

    // Links: [text](url)
    escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:var(--teal-accent);">$1</a>');

    // Line breaks
    escaped = escaped.replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br>');
    return `<p>${escaped}</p>`;
  }

  function appendMessageToFeed(msg) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${msg.role}`;

    const speaker = document.createElement('span');
    speaker.className = 'message-speaker';
    speaker.innerText = msg.role === 'admiral' ? 'ADMIRAL' : (msg.role === 'engineering' ? 'ENGINEERING' : (msg.role === 'alert' ? 'ALERT' : 'CAPTAIN'));
    bubble.appendChild(speaker);

    // Render attachments if present
    if (msg.attachments && msg.attachments.length > 0) {
      msg.attachments.forEach(att => {
        const attEl = document.createElement('div');
        attEl.className = 'attachment-item-rendered';
        attEl.style.cssText = 'font-size:0.8rem; opacity:0.85; margin:0.3rem 0;';
        if (att.url && (att.filename && att.filename.match(/\.(png|jpg|jpeg|webp|gif)$/i))) {
          attEl.innerHTML = `<img src="${att.url}" alt="${att.original_name || att.filename}" style="max-width:100%; border-radius:6px; display:block; margin:4px 0;">`;
        } else {
          attEl.innerHTML = `📎 <a href="${att.url || '#'}" target="_blank" style="color:inherit; text-decoration:underline;">${att.original_name || att.filename}</a>`;
        }
        bubble.appendChild(attEl);
      });
    }

    // Render tool events if present
    if (msg.tool_events && msg.tool_events.length > 0) {
      msg.tool_events.forEach(t => {
        const toolBadge = document.createElement('div');
        toolBadge.className = 'tool-event-badge';
        toolBadge.innerHTML = `<span>⚙️</span> <span class="tool-event-summary">${t.summary || t.action || t.name}</span>`;
        bubble.appendChild(toolBadge);
      });
    }

    const body = document.createElement('div');
    body.className = 'message-body';
    body.innerHTML = formatMarkdown(msg.text);
    bubble.appendChild(body);

    feedContent.appendChild(bubble);
  }

  // --- TURN EXECUTION & SSE STREAMING ---
  composerForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const prompt = composerInput.value.trim();
    if (!prompt || isGenerating) return;

    sendTurnPrompt(prompt);
  });

  async function sendTurnPrompt(prompt) {
    if (!activeThreadId) {
      await createNewThread();
    }

    // Append Admiral message immediately to UI
    const admiralMsg = {
      role: 'admiral',
      text: prompt,
      attachments: activeAttachment ? [activeAttachment] : []
    };
    appendMessageToFeed(admiralMsg);

    // Clear composer
    composerInput.value = '';
    composerInput.style.height = 'auto';
    if (activeThreadId) localStorage.removeItem(`draft_${activeThreadId}`);
    clearAttachment();

    // Prepare Captain stream bubble
    const captainBubble = document.createElement('div');
    captainBubble.className = 'message-bubble captain';

    const speaker = document.createElement('span');
    speaker.className = 'message-speaker';
    speaker.innerText = 'CAPTAIN';

    const body = document.createElement('div');
    body.className = 'message-body';
    body.innerText = '...';

    captainBubble.appendChild(speaker);
    captainBubble.appendChild(body);
    feedContent.appendChild(captainBubble);

    scrollToBottom();
    setGenerating(true);

    let accumulatedText = '';

    // Initiate SSE Stream fetch
    try {
      const response = await fetch('/captain-api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: activeThreadId,
          prompt: prompt,
          attachments: admiralMsg.attachments
        })
      });

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep partial frame

        for (const lineBlock of lines) {
          const events = lineBlock.split('\n');
          let eventType = 'message';
          let eventData = '';

          for (const line of events) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6).trim();
            }
          }

          if (eventType === 'delta' && eventData) {
            try {
              const dataObj = JSON.parse(eventData);
              if (dataObj.content) {
                accumulatedText += dataObj.content;
                body.innerHTML = formatMarkdown(accumulatedText);
                scrollToBottom();
              }
            } catch (err) {}
          } else if (eventType === 'tool' && eventData) {
            try {
              const toolObj = JSON.parse(eventData);
              const toolBadge = document.createElement('div');
              toolBadge.className = 'tool-event-badge';
              toolBadge.innerHTML = `<span>⚙️</span> <span class="tool-event-summary">${toolObj.summary || toolObj.action}</span>`;
              captainBubble.insertBefore(toolBadge, body);
            } catch (err) {}
          } else if (eventType === 'done') {
            break;
          }
        }
      }

      if (!accumulatedText.trim()) {
        body.innerText = '(Turn completed)';
      }
    } catch (err) {
      console.error(err);
      body.innerText = `Error: ${err.message || 'Turn failed'}`;
    } finally {
      setGenerating(false);
      loadActiveThread();
      loadThreadsList();
    }
  }

  // Stop Generation Action
  stopGenBtn.addEventListener('click', async () => {
    if (!activeThreadId || !isGenerating) return;

    try {
      await fetch('/captain-api/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: activeThreadId })
      });
    } catch (err) {
      console.error(err);
    }
  });

  function setGenerating(generating) {
    isGenerating = generating;
    sendBtn.disabled = generating;
    stopGenBtn.style.display = generating ? 'inline-flex' : 'none';
  }

  // --- HEART LESSONS DIALOG ---
  openHeartBtn.addEventListener('click', () => {
    loadHeartLessons();
    heartDialog.showModal();
    closeDrawer();
  });

  closeHeartBtn.addEventListener('click', () => heartDialog.close());

  async function loadHeartLessons() {
    try {
      const resp = await fetch('/captain-api/heart');
      if (!resp.ok) return;
      const data = await resp.json();
      renderHeartLessons(data.lessons || []);
    } catch (err) {
      console.error(err);
    }
  }

  function renderHeartLessons(lessons) {
    if (lessons.length === 0) {
      heartList.innerHTML = '<div class="dialog-hint">No persisted Heart lessons yet.</div>';
      return;
    }

    heartList.innerHTML = '';
    lessons.forEach(h => {
      const el = document.createElement('div');
      el.className = 'heart-item';
      const dateStr = new Date(h.created_at * 1000).toLocaleDateString();
      el.innerHTML = `
        <strong>${h.lesson}</strong>
        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:4px;">Source: ${h.source} • ${dateStr}</div>
      `;
      heartList.appendChild(el);
    });
  }

  saveHeartBtn.addEventListener('click', async () => {
    const text = newHeartText.value.trim();
    if (!text) return;

    try {
      const resp = await fetch('/captain-api/heart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lesson: text, source: 'Admiral manual entry' })
      });
      if (resp.ok) {
        newHeartText.value = '';
        loadHeartLessons();
      }
    } catch (err) {
      console.error(err);
    }
  });

  // Polyfill string startsWith
  if (!String.prototype.startswith) {
    String.prototype.startswith = function(search, pos) {
      return this.substr(!pos || pos < 0 ? 0 : +pos, search.length) === search;
    };
  }

  // Initialize
  loadThreadsList();
});
