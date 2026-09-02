// tests/fixtures/js/crypto_app.ts
// TypeScript file: the finding language must be "typescript".

// Web Crypto API - SHA-256
const digest = crypto.subtle.digest("SHA-256", new TextEncoder().encode("data"));

// Node crypto module import (weak signal)
import * as nodeCrypto from "crypto";