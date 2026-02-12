/**
 * Tests for Scientific Notation Service
 * Task 149 - Scientific notation localization
 */

import { describe, it, expect } from 'vitest';

import {
  formatScientific,
  formatWithUnit,
  convertUnit,
  FormattingOptionsSchema,
} from '../scientificNotationService';
import scientificNotationService from '../scientificNotationService';

describe('ScientificNotationService', () => {
  describe('formatScientific', () => {
    it('should format in scientific notation', () => {
      const result = formatScientific(1234567, { style: 'SCIENTIFIC' });
      // Service produces Unicode: "1.23×10⁶"
      expect(result).toMatch(/1\.23.*×.*10.*⁶/);
    });

    it('should format in engineering notation', () => {
      const result = formatScientific(1234567, { style: 'ENGINEERING' });
      // Engineering notation uses powers of 3, produces Unicode superscripts
      expect(result).toMatch(/1\.23.*×.*10.*⁶/);
    });

    it('should format in E notation', () => {
      const result = formatScientific(1234567, { style: 'E_NOTATION' });
      expect(result).toMatch(/1\.23.*[eE].*6/);
    });

    it('should format in plain notation', () => {
      // Default significantDigits=3, useGrouping=true, locale='en-US'
      // 1234.56 with 3 sig digits → "1,230" (locale-formatted with grouping)
      const result = formatScientific(1234.56, { style: 'PLAIN' });
      expect(result).toMatch(/1[,.]?230/);
    });

    it('should use SI prefixes', () => {
      const result = formatScientific(1500, { style: 'SI_PREFIX' });
      expect(result).toMatch(/1\.5.*k/);
    });

    it('should format for LaTeX', () => {
      const result = formatScientific(1234567, { style: 'LATEX' });
      expect(result).toContain('\\times');
      expect(result).toContain('^{6}');
    });

    it('should respect significantDigits', () => {
      const result = formatScientific(1.23456789, { style: 'PLAIN', significantDigits: 2 });
      expect(result).toBe('1.2');
    });

    it('should add thousands separator', () => {
      const result = formatScientific(1234567, {
        style: 'PLAIN',
        useGrouping: true,
        locale: 'en-US',
        significantDigits: 7,
      });
      expect(result).toBe('1,234,567');
    });

    it('should use locale decimal separator', () => {
      const result = formatScientific(1234.56, {
        style: 'PLAIN',
        locale: 'de-DE',
        significantDigits: 10,
        useGrouping: false,
      });
      expect(result).toBe('1234,56');
    });

    it('should not add sign prefix for positive numbers (no option in schema)', () => {
      const result = formatScientific(42, { style: 'PLAIN' });
      expect(result).toBe('42');
    });

    it('should handle negative numbers', () => {
      const result = formatScientific(-42, { style: 'PLAIN' });
      expect(result).toBe('-42');
    });

    it('should handle zero', () => {
      const result = formatScientific(0, { style: 'SCIENTIFIC' });
      expect(result).toContain('0');
    });

    it('should handle very small numbers', () => {
      const result = formatScientific(0.000001234, { style: 'SCIENTIFIC' });
      // Service produces Unicode: "1.23×10⁻⁶"
      expect(result).toMatch(/1\.23.*×.*10.*⁻⁶/);
    });
  });

  describe('formatWithUnit', () => {
    it('should format value with unit', () => {
      // Default style is SCIENTIFIC, minExponentForScientific=4
      // 1500 has exponent 3 < 4, so falls back to PLAIN formatting
      // PLAIN with 3 sig digits, grouping=true → "1,500 m"
      const result = formatWithUnit(1500, 'm');
      expect(result).toMatch(/1[,.]?500/);
      expect(result).toContain('m');
    });

    it('should apply SI prefix to value with unit', () => {
      // SI_PREFIX: 1500 → "1.5k", then " m" appended → "1.5k m"
      const result = formatWithUnit(1500, 'm', { style: 'SI_PREFIX' });
      expect(result).toMatch(/1\.5k\s*m/);
    });

    it('should format with complex units', () => {
      const result = formatWithUnit(9.8, 'm/s²', { style: 'PLAIN', significantDigits: 2 });
      expect(result).toBe('9.8 m/s²');
    });
  });

  describe('convertUnit', () => {
    it('should convert between compatible units', () => {
      const result = convertUnit(1000, 'm', 'km');
      expect(result).toBe(1);
    });

    it('should return undefined for temperature (°C/°F have no siConversion in service)', () => {
      expect(convertUnit(100, '°C', '°F')).toBeUndefined();
      expect(convertUnit(32, '°F', '°C')).toBeUndefined();
    });

    it('should return undefined for incompatible units', () => {
      expect(convertUnit(1, 'm', 'kg')).toBeUndefined();
    });

    it('should handle same unit conversion', () => {
      const result = convertUnit(42, 'm', 'm');
      expect(result).toBe(42);
    });
  });

  describe('supported units (from COMMON_UNITS)', () => {
    it('should expose list of supported units via default export', () => {
      const units = Object.keys(scientificNotationService.COMMON_UNITS);
      expect(units.length).toBeGreaterThan(0);
      expect(units).toContain('m');
      expect(units).toContain('kg');
      expect(units).toContain('s');
    });
  });

  describe('default formatting options (FormattingOptionsSchema)', () => {
    it('should have default options with style, significantDigits, locale', () => {
      const options = FormattingOptionsSchema.parse({});
      expect(options).toHaveProperty('style');
      expect(options).toHaveProperty('significantDigits');
      expect(options).toHaveProperty('locale');
    });
  });
});
