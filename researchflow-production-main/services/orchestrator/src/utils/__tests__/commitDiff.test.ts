import { describe, it, expect } from 'vitest';

import { computeSectionSummary, computeUnifiedDiff } from '../commitDiff';

describe('commitDiff utilities', () => {
  it('computes a PHI-safe section summary (no raw text)', () => {
    const oldContent = {
      A: 'Patient John Doe has diabetes.',
      B: 'Allergies: penicillin',
    };
    const newContent = {
      A: 'Patient John Doe has diabetes mellitus type 2.',
      C: 'Medications: metformin',
    };

    const summary = computeSectionSummary(oldContent, newContent);

    expect(summary.added_section_keys).toEqual(['C']);
    expect(summary.removed_section_keys).toEqual(['B']);
    expect(summary.modified_section_keys).toEqual(['A']);
    expect(summary.changed_section_keys).toEqual(['A', 'B', 'C']);
    expect(summary.changed_sections_count).toBe(3);
    expect(summary.added_sections_count).toBe(1);
    expect(summary.removed_sections_count).toBe(1);
    expect(summary.modified_sections_count).toBe(1);
    expect(typeof summary.word_count_delta).toBe('number');
    expect(typeof summary.old_total_word_count).toBe('number');
    expect(typeof summary.new_total_word_count).toBe('number');

    const serialized = JSON.stringify(summary);
    expect(serialized).not.toContain(oldContent.A);
    expect(serialized).not.toContain(oldContent.B);
    expect(serialized).not.toContain(newContent.A);
    expect(serialized).not.toContain(newContent.C);
  });

  it('computes deterministic output for summary and diff', () => {
    const oldContent = { Z: 'z', A: 'alpha', B: 'beta' };
    const newContent = { A: 'alpha', B: 'beta2', C: 'gamma' };

    const s1 = computeSectionSummary(oldContent, newContent);
    const s2 = computeSectionSummary(oldContent, newContent);
    expect(s1).toEqual(s2);

    const d1 = computeUnifiedDiff(oldContent, newContent, { hipaaMode: true, hashSalt: 'salt' });
    const d2 = computeUnifiedDiff(oldContent, newContent, { hipaaMode: true, hashSalt: 'salt' });
    expect(d1).toBe(d2);
  });

  it('does not leak raw section content in HIPAA-mode unified diff', () => {
    const oldContent = {
      assessment: 'John Doe, DOB 01/02/1970, SSN 123-45-6789',
      plan: 'Start metformin 500mg daily',
    };
    const newContent = {
      assessment: 'John Doe, DOB 01/02/1970, SSN 123-45-6789 (verified)',
      plan: 'Start metformin 500mg daily',
      followup: 'Return in 2 weeks',
    };

    const diff = computeUnifiedDiff(oldContent, newContent, { hipaaMode: true, hashSalt: 'unit-test' });

    expect(diff).toContain('--- old');
    expect(diff).toContain('+++ new');
    expect(diff).toContain('assessment');
    expect(diff).toContain('sha256=');

    expect(diff).not.toContain(oldContent.assessment);
    expect(diff).not.toContain(newContent.assessment);
    expect(diff).not.toContain('metformin 500mg daily');
    expect(diff).not.toContain('Return in 2 weeks');
  });

  it('includes escaped raw values when hipaaMode=false', () => {
    const oldContent = { A: 'line1\nline2' };
    const newContent = { A: 'line1\nline2 changed' };

    const diff = computeUnifiedDiff(oldContent, newContent, { hipaaMode: false });
    expect(diff).toContain('A\tline1\\nline2');
    expect(diff).toContain('A\tline1\\nline2 changed');
  });
});

