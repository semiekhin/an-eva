/**
 * RIZALTA Chat Widget — АН Эва v1.1
 * Embeddable script: подключается одной строкой на любой сайт.
 * <script src="https://eva-dev.rizaltaservice.ru/widget/chat-widget.js"></script>
 *
 * Экспортирует window.openBot() для кнопок на лендинге.
 */
(function() {
  'use strict';

  // ── Config ──
  var API_URL = window.RIZALTA_CHAT_API || 'https://eva-dev.rizaltaservice.ru';
  var AUTO_OPEN_DELAY = 30000;
  var REQUEST_TIMEOUT = 120000;
  var WIDGET_ID = 'rizalta-chat-widget';

  // Prevent double init
  if (document.getElementById(WIDGET_ID)) return;

  // ── Inject CSS ──
  var style = document.createElement('style');
  style.textContent = [
    "@import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600&display=swap');",

    '#' + WIDGET_ID + ' {',
    '  font-family: "Raleway", sans-serif;',
    '  position: fixed;',
    '  bottom: 24px;',
    '  right: 24px;',
    '  z-index: 99999;',
    '  line-height: 1.5;',
    '}',

    // ── Button ──
    '#' + WIDGET_ID + ' .rz-chat-btn {',
    '  width: 64px;',
    '  height: 64px;',
    '  border-radius: 50%;',
    '  background: linear-gradient(135deg, #c9a54a, #b8943f);',
    '  border: none;',
    '  cursor: pointer;',
    '  display: flex;',
    '  align-items: center;',
    '  justify-content: center;',
    '  box-shadow: 0 4px 20px rgba(201,165,74,0.4);',
    '  transition: transform 0.3s, box-shadow 0.3s;',
    '  animation: rz-pulse 2s ease-in-out infinite;',
    '  position: relative;',
    '}',
    '#' + WIDGET_ID + ' .rz-chat-btn:hover {',
    '  transform: scale(1.08);',
    '  box-shadow: 0 6px 30px rgba(201,165,74,0.6);',
    '}',
    '#' + WIDGET_ID + ' .rz-chat-btn svg { width: 28px; height: 28px; fill: #060b06; }',
    '#' + WIDGET_ID + ' .rz-chat-btn.active .icon-chat { display: none; }',
    '#' + WIDGET_ID + ' .rz-chat-btn:not(.active) .icon-close { display: none; }',

    '@keyframes rz-pulse {',
    '  0%, 100% { box-shadow: 0 4px 20px rgba(201,165,74,0.4); }',
    '  50% { box-shadow: 0 4px 30px rgba(201,165,74,0.7); }',
    '}',

    // ── Window ──
    '#' + WIDGET_ID + ' .rz-chat-window {',
    '  display: none;',
    '  position: fixed;',
    '  bottom: 100px;',
    '  right: 24px;',
    '  width: 400px;',
    '  height: 550px;',
    '  background: #060b06;',
    '  border: 1px solid rgba(201,165,74,0.2);',
    '  border-radius: 16px;',
    '  box-shadow: 0 16px 60px rgba(0,0,0,0.6);',
    '  flex-direction: column;',
    '  overflow: hidden;',
    '}',
    '#' + WIDGET_ID + ' .rz-chat-window.open {',
    '  display: flex;',
    '  animation: rz-slide-up 0.3s ease-out;',
    '}',
    '@keyframes rz-slide-up {',
    '  from { opacity: 0; transform: translateY(20px); }',
    '  to { opacity: 1; transform: translateY(0); }',
    '}',

    // ── Header ──
    '#' + WIDGET_ID + ' .rz-header {',
    '  padding: 16px 20px;',
    '  background: #0f1a0f;',
    '  border-bottom: 1px solid rgba(201,165,74,0.2);',
    '  display: flex;',
    '  align-items: center;',
    '  gap: 12px;',
    '  flex-shrink: 0;',
    '}',
    '#' + WIDGET_ID + ' .rz-avatar {',
    '  width: 40px;',
    '  height: 40px;',
    '  border-radius: 50%;',
    '  background: linear-gradient(135deg, #c9a54a, #b8943f);',
    '  display: flex;',
    '  align-items: center;',
    '  justify-content: center;',
    '  font-weight: 600;',
    '  font-size: 18px;',
    '  color: #060b06;',
    '  flex-shrink: 0;',
    '}',
    '#' + WIDGET_ID + ' .rz-header-info h3 {',
    '  font-size: 14px; font-weight: 600; color: #f2ede5; margin: 0;',
    '}',
    '#' + WIDGET_ID + ' .rz-header-info p {',
    '  font-size: 12px; color: #c9a54a; font-weight: 400; margin: 0;',
    '}',

    // ── Messages ──
    '#' + WIDGET_ID + ' .rz-messages {',
    '  flex: 1;',
    '  overflow-y: auto;',
    '  padding: 16px;',
    '  display: flex;',
    '  flex-direction: column;',
    '  gap: 12px;',
    '}',
    '#' + WIDGET_ID + ' .rz-messages::-webkit-scrollbar { width: 4px; }',
    '#' + WIDGET_ID + ' .rz-messages::-webkit-scrollbar-track { background: transparent; }',
    '#' + WIDGET_ID + ' .rz-messages::-webkit-scrollbar-thumb { background: rgba(201,165,74,0.2); border-radius: 2px; }',

    '#' + WIDGET_ID + ' .rz-msg {',
    '  max-width: 82%;',
    '  padding: 10px 14px;',
    '  border-radius: 12px;',
    '  font-size: 14px;',
    '  line-height: 1.5;',
    '  color: #f2ede5;',
    '  word-wrap: break-word;',
    '}',
    '#' + WIDGET_ID + ' .rz-msg.bot {',
    '  align-self: flex-start;',
    '  background: #0f1a0f;',
    '  border: 1px solid rgba(201,165,74,0.2);',
    '  border-bottom-left-radius: 4px;',
    '}',
    '#' + WIDGET_ID + ' .rz-msg.user {',
    '  align-self: flex-end;',
    '  background: linear-gradient(135deg, #c9a54a, #b8943f);',
    '  color: #060b06;',
    '  font-weight: 500;',
    '  border-bottom-right-radius: 4px;',
    '}',
    '#' + WIDGET_ID + ' .rz-msg .rz-msg-avatar {',
    '  display: inline-block;',
    '  width: 24px; height: 24px;',
    '  border-radius: 50%;',
    '  background: linear-gradient(135deg, #c9a54a, #b8943f);',
    '  text-align: center;',
    '  line-height: 24px;',
    '  font-size: 11px; font-weight: 600;',
    '  color: #060b06;',
    '  margin-right: 6px;',
    '  vertical-align: middle;',
    '}',

    // ── Typing ──
    '#' + WIDGET_ID + ' .rz-typing {',
    '  display: none;',
    '  align-self: flex-start;',
    '  padding: 10px 14px;',
    '  background: #0f1a0f;',
    '  border: 1px solid rgba(201,165,74,0.2);',
    '  border-radius: 12px;',
    '  border-bottom-left-radius: 4px;',
    '  font-size: 13px;',
    '  color: rgba(242,237,229,0.6);',
    '  margin: 0 16px;',
    '}',
    '#' + WIDGET_ID + ' .rz-typing.show { display: block; }',
    '#' + WIDGET_ID + ' .rz-typing span { display: inline-block; animation: rz-dot 1.4s infinite; }',
    '#' + WIDGET_ID + ' .rz-typing span:nth-child(2) { animation-delay: 0.2s; }',
    '#' + WIDGET_ID + ' .rz-typing span:nth-child(3) { animation-delay: 0.4s; }',
    '@keyframes rz-dot {',
    '  0%, 60%, 100% { opacity: 0.3; }',
    '  30% { opacity: 1; }',
    '}',

    // ── Quick replies ──
    '#' + WIDGET_ID + ' .rz-quick-replies {',
    '  display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 8px;',
    '}',
    '#' + WIDGET_ID + ' .rz-quick-btn {',
    '  padding: 8px 14px;',
    '  border: 1px solid #c9a54a;',
    '  border-radius: 20px;',
    '  background: transparent;',
    '  color: #c9a54a;',
    '  font-family: "Raleway", sans-serif;',
    '  font-size: 13px; font-weight: 500;',
    '  cursor: pointer;',
    '  transition: all 0.2s;',
    '}',
    '#' + WIDGET_ID + ' .rz-quick-btn:hover { background: rgba(201,165,74,0.15); }',
    '#' + WIDGET_ID + ' .rz-contact-btn {',
    '  padding: 10px 16px;',
    '  border: none;',
    '  border-radius: 20px;',
    '  background: linear-gradient(135deg, #c9a54a, #b8943f);',
    '  color: #060b06;',
    '  font-family: "Raleway", sans-serif;',
    '  font-size: 13px; font-weight: 600;',
    '  cursor: pointer;',
    '  transition: all 0.2s;',
    '  white-space: nowrap;',
    '}',
    '#' + WIDGET_ID + ' .rz-contact-btn:hover { transform: scale(1.03); box-shadow: 0 2px 12px rgba(201,165,74,0.4); }',

    // ── Input ──
    '#' + WIDGET_ID + ' .rz-input-area {',
    '  padding: 12px 16px;',
    '  border-top: 1px solid rgba(201,165,74,0.2);',
    '  display: flex; gap: 8px;',
    '  background: #0f1a0f;',
    '  flex-shrink: 0;',
    '}',
    '#' + WIDGET_ID + ' .rz-input {',
    '  flex: 1;',
    '  padding: 10px 14px;',
    '  border: 1px solid rgba(201,165,74,0.2);',
    '  border-radius: 24px;',
    '  background: #060b06;',
    '  color: #f2ede5;',
    '  font-family: "Raleway", sans-serif;',
    '  font-size: 14px;',
    '  outline: none;',
    '  transition: border-color 0.2s;',
    '}',
    '#' + WIDGET_ID + ' .rz-input::placeholder { color: rgba(242,237,229,0.6); }',
    '#' + WIDGET_ID + ' .rz-input:focus { border-color: #c9a54a; }',
    '#' + WIDGET_ID + ' .rz-send-btn {',
    '  width: 42px; height: 42px;',
    '  border-radius: 50%; border: none;',
    '  background: linear-gradient(135deg, #c9a54a, #b8943f);',
    '  cursor: pointer;',
    '  display: flex; align-items: center; justify-content: center;',
    '  transition: transform 0.2s;',
    '  flex-shrink: 0;',
    '}',
    '#' + WIDGET_ID + ' .rz-send-btn:hover { transform: scale(1.05); }',
    '#' + WIDGET_ID + ' .rz-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }',
    '#' + WIDGET_ID + ' .rz-send-btn svg { width: 18px; height: 18px; fill: #060b06; }',

    // ── Mobile ──
    '@media (max-width: 480px) {',
    '  #' + WIDGET_ID + ' .rz-chat-window {',
    '    bottom: 0; right: 0; left: 0;',
    '    width: 100%; height: 100%;',
    '    border-radius: 0; border: none;',
    '  }',
    '  #' + WIDGET_ID + ' .rz-chat-btn {',
    '    width: 56px; height: 56px;',
    '  }',
    '  #' + WIDGET_ID + ' .rz-chat-btn svg { width: 24px; height: 24px; }',
    '}'
  ].join('\n');
  document.head.appendChild(style);

  // ── Inject HTML ──
  var container = document.createElement('div');
  container.id = WIDGET_ID;
  container.innerHTML = [
    '<button class="rz-chat-btn" id="rzChatBtn" aria-label="\u041E\u0442\u043A\u0440\u044B\u0442\u044C \u0447\u0430\u0442">',
    '  <svg class="icon-chat" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>',
    '  <svg class="icon-close" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
    '</button>',
    '<div class="rz-chat-window" id="rzChatWindow">',
    '  <div class="rz-header">',
    '    <div class="rz-avatar">\u041C</div>',
    '    <div class="rz-header-info">',
    '      <h3>\u041C\u0430\u0440\u0433\u043E</h3>',
    '      <p>\u041A\u043E\u043D\u0441\u0443\u043B\u044C\u0442\u0430\u043D\u0442 RIZALTA Resort</p>',
    '    </div>',
    '  </div>',
    '  <div class="rz-messages" id="rzMessages"></div>',
    '  <div class="rz-typing" id="rzTyping">',
    '    \u041C\u0430\u0440\u0433\u043E \u043F\u0435\u0447\u0430\u0442\u0430\u0435\u0442<span>.</span><span>.</span><span>.</span>',
    '  </div>',
    '  <div class="rz-quick-replies" id="rzQuickReplies"></div>',
    '  <div class="rz-input-area">',
    '    <input class="rz-input" id="rzInput" type="text" placeholder="\u041D\u0430\u043F\u0438\u0448\u0438\u0442\u0435 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435..." autocomplete="off">',
    '    <button class="rz-send-btn" id="rzSendBtn" aria-label="\u041E\u0442\u043F\u0440\u0430\u0432\u0438\u0442\u044C">',
    '      <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
    '    </button>',
    '  </div>',
    '</div>'
  ].join('\n');
  document.body.appendChild(container);

  // ── Elements ──
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

  // ── Helpers ──

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
    if (replies && replies.length) {
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
    showContactButton();
  }

  function showContactButton() {
    // Remove old contact button if exists
    var old = quickReplies.querySelector('.rz-contact-btn');
    if (old) old.remove();
    var cb = document.createElement('button');
    cb.className = 'rz-contact-btn';
    cb.textContent = '\u{1F4DE} \u0421\u0432\u044F\u0437\u0430\u0442\u044C\u0441\u044F \u0441 \u043E\u0442\u0434\u0435\u043B\u043E\u043C \u043F\u0440\u043E\u0434\u0430\u0436';
    cb.addEventListener('click', function() {
      sendMessage('\u0425\u043E\u0447\u0443 \u0441\u0432\u044F\u0437\u0430\u0442\u044C\u0441\u044F \u0441 \u043E\u0442\u0434\u0435\u043B\u043E\u043C \u043F\u0440\u043E\u0434\u0430\u0436');
    });
    quickReplies.appendChild(cb);
  }

  function showTyping() { typing.classList.add('show'); msgs.scrollTop = msgs.scrollHeight; }
  function hideTyping() { typing.classList.remove('show'); }

  // ── Session ──

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
      showQuickReplies([
        '\u0420\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u0442\u044C \u0434\u043E\u0445\u043E\u0434',
        '\u0426\u0435\u043D\u044B \u0438 \u043F\u043B\u0430\u043D\u0438\u0440\u043E\u0432\u043A\u0438',
        '\u0417\u0430\u043F\u043B\u0430\u043D\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u043E\u043D\u043B\u0430\u0439\u043D-\u043F\u043E\u043A\u0430\u0437'
      ]);
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
        showContactButton();
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
      showContactButton();
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

  function openChat() {
    if (!isOpen) toggle();
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

  // ── Export openBot() for landing page buttons ──
  window.openBot = openChat;
  window.rizaltaChat = {
    open: openChat,
    close: function() { if (isOpen) toggle(); },
    toggle: toggle
  };

})();
