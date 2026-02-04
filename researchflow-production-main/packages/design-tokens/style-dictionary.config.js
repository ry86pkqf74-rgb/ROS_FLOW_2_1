const StyleDictionary = require('style-dictionary');

// Custom transform to convert token names to CSS variable format
StyleDictionary.registerTransform({
  name: 'name/cti/kebab-custom',
  type: 'name',
  transformer: (token, options) => {
    return token.path.join('-').toLowerCase();
  }
});

// Custom format for TypeScript constants
StyleDictionary.registerFormat({
  name: 'typescript/es6-declarations',
  formatter: function({ dictionary, file }) {
    let output = `/**
 * ResearchFlow Design Tokens
 * Auto-generated from tokens/*.json - DO NOT EDIT DIRECTLY
 * Generated: ${new Date().toISOString()}
 */

`;

    // Generate type definitions
    output += `export interface DesignTokens {\n`;
    
    dictionary.allTokens.forEach(token => {
      const name = token.path.join('_').toUpperCase();
      output += `  ${name}: string;\n`;
    });
    
    output += `}\n\n`;

    // Generate constants object
    output += `export const tokens: DesignTokens = {\n`;
    
    dictionary.allTokens.forEach(token => {
      const name = token.path.join('_').toUpperCase();
      const value = typeof token.value === 'string' ? token.value : JSON.stringify(token.value);
      output += `  ${name}: '${value}',\n`;
    });
    
    output += `} as const;\n\n`;

    // Generate CSS variable references
    output += `export const cssVars = {\n`;
    
    dictionary.allTokens.forEach(token => {
      const name = token.path.join('_').toUpperCase();
      const cssVar = '--' + token.path.join('-').toLowerCase();
      output += `  ${name}: 'var(${cssVar})',\n`;
    });
    
    output += `} as const;\n\n`;

    // Export individual token categories
    output += `// Semantic color tokens\n`;
    output += `export const colors = {\n`;
    dictionary.allTokens
      .filter(t => t.path[0] === 'color' || t.path[0] === 'semantic')
      .forEach(token => {
        const name = token.path.slice(1).join('_').toUpperCase() || token.path[0].toUpperCase();
        output += `  ${name}: 'var(--${token.path.join('-').toLowerCase()})',\n`;
      });
    output += `} as const;\n\n`;

    output += `// Spacing tokens\n`;
    output += `export const spacing = {\n`;
    dictionary.allTokens
      .filter(t => t.path[0] === 'spacing')
      .forEach(token => {
        const name = token.path[1].replace('.', '_');
        output += `  '${name}': 'var(--${token.path.join('-').toLowerCase()})',\n`;
      });
    output += `} as const;\n\n`;

    output += `export default tokens;\n`;

    return output;
  }
});

module.exports = {
  source: ['tokens/**/*.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: 'dist/',
      files: [
        {
          destination: 'tokens.css',
          format: 'css/variables',
          options: {
            outputReferences: true
          }
        }
      ],
      transforms: ['attribute/cti', 'name/cti/kebab-custom', 'time/seconds', 'content/icon', 'size/rem', 'color/css']
    },
    ts: {
      transformGroup: 'js',
      buildPath: 'dist/',
      files: [
        {
          destination: 'tokens.ts',
          format: 'typescript/es6-declarations'
        }
      ]
    },
    js: {
      transformGroup: 'js',
      buildPath: 'dist/',
      files: [
        {
          destination: 'tokens.js',
          format: 'javascript/es6'
        },
        {
          destination: 'tokens.mjs',
          format: 'javascript/es6'
        }
      ]
    },
    json: {
      transformGroup: 'js',
      buildPath: 'dist/',
      files: [
        {
          destination: 'tokens.json',
          format: 'json/flat'
        }
      ]
    }
  }
};
