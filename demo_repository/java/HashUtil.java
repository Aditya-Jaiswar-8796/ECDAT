// demo_repository/java/HashUtil.java
//
// SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
// SIH presentation. Never run in production.

import java.security.MessageDigest;

/**
 * Demo utility that computes a SHA-256 hash of a string.
 * The scanner should detect the MessageDigest.getInstance usage below.
 */
public class HashUtil {

    public static String sha256Hex(String input) throws Exception {
        // <-- scanner detects this line: SHA-256
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(input.getBytes());
        StringBuilder hex = new StringBuilder();
        for (byte b : hash) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }
}