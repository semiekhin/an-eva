/**
 * RIZALTA Chat Widget Loader
 *
 * Встраивание на сайт одной строкой:
 * <script src="https://webchat.rizaltaservice.ru/widget/chat-widget.js"></script>
 *
 * Опционально можно задать API URL перед подключением:
 * <script>window.RIZALTA_CHAT_API = 'https://my-custom-url.com';</script>
 */
(function() {
  'use strict';

  if (document.getElementById('rizalta-chat-widget')) return;

  var scriptTag = document.currentScript || (function() {
    var scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  var baseUrl = scriptTag.src.replace(/\/widget\/chat-widget\.js.*$/, '');

  if (!window.RIZALTA_CHAT_API) {
    window.RIZALTA_CHAT_API = baseUrl;
  }

  var iframe = document.createElement('iframe');
  iframe.id = 'rizalta-chat-frame';
  iframe.src = baseUrl + '/widget/chat-widget.html';
  iframe.style.cssText = 'position:fixed;bottom:0;right:0;width:480px;height:650px;border:none;z-index:99999;background:transparent;pointer-events:none;';
  iframe.setAttribute('allow', 'clipboard-read; clipboard-write');
  iframe.setAttribute('loading', 'lazy');

  iframe.onload = function() {
    iframe.style.pointerEvents = 'auto';
  };

  document.body.appendChild(iframe);
})();
