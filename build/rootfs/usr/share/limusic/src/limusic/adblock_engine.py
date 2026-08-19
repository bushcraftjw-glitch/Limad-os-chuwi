import json
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parents[2] / "data" / "adblock-scriptlet-rules.json"


def _load_rules():
    with RULES_FILE.open("r", encoding="utf-8") as handle:
        rules = json.load(handle)
    if rules.get("format") != "org.limad.adblock-scriptlet-rules":
        raise ValueError("Ungültiges LiMusic-Adblock-Regelformat")
    if rules.get("format_version") != 1:
        raise ValueError("Nicht unterstützte LiMusic-Adblock-Regelversion")
    return rules


RULES = _load_rules()
_RULES_JSON = json.dumps(RULES, ensure_ascii=False, separators=(",", ":"))

_ENGINE_TEMPLATE = r"""
(() => {
  'use strict';

  const RULES = __RULES_JSON__;
  const host = String(location.hostname || '').toLowerCase();
  if (!(host === 'youtube.com' || host.endsWith('.youtube.com'))) return;

  const KEY = '__limusicScriptletEngineV1';
  if (window[KEY] && window[KEY].installed) {
    try { window[KEY].ensureRuntime && window[KEY].ensureRuntime(); } catch (_) {}
    return;
  }

  const native = {
    fetch: typeof window.fetch === 'function' ? window.fetch : null,
    XMLHttpRequest: window.XMLHttpRequest,
    jsonParse: JSON.parse.bind(JSON),
    jsonStringify: JSON.stringify.bind(JSON),
    appendChild: Node.prototype.appendChild,
    insertBefore: Node.prototype.insertBefore,
    replaceChild: Node.prototype.replaceChild,
  };

  const state = window[KEY] = {
    installed: false,
    engineVersion: RULES.engine_version,
    fetchHits: 0,
    xhrHits: 0,
    prunedKeys: 0,
    reelAdsRemoved: 0,
    textReplacements: 0,
    bypassScriptsRemoved: 0,
    skipClicks: 0,
    reports: 0,
    runtimeTimer: null,
    observer: null,
    enabled: true,
  };

  const report = (event, extra = {}) => {
    if (state.reports >= 180) return;
    state.reports += 1;
    try {
      const handler = window.webkit &&
        window.webkit.messageHandlers &&
        window.webkit.messageHandlers.limusicAdDiag;
      if (handler) {
        handler.postMessage(native.jsonStringify({
          source: 'scriptlet-engine-v1',
          event,
          at: Date.now(),
          href: location.href,
          ...extra,
        }));
      }
    } catch (_) {}
  };

  report('engine-enter', {engineVersion: RULES.engine_version});

  const targetUrlRegex = new RegExp(RULES.response_url_regex, 'i');
  const pruneKeys = new Set(RULES.prune_keys || []);

  const isTargetUrl = (url) => {
    try { return targetUrlRegex.test(String(url || '')); }
    catch (_) { return false; }
  };

  const pruneObject = (value, depth = 0, seen = new WeakSet()) => {
    if (!value || typeof value !== 'object' || depth > 14) return value;
    if (seen.has(value)) return value;
    seen.add(value);

    if (Array.isArray(value)) {
      for (let index = value.length - 1; index >= 0; index -= 1) {
        const item = value[index];
        if (RULES.remove_reel_ads) {
          try {
            const endpoint = item && item.command && item.command.reelWatchEndpoint;
            if (endpoint && endpoint.adClientParams && endpoint.adClientParams.isAd) {
              value.splice(index, 1);
              state.reelAdsRemoved += 1;
              continue;
            }
          } catch (_) {}
        }
        pruneObject(item, depth + 1, seen);
      }
      return value;
    }

    for (const key of Object.keys(value)) {
      if (pruneKeys.has(key)) {
        try {
          delete value[key];
          state.prunedKeys += 1;
        } catch (_) {}
        continue;
      }
      try { pruneObject(value[key], depth + 1, seen); } catch (_) {}
    }
    return value;
  };

  const exactReplace = (text) => {
    let clean = text;
    for (const rule of RULES.exact_key_replacements || []) {
      const before = clean;
      clean = clean.split(rule.from).join(rule.to);
      if (clean !== before) state.textReplacements += 1;
    }
    return clean;
  };

  const regexReplaceValidated = (text, url) => {
    let clean = text;
    for (const rule of RULES.validated_regex_replacements || []) {
      try {
        if (!(new RegExp(rule.url_regex, 'i')).test(String(url || ''))) continue;
        const candidate = clean.replace(
          new RegExp(rule.pattern, rule.flags || ''),
          rule.replacement || ''
        );
        if (candidate === clean) continue;
        // Never return malformed JSON from a regex quick-fix.
        native.jsonParse(candidate);
        clean = candidate;
        state.textReplacements += 1;
      } catch (_) {}
    }
    return clean;
  };

  const cleanText = (text, url, source) => {
    if (!state.enabled || typeof text !== 'string' || !isTargetUrl(url)) return text;
    let clean = exactReplace(text);
    clean = regexReplaceValidated(clean, url);
    try {
      const parsed = native.jsonParse(clean);
      const beforePruned = state.prunedKeys;
      const beforeReels = state.reelAdsRemoved;
      pruneObject(parsed);
      if (
        state.prunedKeys !== beforePruned ||
        state.reelAdsRemoved !== beforeReels
      ) {
        clean = native.jsonStringify(parsed);
      }
    } catch (_) {}

    if (clean !== text) {
      report('response-cleaned', {
        source,
        url: String(url || '').slice(0, 260),
      });
    }
    return clean;
  };

  const cleanJson = (value, url, source) => {
    if (!state.enabled || !isTargetUrl(url)) return value;
    const beforePruned = state.prunedKeys;
    const beforeReels = state.reelAdsRemoved;
    try { pruneObject(value); } catch (_) {}
    if (
      state.prunedKeys !== beforePruned ||
      state.reelAdsRemoved !== beforeReels
    ) {
      report('json-cleaned', {
        source,
        url: String(url || '').slice(0, 260),
      });
    }
    return value;
  };

  // AdGuard/uBO-style response replacement: hook fetch itself and return a
  // cleaned Response before YouTube page code can parse the player payload.
  if (native.fetch) {
    const fetchProxy = new Proxy(native.fetch, {
      async apply(target, thisArg, args) {
        const response = await Reflect.apply(target, thisArg, args);
        let url = '';
        try {
          url = response.url ||
            (args[0] && typeof args[0] === 'object' && args[0].url) ||
            String(args[0] || '');
        } catch (_) {}
        if (!state.enabled || !isTargetUrl(url)) return response;

        try {
          const clone = response.clone();
          const rawText = await clone.text();
          const clean = cleanText(rawText, url, 'fetch-proxy');
          if (clean === rawText) return response;

          state.fetchHits += 1;
          const headers = new Headers(response.headers);
          headers.delete('content-length');
          headers.delete('content-encoding');
          const replacement = new Response(clean, {
            status: response.status,
            statusText: response.statusText,
            headers,
          });
          for (const prop of ['url', 'redirected', 'type']) {
            try {
              Object.defineProperty(replacement, prop, {
                configurable: true,
                enumerable: true,
                value: response[prop],
              });
            } catch (_) {}
          }
          report('fetch-response-replaced', {
            url: String(url).slice(0, 260),
            status: response.status,
          });
          return replacement;
        } catch (error) {
          report('fetch-clean-error', {error: String(error)});
          return response;
        }
      },
    });

    try {
      Object.defineProperty(window, 'fetch', {
        configurable: false,
        enumerable: true,
        get: () => fetchProxy,
        set: () => {},
      });
      report('fetch-proxy-installed');
    } catch (error) {
      try { window.fetch = fetchProxy; } catch (_) {}
      report('fetch-proxy-soft-installed', {error: String(error)});
    }
  }

  // Fallback for code which captured Response methods before fetch was wrapped.
  try {
    if (typeof Response !== 'undefined' && Response.prototype) {
      if (typeof Response.prototype.json === 'function') {
        const responseJson = Response.prototype.json;
        Response.prototype.json = function(...args) {
          const url = this.url || '';
          return responseJson.apply(this, args).then((value) =>
            cleanJson(value, url, 'response-json')
          );
        };
      }
      if (typeof Response.prototype.text === 'function') {
        const responseText = Response.prototype.text;
        Response.prototype.text = function(...args) {
          const url = this.url || '';
          return responseText.apply(this, args).then((text) =>
            cleanText(text, url, 'response-text')
          );
        };
      }
      report('response-methods-installed');
    }
  } catch (error) {
    report('response-methods-error', {error: String(error)});
  }

  // Proxy the XHR *instance*, not its prototype getters. This also works when
  // WebKit marks native response/responseText accessors non-configurable.
  try {
    const NativeXHR = native.XMLHttpRequest;
    const handlerMap = new WeakMap();

    const XHRConstructorProxy = new Proxy(NativeXHR, {
      construct(target, args, newTarget) {
        const xhr = Reflect.construct(target, args, newTarget);
        let requestUrl = '';
        let proxy = null;
        let cachedRawText = null;
        let cachedCleanText = null;

        const getCleanText = () => {
          let raw;
          try { raw = xhr.responseText; }
          catch (_) { return null; }
          if (raw === cachedRawText && cachedCleanText !== null) {
            return cachedCleanText;
          }
          cachedRawText = raw;
          cachedCleanText = cleanText(
            raw,
            requestUrl || xhr.responseURL || '',
            'xhr-proxy'
          );
          if (cachedCleanText !== raw) state.xhrHits += 1;
          return cachedCleanText;
        };

        proxy = new Proxy(xhr, {
          get(obj, prop) {
            if (prop === 'open') {
              return function(method, url, ...rest) {
                requestUrl = String(url || '');
                return obj.open(method, url, ...rest);
              };
            }
            if (prop === 'responseText') {
              const url = requestUrl || obj.responseURL || '';
              if (state.enabled && isTargetUrl(url)) {
                const clean = getCleanText();
                if (clean !== null) return clean;
              }
              return obj.responseText;
            }
            if (prop === 'response') {
              const url = requestUrl || obj.responseURL || '';
              if (state.enabled && isTargetUrl(url)) {
                try {
                  if (obj.responseType === 'json' && obj.response) {
                    return cleanJson(obj.response, url, 'xhr-json-proxy');
                  }
                  if (obj.responseType === '' || obj.responseType === 'text') {
                    const clean = getCleanText();
                    if (clean !== null) return clean;
                  }
                } catch (_) {}
              }
              return obj.response;
            }
            if (prop === 'addEventListener') {
              return function(type, callback, options) {
                if (typeof callback !== 'function') {
                  return obj.addEventListener(type, callback, options);
                }
                let callbacks = handlerMap.get(obj);
                if (!callbacks) {
                  callbacks = new WeakMap();
                  handlerMap.set(obj, callbacks);
                }
                let wrapped = callbacks.get(callback);
                if (!wrapped) {
                  wrapped = function(event) {
                    return callback.call(proxy, event);
                  };
                  callbacks.set(callback, wrapped);
                }
                return obj.addEventListener(type, wrapped, options);
              };
            }
            if (prop === 'removeEventListener') {
              return function(type, callback, options) {
                const callbacks = handlerMap.get(obj);
                const wrapped = callbacks && callbacks.get(callback);
                return obj.removeEventListener(type, wrapped || callback, options);
              };
            }
            const value = Reflect.get(obj, prop, obj);
            return typeof value === 'function' ? value.bind(obj) : value;
          },
          set(obj, prop, value) {
            if (typeof prop === 'string' && prop.startsWith('on') && typeof value === 'function') {
              obj[prop] = function(...args) {
                return value.apply(proxy, args);
              };
              return true;
            }
            return Reflect.set(obj, prop, value, obj);
          },
        });
        return proxy;
      },
      get(target, prop, receiver) {
        return Reflect.get(target, prop, receiver);
      },
    });

    try {
      Object.defineProperty(window, 'XMLHttpRequest', {
        configurable: false,
        enumerable: true,
        get: () => XHRConstructorProxy,
        set: () => {},
      });
      report('xhr-constructor-proxy-installed');
    } catch (error) {
      try { window.XMLHttpRequest = XHRConstructorProxy; } catch (_) {}
      report('xhr-constructor-proxy-soft-installed', {error: String(error)});
    }
  } catch (error) {
    report('xhr-constructor-proxy-error', {error: String(error)});
  }

  // JSON.parse fallback for initial player payloads and nested playerResponse.
  try {
    const jsonParseProxy = new Proxy(native.jsonParse, {
      apply(target, thisArg, args) {
        const result = Reflect.apply(target, thisArg, args);
        try {
          const text = args[0];
          if (
            typeof text === 'string' &&
            (text.includes('"adPlacements"') ||
             text.includes('"adSlots"') ||
             text.includes('"playerAds"'))
          ) {
            pruneObject(result);
          }
        } catch (_) {}
        return result;
      },
    });
    try {
      Object.defineProperty(JSON, 'parse', {
        configurable: false,
        enumerable: false,
        get: () => jsonParseProxy,
        set: () => {},
      });
    } catch (_) {
      JSON.parse = jsonParseProxy;
    }
    report('json-parse-proxy-installed');
  } catch (error) {
    report('json-parse-proxy-error', {error: String(error)});
  }

  // Equivalent of the narrowly-targeted uBO DOM-bypass quick-fix.
  const shouldRemoveScript = (node) => {
    try {
      if (!node || String(node.nodeName).toUpperCase() !== 'SCRIPT') return false;
      const text = String(node.textContent || node.innerText || '');
      return (RULES.remove_script_text_contains || []).some((needle) =>
        text.includes(needle)
      );
    } catch (_) {
      return false;
    }
  };

  const protectInsertion = (nativeMethod, name) => function(node, ...rest) {
    if (shouldRemoveScript(node)) {
      state.bypassScriptsRemoved += 1;
      report('bypass-script-removed', {method: name});
      try { node.textContent = ''; } catch (_) {}
    }
    return nativeMethod.call(this, node, ...rest);
  };

  try {
    Node.prototype.appendChild = protectInsertion(native.appendChild, 'appendChild');
    Node.prototype.insertBefore = protectInsertion(native.insertBefore, 'insertBefore');
    Node.prototype.replaceChild = protectInsertion(native.replaceChild, 'replaceChild');
    report('dom-bypass-guards-installed');
  } catch (error) {
    report('dom-bypass-guards-error', {error: String(error)});
  }

  const hideCosmetic = () => {
    for (const selector of RULES.cosmetic_selectors || []) {
      try {
        document.querySelectorAll(selector).forEach((node) => {
          node.style.setProperty('display', 'none', 'important');
          node.style.setProperty('visibility', 'hidden', 'important');
          node.style.setProperty('pointer-events', 'none', 'important');
        });
      } catch (_) {}
    }
  };

  const clickSkip = () => {
    const selectors = [
      '.ytp-ad-skip-button',
      '.ytp-skip-ad-button',
      '.ytp-ad-skip-button-modern',
      'button[class*="ytp-ad-skip"]',
      '[id*="skip-button"] button',
      'button[aria-label*="Skip"]',
      'button[aria-label*="Überspring"]',
      'button[aria-label*="überspring"]',
    ];
    for (const selector of selectors) {
      try {
        const button = document.querySelector(selector);
        if (button) {
          button.click();
          state.skipClicks += 1;
          report('skip-clicked', {selector});
          return true;
        }
      } catch (_) {}
    }
    return false;
  };

  const fastForwardAd = () => {
    try {
      const player = document.querySelector('#movie_player, .html5-video-player');
      if (!player || !player.classList.contains('ad-showing')) return false;
      const media = document.querySelector('video, audio');
      if (!media) return false;
      media.muted = true;
      let end = Number(media.duration);
      try {
        if (media.seekable && media.seekable.length) {
          end = Number(media.seekable.end(media.seekable.length - 1));
        }
      } catch (_) {}
      if (Number.isFinite(end) && end > 0.25) {
        media.currentTime = Math.max(0, end - 0.02);
      } else {
        media.playbackRate = 16;
      }
      return true;
    } catch (_) {
      return false;
    }
  };

  state.ensureRuntime = () => {
    if (!state.enabled) return;
    hideCosmetic();
    clickSkip();
    fastForwardAd();
  };

  try {
    if (document.documentElement) {
      state.observer = new MutationObserver(() => {
        if (state.enabled) queueMicrotask(state.ensureRuntime);
      });
      state.observer.observe(document.documentElement, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ['class', 'style', 'hidden', 'aria-label'],
      });
    }
    state.runtimeTimer = setInterval(state.ensureRuntime, 100);
  } catch (error) {
    report('runtime-install-error', {error: String(error)});
  }

  window.__limusicAdBlockTick = state.ensureRuntime;
  window.__limusicSetAdBlockEnabled = (enabled) => {
    state.enabled = Boolean(enabled);
    if (state.enabled) state.ensureRuntime();
    return state.enabled;
  };

  state.installed = true;
  state.ensureRuntime();
  report('engine-ready');
})();
"""

ENGINE_BOOTSTRAP_SCRIPT = _ENGINE_TEMPLATE.replace("__RULES_JSON__", _RULES_JSON)

# The same idempotent engine is deliberately used at document-end and for
# COMMITTED/FINISHED fallback injection. If document-start already worked it
# only calls ensureRuntime(); otherwise it installs the full engine there.
ENGINE_RUNTIME_SCRIPT = ENGINE_BOOTSTRAP_SCRIPT
