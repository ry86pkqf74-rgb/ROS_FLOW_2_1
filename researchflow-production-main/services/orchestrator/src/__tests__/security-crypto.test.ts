/**
 * Tests for SecurityEnhancementMiddleware encrypt / decrypt
 *
 * Validates:
 *   1. v2 envelope roundtrip  (encrypt → decrypt)
 *   2. v2 envelope format     (v2:<iv>:<ciphertext>:<authTag>)
 *   3. Corrupted v2 envelope  (bad auth tag / truncated)
 *   4. v1 legacy ciphertext   (deprecated format still decrypts)
 *   5. Non-determinism        (same plaintext → different ciphertext each call)
 *
 * Run with:
 *   node --import tsx --test src/__tests__/security-crypto.test.ts
 */

import { describe, it, before } from 'node:test';
import assert from 'node:assert/strict';
import { SecurityEnhancementMiddleware } from '../middleware/security-enhancements.js';

const TEST_ENCRYPTION_KEY = 'a]2Sf9x!Kq#nLzW8_P7vYbR4dGmU0JcHe'; // 34 chars, satisfies ≥32

let middleware: SecurityEnhancementMiddleware;

before(() => {
  middleware = new SecurityEnhancementMiddleware({
    encryptionKey: TEST_ENCRYPTION_KEY,
    jwtSecret: 'test-jwt-secret-that-is-at-least-32-chars-long!',
  });
});

// ---------------------------------------------------------------------------
// 1. v2 roundtrip
// ---------------------------------------------------------------------------
describe('v2 encrypt → decrypt roundtrip', () => {
  it('decrypts to the original plaintext', () => {
    const plaintext = 'Hello, ResearchFlow!';
    const { encrypted, iv } = middleware.encrypt(plaintext);
    const result = middleware.decrypt(encrypted, iv);
    assert.equal(result, plaintext);
  });

  it('handles empty string', () => {
    const { encrypted, iv } = middleware.encrypt('');
    assert.equal(middleware.decrypt(encrypted, iv), '');
  });

  it('handles long multi-line content', () => {
    const plaintext = 'line1\nline2\nline3'.repeat(500);
    const { encrypted, iv } = middleware.encrypt(plaintext);
    assert.equal(middleware.decrypt(encrypted, iv), plaintext);
  });
});

// ---------------------------------------------------------------------------
// 2. v2 envelope structure
// ---------------------------------------------------------------------------
describe('v2 envelope format', () => {
  it('encrypted string starts with "v2:"', () => {
    const { encrypted } = middleware.encrypt('test');
    assert.ok(encrypted.startsWith('v2:'));
  });

  it('contains exactly 4 colon-delimited parts', () => {
    const { encrypted } = middleware.encrypt('test');
    const parts = encrypted.split(':');
    assert.equal(parts.length, 4);
    assert.equal(parts[0], 'v2');
    // IV = 32 hex chars (16 bytes)
    assert.equal(parts[1].length, 32);
    // Auth tag = 32 hex chars (16 bytes)
    assert.equal(parts[3].length, 32);
  });

  it('returned iv matches the IV embedded in envelope', () => {
    const { encrypted, iv } = middleware.encrypt('test');
    const embeddedIv = encrypted.split(':')[1];
    assert.equal(embeddedIv, iv);
  });
});

// ---------------------------------------------------------------------------
// 3. Corrupted v2 should fail cleanly
// ---------------------------------------------------------------------------
describe('corrupted v2 ciphertext', () => {
  it('throws on tampered auth tag', () => {
    const { encrypted, iv } = middleware.encrypt('secret');
    // Flip last char of the auth tag
    const lastChar = encrypted.slice(-1);
    const flipped = lastChar === '0' ? '1' : '0';
    const tampered = encrypted.slice(0, -1) + flipped;

    assert.throws(() => middleware.decrypt(tampered, iv));
  });

  it('throws on truncated envelope', () => {
    const { encrypted, iv } = middleware.encrypt('data');
    const truncated = encrypted.slice(0, encrypted.length - 10);
    assert.throws(() => middleware.decrypt(truncated, iv));
  });

  it('throws on malformed v2 prefix with wrong part count', () => {
    assert.throws(
      () => middleware.decrypt('v2:aabbcc', 'deadbeef'),
      /Malformed v2 encryption envelope/
    );
  });
});

// ---------------------------------------------------------------------------
// 4. v1 legacy decryption
//
// The old code used deprecated `crypto.createCipher('aes-256-gcm', key)` which
// is no longer available.  We keep a v1 path that attempts decryption with an
// all-zero IV (matching createCipher's internal behaviour for GCM).
//
// Because `createCipher` is removed in modern Node, we cannot trivially
// generate a real v1 fixture at test-time.  Instead we verify the code path
// exists and fails gracefully for unknown data.
// ---------------------------------------------------------------------------
describe('v1 legacy decrypt path', () => {
  it('does not treat non-v2 string as v2', () => {
    // A random hex string that does NOT start with "v2:" should go through
    // the v1 path, which will fail because it isn't real v1 ciphertext.
    const fakeHex = 'deadbeefcafebabe1234567890abcdef';
    assert.throws(
      () => middleware.decrypt(fakeHex, 'aabbccdd'),
      /Re-encrypt with the current v2 format/
    );
  });

  it('gives a helpful error message for bad v1 data', () => {
    assert.throws(
      () => middleware.decrypt('not-hex-at-all', ''),
      /Re-encrypt with the current v2 format/
    );
  });
});

// ---------------------------------------------------------------------------
// 5. Non-determinism (each encrypt produces unique ciphertext)
// ---------------------------------------------------------------------------
describe('non-determinism', () => {
  it('produces different ciphertext for the same plaintext', () => {
    const a = middleware.encrypt('same').encrypted;
    const b = middleware.encrypt('same').encrypted;
    assert.notEqual(a, b);
  });
});
