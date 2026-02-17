(function() {
  'use strict';

  var API_URL = window.RIZALTA_CHAT_API || 'https://eva-dev.rizaltaservice.ru';
  var AUTO_OPEN_DELAY = 30000;
  var REQUEST_TIMEOUT = 120000;

  var btn = document.getElementById('rzChatBtn');
  var win = document.getElementById('rzChatWindow');
  var msgs = document.getElementById('rzMessages');
  var input = document.getElementById('rzInput');
  var sendBtn = document.getElementById('rzSendBtn');
  var typing = document.getElementById('rzTyping');
  var quickReplies = document.getElementById('rzQuickReplies');

  var isOpen = false;
  var sessionId = localStorage.getItem('rz_session_id') || null;
  var isSending = false;
  var sessionPromise = null;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function saveLocalHistory(messages) {
    try { sessionStorage.setItem('rz_messages', JSON.stringify(messages)); } catch(e) {}
  }

  function loadLocalHistory() {
    try { return JSON.parse(sessionStorage.getItem('rz_messages')) || []; } catch(e) { return []; }
  }

  function addMessage(text, role) {
    var div = document.createElement('div');
    div.className = 'rz-msg ' + role;
    if (role === 'bot') {
      div.innerHTML = '<span class="rz-msg-avatar">\u041C</span>' + escapeHtml(text);
    } else {
      div.textContent = text;
    }
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    var history = loadLocalHistory();
    history.push({ role: role, text: text });
    saveLocalHistory(history);
    return div;
  }

  function createBotBubble() {
    var div = document.createElement('div');
    div.className = 'rz-msg bot';
    div.innerHTML = '<span class="rz-msg-avatar">\u041C</span>';
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function appendToBubble(bubble, token) {
    var textNode = bubble.lastChild;
    if (!textNode || textNode.nodeType !== 3) {
      textNode = document.createTextNode('');
      bubble.appendChild(textNode);
    }
    textNode.textContent += token;
    msgs.scrollTop = msgs.scrollHeight;
  }

  function finalizeBubble(bubble) {
    var text = '';
    for (var i = 0; i < bubble.childNodes.length; i++) {
      if (bubble.childNodes[i].nodeType === 3) text += bubble.childNodes[i].textContent;
    }
    text = text.trim();
    if (text) {
      var history = loadLocalHistory();
      history.push({ role: 'bot', text: text });
      saveLocalHistory(history);
    }
  }

  function showQuickReplies(replies) {
    quickReplies.innerHTML = '';
    if (!replies || !replies.length) return;
    replies.forEach(function(t) {
      var b = document.createElement('button');
      b.className = 'rz-quick-btn';
      b.textContent = t;
      b.addEventListener('click', function() {
        quickReplies.innerHTML = '';
        sendMessage(t);
      });
      quickReplies.appendChild(b);
    });
  }

  function showTyping() { typing.classList.add('show'); msgs.scrollTop = msgs.scrollHeight; }
  function hideTyping() { typing.classList.remove('show'); }

  // ── Session (single promise, no duplicates) ──

  function ensureSession() {
    if (sessionId) return Promise.resolve(sessionId);
    if (sessionPromise) return sessionPromise;

    sessionPromise = fetch(API_URL + '/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page_url: window.location.href })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      sessionId = data.session_id;
      localStorage.setItem('rz_session_id', sessionId);
      addMessage(data.greeting, 'bot');
      showQuickReplies(['\u0420\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u0442\u044C \u0434\u043E\u0445\u043E\u0434', '\u041F\u043E\u0434\u043E\u0431\u0440\u0430\u0442\u044C \u0430\u043F\u0430\u0440\u0442\u0430\u043C\u0435\u043D\u0442\u044B', '\u0421\u0440\u0430\u0432\u043D\u0438\u0442\u044C \u0441 \u0434\u0435\u043F\u043E\u0437\u0438\u0442\u043E\u043C']);
      sessionPromise = null;
      return sessionId;
    })
    .catch(function(e) {
      sessionPromise = null;
      throw e;
    });

    return sessionPromise;
  }

  function resumeSession() {
    return fetch(API_URL + '/api/session/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: '' })
    })
    .then(function(r) {
      if (r.status === 404) {
        sessionId = null;
        localStorage.removeItem('rz_session_id');
        return ensureSession();
      }
      return r.json();
    })
    .then(function(data) {
      if (data && data.history) {
        var localHistory = [];
        data.history.forEach(function(m) {
          var role = m.role === 'assistant' ? 'bot' : 'user';
          var div = document.createElement('div');
          div.className = 'rz-msg ' + role;
          if (role === 'bot') {
            div.innerHTML = '<span class="rz-msg-avatar">\u041C</span>' + escapeHtml(m.content);
          } else {
            div.textContent = m.content;
          }
          msgs.appendChild(div);
          localHistory.push({ role: role, text: m.content });
        });
        saveLocalHistory(localHistory);
        msgs.scrollTop = msgs.scrollHeight;
      }
    });
  }

  // ── Send ──

  function sendMessage(text) {
    if (!text.trim() || isSending) return;
    isSending = true;
    input.value = '';
    sendBtn.disabled = true;
    quickReplies.innerHTML = '';
    addMessage(text, 'user');
    showTyping();

    ensureSession().then(function() {
      sendSSE(text);
    }).catch(function() {
      hideTyping();
      isSending = false;
      sendBtn.disabled = false;
      addMessage('\u0418\u0437\u0432\u0438\u043D\u0438\u0442\u0435, \u0441\u0432\u044F\u0437\u044C \u043F\u043E\u0434\u0432\u0438\u0441\u043B\u0430. \u041F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0451 \u0440\u0430\u0437.', 'bot');
    });
  }

  function sendSSE(text) {
    var controller = new AbortController();
    var timeout = setTimeout(function() { controller.abort(); }, REQUEST_TIMEOUT);
    var bubble = null;
    var gotTokens = false;
    var streamDone = false;

    fetch(API_URL + '/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
      signal: controller.signal
    })
    .then(function(response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      function processLine(line) {
        line = line.trim();
        if (line.indexOf('data: ') !== 0) return;
        try {
          var data = JSON.parse(line.substring(6));
          if (data.type === 'token') {
            if (!gotTokens) { hideTyping(); bubble = createBotBubble(); gotTokens = true; }
            appendToBubble(bubble, data.token);
          } else if (data.type === 'done') {
            streamDone = true;
          } else if (data.type === 'error') {
            if (!gotTokens) { hideTyping(); addMessage('\u041F\u0440\u043E\u0441\u0442\u0438\u0442\u0435, \u0441\u0432\u044F\u0437\u044C \u043F\u043E\u0434\u0432\u0438\u0441\u043B\u0430. \u041D\u0430\u043F\u0438\u0448\u0438\u0442\u0435 \u0435\u0449\u0451 \u0440\u0430\u0437?', 'bot'); }
            streamDone = true;
          }
        } catch(e) {}
      }

      function pump() {
        return reader.read().then(function(result) {
          if (result.done) {
            if (buffer.trim()) processLine(buffer);
            finish();
            return;
          }
          buffer += decoder.decode(result.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop();
          for (var i = 0; i < lines.length; i++) processLine(lines[i]);
          if (streamDone) { finish(); return; }
          return pump();
        });
      }

      function finish() {
        clearTimeout(timeout);
        if (bubble) finalizeBubble(bubble);
        if (!gotTokens) hideTyping();
        isSending = false;
        sendBtn.disabled = false;
      }

      return pump();
    })
    .catch(function(err) {
      clearTimeout(timeout);
      hideTyping();
      isSending = false;
      sendBtn.disabled = false;
      if (err.name === 'AbortError') {
        addMessage('\u0421\u0435\u0440\u0432\u0435\u0440 \u043D\u0435 \u043E\u0442\u0432\u0435\u0447\u0430\u0435\u0442, \u043F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u043F\u043E\u0437\u0436\u0435.', 'bot');
      } else {
        sendFallback(text);
      }
    });
  }

  function sendFallback(text) {
    isSending = true;
    sendBtn.disabled = true;
    showTyping();
    fetch(API_URL + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      hideTyping(); isSending = false; sendBtn.disabled = false;
      if (data.session_id) { sessionId = data.session_id; localStorage.setItem('rz_session_id', sessionId); }
      addMessage(data.reply, 'bot');
    })
    .catch(function() {
      hideTyping(); isSending = false; sendBtn.disabled = false;
      addMessage('\u0418\u0437\u0432\u0438\u043D\u0438\u0442\u0435, \u0441\u0432\u044F\u0437\u044C \u043F\u043E\u0434\u0432\u0438\u0441\u043B\u0430. \u041F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0451 \u0440\u0430\u0437.', 'bot');
    });
  }

  // ── Toggle ──

  function toggle() {
    isOpen = !isOpen;
    if (isOpen) {
      win.classList.add('open');
      btn.classList.add('active');
      btn.style.animation = 'none';
      input.focus();
      localStorage.setItem('rz_chat_opened', '1');
      if (!sessionId && loadLocalHistory().length === 0) ensureSession();
    } else {
      win.classList.remove('open');
      btn.classList.remove('active');
    }
  }

  // ── Events ──
  btn.addEventListener('click', toggle);
  sendBtn.addEventListener('click', function() { sendMessage(input.value); });
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });

  // ── Init ──
  var localHistory = loadLocalHistory();
  if (localHistory.length > 0) {
    localHistory.forEach(function(m) {
      var div = document.createElement('div');
      div.className = 'rz-msg ' + m.role;
      if (m.role === 'bot') {
        div.innerHTML = '<span class="rz-msg-avatar">\u041C</span>' + escapeHtml(m.text);
      } else {
        div.textContent = m.text;
      }
      msgs.appendChild(div);
    });
    msgs.scrollTop = msgs.scrollHeight;
  }

  if (sessionId && localHistory.length === 0) resumeSession();

  if (!localStorage.getItem('rz_chat_opened')) {
    setTimeout(function() { if (!isOpen) toggle(); }, AUTO_OPEN_DELAY);
  }

})();
