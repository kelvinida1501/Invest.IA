import js from '@eslint/js';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx,js,jsx}'],
    ignores: ['node_modules', 'dist'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2021,
      sourceType: 'module'
    },
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooks,
      '@typescript-eslint': tsPlugin
    },
    rules: {
      'react/react-in-jsx-scope': 'off', // Não necessário no React 17+
      '@typescript-eslint/no-unused-vars': ['warn'],
      semi: ['error', 'always'],
      quotes: ['error', 'single']
    },
    settings: {
      react: {
        version: 'detect'
      }
    }
  }
];
