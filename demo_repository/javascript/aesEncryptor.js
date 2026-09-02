// demo_repository/javascript/aesEncryptor.js
//
// SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
// SIH presentation. Never run in production.

const crypto = require("crypto");

/**
 * Encrypt a message with AES-256-GCM using a fixed key (demo only).
 * The scanner should detect the createCipheriv usage below.
 */
function encryptText(plainText, key) {
    const iv = crypto.randomBytes(12);
    // <-- scanner detects this line: createCipheriv('aes-256-gcm', ...)
    const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
    const encrypted = Buffer.concat([cipher.update(plainText, "utf8"), cipher.final()]);
    return { iv, tag: cipher.getAuthTag(), encrypted };
}

module.exports = { encryptText };