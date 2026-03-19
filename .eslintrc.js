const baseConfig = require("./config/.eslintrc.json");

module.exports = {
  ...baseConfig,
  env: {
    ...baseConfig.env,
    jest: true,
    node: true,
  },
  overrides: [
    {
      files: ["tests/javascript/**/*.js"],
      env: {
        browser: true,
        es2021: true,
        jest: true,
        node: true,
      },
    },
  ],
};
