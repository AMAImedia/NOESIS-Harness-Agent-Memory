/* NOESIS universal shell: 11 languages, theme, language picker.
   Works with plain HTML pages; no build step. */
'use strict';
(function () {
  var LANGS = window.NOESIS_LANGS || [
    {code:'en', flag:'gb', native:'English',    english:'English'},
    {code:'zh', flag:'cn', native:'中文',         english:'Chinese'},
    {code:'hi', flag:'in', native:'हिन्दी',       english:'Hindi'},
    {code:'es', flag:'es', native:'Español',    english:'Spanish'},
    {code:'ar', flag:'sa', native:'العربية',     english:'Arabic'},
    {code:'fr', flag:'fr', native:'Français',   english:'French'},
    {code:'bn', flag:'bd', native:'বাংলা',       english:'Bengali'},
    {code:'pt', flag:'pt', native:'Português',  english:'Portuguese'},
    {code:'ru', flag:'ru', native:'Русский',    english:'Russian'},
    {code:'ja', flag:'jp', native:'日本語',       english:'Japanese'},
    {code:'vi', flag:'vn', native:'Tiếng Việt', english:'Vietnamese'}
  ];
  window.NOESIS_LANGS = LANGS;

  var LANG_KEY = 'noesis-shell-lang';
  var THEME_KEY = 'noesis-shell-theme';
  var current = localStorage.getItem(LANG_KEY) || (navigator.language || 'en').slice(0, 2);
  if (!LANGS.some(function (l) { return l.code === current; })) current = 'en';

  function flagUrl(code) {
    var meta = LANGS.find(function (l) { return l.code === code; }) || LANGS[0];
    return (window.NOESIS_FLAG_PATH || 'vendor/flags/') + meta.flag + '.png';
  }
  function langMeta(code) {
    return LANGS.find(function (l) { return l.code === code; }) || LANGS[0];
  }

  var api = {
    LANGS: LANGS,
    get lang() { return current; },
    setLang: function (code) {
      if (!LANGS.some(function (l) { return l.code === code; })) return;
      current = code;
      localStorage.setItem(LANG_KEY, code);
      document.documentElement.setAttribute('lang', code);
      document.documentElement.setAttribute('data-lang', code);
      if (api.dict) api.apply(api.dict);
      if (api.onChange) api.onChange(code);
      api.render();
    },
    t: function (dict, key) {
      var pack = dict[current] || dict.en || {};
      var en = dict.en || {};
      return pack[key] != null ? pack[key] : (en[key] != null ? en[key] : key);
    },
    apply: function (dict) {
      document.querySelectorAll('[data-i18n]').forEach(function (el) {
        var k = el.getAttribute('data-i18n');
        el.textContent = api.t(dict, k);
      });
      document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
        var k = el.getAttribute('data-i18n-html');
        el.innerHTML = api.t(dict, k);
      });
      document.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
        var k = el.getAttribute('data-i18n-ph');
        el.placeholder = api.t(dict, k);
      });
      document.querySelectorAll('[data-i18n-aria]').forEach(function (el) {
        var k = el.getAttribute('data-i18n-aria');
        el.setAttribute('aria-label', api.t(dict, k));
      });
    },
    render: function () {
      var btn = document.getElementById('langBtn');
      if (btn) {
        var m = langMeta(current);
        btn.innerHTML = '<img src="' + flagUrl(current) + '" width="20" height="14" alt="" style="border-radius:2px;object-fit:cover">' +
          '<span>' + m.native + '</span><span style="opacity:.6">▾</span>';
      }
      var menu = document.getElementById('langMenu');
      if (menu) {
        menu.innerHTML = '';
        LANGS.forEach(function (l) {
          var b = document.createElement('button');
          b.type = 'button';
          b.setAttribute('role', 'option');
          b.setAttribute('aria-selected', l.code === current ? 'true' : 'false');
          b.style.cssText = 'display:grid;grid-template-columns:22px 1fr;align-items:center;gap:8px;width:100%;padding:8px 10px;border:0;background:' +
            (l.code === current ? 'var(--surface-2)' : 'transparent') + ';border-radius:8px;color:var(--text);text-align:left;cursor:pointer;font:inherit';
          b.innerHTML = '<img src="' + flagUrl(l.code) + '" width="20" height="14" alt="" style="border-radius:2px;object-fit:cover">' +
            '<span>' + l.native + '</span>';
          b.addEventListener('click', function () { api.setLang(l.code); menu.classList.remove('open'); });
          menu.appendChild(b);
        });
      }
      var themeBtn = document.getElementById('themeBtn');
      if (themeBtn) themeBtn.textContent = document.documentElement.getAttribute('data-theme') === 'light' ? '☀' : '◐';
    },
    init: function (dict, onChange) {
      api.dict = dict || null;
      api.onChange = onChange || null;
      var savedTheme = localStorage.getItem(THEME_KEY);
      if (savedTheme === 'light' || savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', savedTheme);
      }
      var btn = document.getElementById('langBtn');
      var menu = document.getElementById('langMenu');
      if (btn && menu) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          menu.classList.toggle('open');
          btn.setAttribute('aria-expanded', menu.classList.contains('open') ? 'true' : 'false');
        });
        document.addEventListener('click', function () { menu.classList.remove('open'); });
      }
      var themeBtn = document.getElementById('themeBtn');
      if (themeBtn) {
        themeBtn.addEventListener('click', function () {
          var next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', next);
          localStorage.setItem(THEME_KEY, next);
          api.render();
        });
      }
      document.documentElement.setAttribute('lang', current);
      document.documentElement.setAttribute('data-lang', current);
      if (dict) api.apply(dict);
      api.render();
      if (onChange) onChange(current);
    }
  };
  window.NOESIS_SHELL = api;
})();
