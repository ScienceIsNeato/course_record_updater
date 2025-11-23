/**
 * Simple frontend logger utility
 * Provides consistent logging with levels and can be easily configured
 */

const Logger = {
  // Log levels
  LEVELS: {
    ERROR: 0,
    WARN: 1,
    INFO: 2,
    DEBUG: 3
  },

  // Current log level (can be set via environment or config)
  currentLevel: 2, // INFO level by default

  /**
   * Log an error message
   * @param {string} message - The message to log
   * @param {*} data - Optional additional data
   */
  error: function (message, data) {
    if (this.currentLevel >= this.LEVELS.ERROR) {
      if (data) {
        console.error(`❌ ${message}`, data); // eslint-disable-line no-console
      } else {
        console.error(`❌ ${message}`); // eslint-disable-line no-console
      }
    }
  },

  /**
   * Log a warning message
   * @param {string} message - The message to log
   * @param {*} data - Optional additional data
   */
  warn: function (message, data) {
    if (this.currentLevel >= this.LEVELS.WARN) {
      if (data) {
        console.warn(`⚠️ ${message}`, data); // eslint-disable-line no-console
      } else {
        console.warn(`⚠️ ${message}`); // eslint-disable-line no-console
      }
    }
  },

  /**
   * Log an info message
   * @param {string} message - The message to log
   * @param {*} data - Optional additional data
   */
  info: function (message, data) {
    if (this.currentLevel >= this.LEVELS.INFO) {
      if (data) {
        console.log(`ℹ️ ${message}`, data); // eslint-disable-line no-console
      } else {
        console.log(`ℹ️ ${message}`); // eslint-disable-line no-console
      }
    }
  },

  /**
   * Log a debug message
   * @param {string} message - The message to log
   * @param {*} data - Optional additional data
   */
  debug: function (message, data) {
    if (this.currentLevel >= this.LEVELS.DEBUG) {
      if (data) {
        console.log(`🐛 ${message}`, data); // eslint-disable-line no-console
      } else {
        console.log(`🐛 ${message}`); // eslint-disable-line no-console
      }
    }
  },

  /**
   * Set the current log level
   * @param {number} level - The log level to set
   */
  setLevel: function (level) {
    this.currentLevel = level;
  }
};

// Make logger available globally
globalThis.Logger = Logger;

if (typeof module !== 'undefined' && module.exports) {
  module.exports = Logger;
}
