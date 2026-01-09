module.exports = {
  testEnvironment: 'jsdom',
  rootDir: '..',
  roots: ['<rootDir>/tests/javascript'],
  testMatch: ['**/*.test.js'],
  setupFilesAfterEnv: ['<rootDir>/tests/javascript/setupTests.js'],
  moduleDirectories: ['node_modules', '<rootDir>/static', '<rootDir>/tests/javascript'],
  collectCoverageFrom: [
    'static/**/*.js'
  ],
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['lcov', 'text-summary', 'json'],
  coverageThreshold: {
    global: {
      lines: 80
    }
  },
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy'
  }
};
