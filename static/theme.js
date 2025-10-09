(function () {
  const STORAGE_KEY = 'theme-preference';
  const THEME_ATTR = 'data-bs-theme';

  function getStoredPreference() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
  }

  function storePreference(value) {
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (_) {
      // ignore storage errors
    }
  }

  function getSystemPreference() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  function getCurrentPreference() {
    const stored = getStoredPreference();
    if (stored === 'light' || stored === 'dark') return stored;
    return 'system';
  }

  function applyTheme(theme) {
    const resolved = theme === 'system' ? getSystemPreference() : theme;
    document.documentElement.setAttribute(THEME_ATTR, resolved);
  }

  function initTheme() {
    // Apply ASAP to avoid flash
    applyTheme(getCurrentPreference());

    // Listen to system changes if following system
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', () => {
        if (getCurrentPreference() === 'system') applyTheme('system');
      });
    } else if (typeof media.addListener === 'function') {
      media.addListener(() => {
        if (getCurrentPreference() === 'system') applyTheme('system');
      });
    }

    // Wire profile selector if present
    const select = document.getElementById('themePreference');
    if (select) {
      select.value = getCurrentPreference();
      select.addEventListener('change', () => {
        const value = select.value;
        if (value === 'light' || value === 'dark') {
          storePreference(value);
        } else {
          // system
          try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
        }
        applyTheme(value);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
})();
