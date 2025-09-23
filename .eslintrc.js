module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: false
  },
  extends: [
    'standard'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  globals: {
    // Bootstrap globals
    bootstrap: 'readonly',
    
    // Our logger utility
    Logger: 'readonly',
    
    // Our custom globals (functions exposed on window)
    changePage: 'writable',
    editUser: 'writable',
    toggleUserStatus: 'writable',
    resendInvitation: 'writable',
    cancelInvitation: 'writable',
    handleUserSelection: 'writable',
    handleInvitationSelection: 'writable',
    logout: 'writable'
  },
  rules: {
    // Enforce semicolons for clarity
    'semi': ['error', 'always'],
    
    // Disable space-before-function-paren to avoid conflict with Prettier
    // Prettier will handle function parenthesis spacing consistently
    'space-before-function-paren': 'off',
    
    // Enforce consistent quote style
    'quotes': ['error', 'single', { 'avoidEscape': true }],
    
    // Disable indent rule to avoid conflict with Prettier
    // Prettier will handle all indentation consistently
    'indent': 'off',
    
    // Enforce trailing commas for better diffs
    'comma-dangle': ['error', 'never'],
    
    // Error on console statements (should be removed in production)
    'no-console': 'error',
    
    // Error on unused variables
    'no-unused-vars': ['error', { 'argsIgnorePattern': '^_' }],
    
    // Enforce consistent function declarations
    'func-style': ['error', 'declaration', { 'allowArrowFunctions': true }],
    
    // Enforce consistent object property access
    'dot-notation': 'error',
    
    // Enforce consistent array/object formatting
    'object-curly-spacing': ['error', 'always'],
    'array-bracket-spacing': ['error', 'never'],
    
    // Security rules
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',
    
    // Best practices
    'eqeqeq': ['error', 'always'],
    'no-var': 'error',
    'prefer-const': 'error',
    'prefer-arrow-callback': 'error'
  }
};
