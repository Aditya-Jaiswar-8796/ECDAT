// demo_repository/java/PaymentService.java
//
// SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
// SIH presentation. Never run in production.

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * Demo service that encrypts a payment token using AES-GCM.
 * The scanner should detect the Cipher.getInstance usage below.
 */
public class PaymentService {

    private static final String TRANSFORMATION = "AES/GCM/NoPadding";

    public String encryptPaymentToken(String token) throws Exception {
        // Generate a fresh AES key for the demo.
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(256);
        SecretKey key = keyGen.generateKey();

        // <-- scanner detects this line: AES/GCM/NoPadding
        Cipher cipher = Cipher.getInstance(TRANSFORMATION);
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] encrypted = cipher.doFinal(token.getBytes(StandardCharsets.UTF_8));
        return Base64.getEncoder().encodeToString(encrypted);
    }
}