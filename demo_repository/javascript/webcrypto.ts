// demo_repository/javascript/webcrypto.ts
//
// SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
// SIH presentation. Never run in production.

/**
 * Hash a password using the browser Web Crypto API (SHA-256).
 * The scanner should detect the subtle.digest usage below.
 */
export async function hashPassword(password: string): Promise<string> {
    const data = new TextEncoder().encode(password);
    // <-- scanner detects this line: crypto.subtle.digest('SHA-256', ...)
    const digest = await crypto.subtle.digest("SHA-256", data);
    const bytes = new Uint8Array(digest);
    return Array.from(bytes)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
}