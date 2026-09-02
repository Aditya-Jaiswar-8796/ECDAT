// demo_repository/javascript/hashFile.js
//
// SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
// SIH presentation. Never run in production.

const crypto = require("crypto");

/**
 * Compute a SHA-256 hex digest of some content (demo only).
 * The scanner should detect the createHash usage below.
 */
function sha256Hex(content) {
    // <-- scanner detects this line: createHash('sha256')
    return crypto.createHash("sha256").update(content).digest("hex");
}

module.exports = { sha256Hex };