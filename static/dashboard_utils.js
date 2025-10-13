/**
 * Dashboard Utilities - Shared functionality for all dashboard types
 *
 * This module provides common patterns used across all dashboard implementations:
 * - Auto-refresh with visibility change detection
 * - Cache management
 * - Loading state management
 * - Error handling
 */

/**
 * Create a dashboard data manager with auto-refresh capabilities
 *
 * @param {Object} config - Configuration object
 * @param {string} config.refreshButtonId - ID of the refresh button
 * @param {Function} config.loadDataFn - Function to call to load dashboard data
 * @param {number} [config.refreshInterval=300000] - Refresh interval in ms (default 5 minutes)
 * @returns {Object} Dashboard manager with init() and refresh() methods
 */
function createDashboardManager(config) {
  const { refreshButtonId, loadDataFn, refreshInterval = 5 * 60 * 1000 } = config;

  return {
    cache: null,
    lastFetch: 0,
    refreshInterval,

    init() {
      // Refresh when tab becomes visible after interval
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && Date.now() - this.lastFetch > this.refreshInterval) {
          this.loadData({ silent: true });
        }
      });

      // Refresh button handler
      const refreshButton = document.getElementById(refreshButtonId);
      if (refreshButton) {
        refreshButton.addEventListener('click', () => this.loadData({ silent: false }));
      }

      // Initial load and periodic refresh
      this.loadData();
      setInterval(() => this.loadData({ silent: true }), this.refreshInterval);
    },

    async refresh() {
      return this.loadData({ silent: false });
    },

    async loadData(options = {}) {
      return loadDataFn.call(this, options);
    }
  };
}

/**
 * Set loading state for a container
 *
 * @param {string} selector - CSS selector for the container
 * @param {string} message - Loading message to display
 */
function setDashboardLoading(selector, message) {
  const container = document.querySelector(selector);
  if (container) {
    container.innerHTML = `
      <div class="loading-state">
        <div class="spinner"></div>
        <p>${message}</p>
      </div>
    `;
  }
}

/**
 * Set error state for a container
 *
 * @param {string} selector - CSS selector for the container
 * @param {string} message - Error message to display
 */
function setDashboardError(selector, message) {
  const container = document.querySelector(selector);
  if (container) {
    container.innerHTML = `
      <div class="error-state">
        <i class="fas fa-exclamation-triangle"></i>
        <p>${message}</p>
      </div>
    `;
  }
}

/**
 * Common error handler for dashboard fetch operations
 *
 * @param {Error} error - The error object
 * @param {string} context - Context description for logging
 * @param {Object} containers - Object mapping container names to selectors
 */
function handleDashboardError(error, context, containers = {}) {
  // eslint-disable-next-line no-console
  console.error(`[Dashboard Error] ${context}:`, error);

  // Set error state for all provided containers
  for (const [name, selector] of Object.entries(containers)) {
    setDashboardError(selector, `Failed to load ${name}. Please refresh the page.`);
  }
}

/**
 * Fetch JSON data from an API endpoint with error handling
 *
 * @param {string} url - API endpoint URL
 * @param {Object} [options={}] - Fetch options
 * @returns {Promise<Object>} Parsed JSON response
 * @throws {Error} If fetch fails or response is not ok
 */
async function fetchDashboardData(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Unknown error');
    }

    return data;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`[Dashboard] Fetch failed for ${url}:`, error);
    throw error;
  }
}

// Export utilities (for ES6 modules or global access)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    createDashboardManager,
    setDashboardLoading,
    setDashboardError,
    handleDashboardError,
    fetchDashboardData
  };
}
