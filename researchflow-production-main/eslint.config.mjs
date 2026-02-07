// ESLint v9+ flat config
// See: https://eslint.org/docs/latest/use/configure/configuration-files

import js from "@eslint/js";
import prettierConfig from "eslint-config-prettier";
import importPlugin from "eslint-plugin-import";
import tseslint from "typescript-eslint";

/** @type {import('eslint').Linter.FlatConfig[]} */
export default [
  // Base recommended rules
  js.configs.recommended,

  // TypeScript recommended rules
  ...tseslint.configs.recommended,

  // Global ignores
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/build/**",
      "**/.next/**",
      "**/coverage/**",
      "**/.turbo/**",
      "**/.cache/**",
      "**/.output/**",
      "services/web/**",
      "packages/cli/**",
    ],
  },

  // Project settings + plugin wiring
  {
    files: ["**/*.{ts,tsx,js,mjs,cjs}", "**/*.cts", "**/*.mts"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        // Keep lint fast & stable in CI; avoid type-aware lint until explicitly enabled.
        // If you later want type-aware rules, switch to:
        //   projectService: true
        // or provide a dedicated tsconfig.eslint.json.
      },
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin,
      import: importPlugin,
    },
    settings: {
      "import/resolver": {
        typescript: {
          project: "./tsconfig.json",
        },
        node: true,
      },
    },
    rules: {
      // Prefer TS-aware unused vars rule
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", ignoreRestSiblings: true },
      ],

      // Common pragmatic TS rules for mixed codebases
      "@typescript-eslint/no-explicit-any": "off",

      // Import sanity
      "import/no-unresolved": "off", // let TS handle this
      "import/order": [
        "warn",
        {
          "newlines-between": "always",
          alphabetize: { order: "asc", caseInsensitive: true },
        },
      ],

      // Prettier compatibility (turns off conflicting stylistic rules)
      ...prettierConfig.rules,
    },
  },
];
