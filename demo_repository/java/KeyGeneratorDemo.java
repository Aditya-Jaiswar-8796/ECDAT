// demo_repository/java/KeyGeneratorDemo.java
//
// SAFE DEMO CODE - used only to demonstrate the ECDAT scanner during the
// SIH presentation. Never run in production.

import java.security.KeyPair;
import java.security.KeyPairGenerator;

/**
 * Demo that generates an RSA key pair.
 * The scanner should detect the KeyPairGenerator usage below.
 */
public class KeyGeneratorDemo {

    public static void main(String[] args) throws Exception {
        // <-- scanner detects this line: RSA key generation
        KeyPairGenerator keyPairGen = KeyPairGenerator.getInstance("RSA");
        keyPairGen.initialize(2048);
        KeyPair pair = keyPairGen.generateKeyPair();
        System.out.println("RSA key pair generated: " + pair.getPublic());
    }
}