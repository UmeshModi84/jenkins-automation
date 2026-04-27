/* eslint-env node */
module.exports = {
  env: { node: true, es2022: true, mocha: true },
  extends: ['eslint:recommended'],
  parserOptions: { ecmaVersion: 'latest' },
  ignorePatterns: ['node_modules/'],
  rules: {
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }]
  },
  overrides: [
    {
      files: ['public/**/*.js'],
      env: { browser: true, es2022: true }
    }
  ]
};
