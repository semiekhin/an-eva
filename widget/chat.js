(function() {
  'use strict';

  // ── Настройки ──
  var API_URL = window.RIZALTA_CHAT_API || '';
  var AUTO_OPEN_DELAY = 30000;
  var REQUEST_TIMEOUT = 30000;

  // ── DOM ──
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

  // ── Render ──

  function addMessage(text, role) {
    var div = document.createElement('div');
    div.className = 'rz-msg ' + role;
    if (role === 'bot') {
      div.innerHTML = '<span class="rz-msg-avatar">М</span>' + escapeHtml(text);
    } else {
      div.textContent = text;
    }
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;

    var history = loadLocalHistory();
    history.push({ role: role, text: text });
    saveLocalHistory(history);
  }

  function showQuickReplies(replies) {
    quickReplies.innerHTML = '';
    if (!replies || !replies.length) return;
    replies.forEach(function(text) {
      var b = document.createElement('button');
      b.className = 'rz-quick-btn';
      b.textContent = text;
      b.addEventListener('click', function() {
        quickReplies.innerHTML = '';
        sendMessage(text);
      });
      quickReplies.appendChild(b);
    });
  }

  function showTyping() { typing.classList.add('show'); msgs.scrollTop = msgs.scrollHeight; }
  function hideTyping() { typing.classList.remove('show'); }

  // ── Session ──

  function createSession() {
    return fetch(API_URL + '/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page_url: window.location.href })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      sessionId = data.session_id;
      localStorage.setItem('rz_session_id', sessionId);
      addMessage(data.greeting, 'bot');
      showQuickReplies(['Рассчитать доход', 'Подобрать апартаменты', 'Сравнить с депозитом']);
      return sessionId;
    });
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
        return createSession();
      }
      return r.json();
    })
    .then(function(data) {
      if (data && data.history) {
        // Восстанавливаем из сервера
        var localHistory = [];
        data.history.forEach(function(m) {
          var role = m.role === 'assistant' ? 'bot' : 'user';
          var div = document.createElement('div');
          div.className = 'rz-msg ' + role;
          if (role === 'bot') {
            div.innerHTML = '<span class="rz-msg-avatar">М</span>' + escapeHtml(m.content);
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

    // Если нет сессии — создаём, потом отправляем
    var sendFn = function() {
      var controller = new AbortController();
      var timeout = setTimeout(function() { controller.abort(); }, REQUEST_TIMEOUT);

      fetch(API_URL + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
        signal: controller.signal
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        clearTimeout(timeout);
        hideTyping();
        isSending = false;
        sendBtn.disabled = false;

        if (data.session_id) {
          sessionId = data.session_id;
          localStorage.setItem('rz_session_id', sessionId);
        }

        addMessage(data.reply, 'bot');
      })
      .catch(function(err) {
        clearTimeout(timeout);
        hideTyping();
        isSending = false;
        sendBtn.disabled = false;
        var errorMsg = err.name === 'AbortError'
          ? 'Сервер не отвечает, попробуйте позже.'
          : 'Извините, связь подвисла. Попробуйте ещё раз.';
        addMessage(errorMsg, 'bot');
      });
    };

    if (!sessionId) {
      createSession().then(sendFn);
    } else {
      sendFn();
    }
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

      // Первое открытие: создаём сессию
      if (!sessionId && loadLocalHistory().length === 0) {
        createSession();
      }
    } else {
      win.classList.remove('open');
      btn.classList.remove('active');
    }
  }

  // ── Events ──
  btn.addEventListener('click', toggle);
  sendBtn.addEventListener('click', function() { sendMessage(input.value); });
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  // ── Init ──

  // Восстанавливаем локальную историю если есть
  var localHistory = loadLocalHistory();
  if (localHistory.length > 0) {
    localHistory.forEach(function(m) {
      var div = document.createElement('div');
      div.className = 'rz-msg ' + m.role;
      if (m.role === 'bot') {
        div.innerHTML = '<span class="rz-msg-avatar">М</span>' + escapeHtml(m.text);
      } else {
        div.textContent = m.text;
      }
      msgs.appendChild(div);
    });
    msgs.scrollTop = msgs.scrollHeight;
  }

  // Если есть сессия, но нет локальной истории — восстанавливаем с сервера
  if (sessionId && localHistory.length === 0) {
    resumeSession();
  }

  // Автооткрытие через 30 сек
  if (!localStorage.getItem('rz_chat_opened')) {
    setTimeout(function() {
      if (!isOpen) toggle();
    }, AUTO_OPEN_DELAY);
  }

})();
