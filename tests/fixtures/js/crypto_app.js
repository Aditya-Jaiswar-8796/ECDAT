// tests/fixtures/js/crypto_app.js
const crypto = require("crypto");

// Node crypto - SHA-256 hash
const hash = crypto.createHash("sha256").update("data").digest("hex");

// Node crypto - AES-256-GCM cipher
const cipher = crypto.createCipheriv("aes-256-gcm", Buffer.alloc(32), Buffer.alloc(12));

// this fixture has more below to check line offsets
const plain = crypto.randomBytes(16);