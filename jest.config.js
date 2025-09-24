module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/tests/javascript'],
  testMatch: ['**/*.test.js'],
  setupFilesAfterEnv: ['<rootDir>/tests/javascript/setupTests.js'],
  moduleDirectories: ['node_modules', '<rootDir>/static', '<rootDir>/tests/javascript'],
  collectCoverageFrom: ['static/**/*.js'],
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['lcov', 'text-summary'],
  coverageThreshold: {
    global: {
      branches: 75,
      functions: 90,
      lines: 80,
      statements: 80
    }
  },
  moduleNameMapper: {
    '\\.(css|less|scss)$': 'identity-obj-proxy'
  }
};
