// tests/fixtures/java/crypto_app.java
package com.demo;

import javax.crypto.Cipher;
import java.security.MessageDigest;
import java.security.KeyPairGenerator;

public class CryptoApp {

    public byte[] encrypt(String data) throws Exception {
        // RSA/ECB/PKCS1Padding encryption
        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        return new byte[0];
    }

    public byte[] hash(String data) throws Exception {
        // SHA-256 digest
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        return md.digest(data.getBytes());
    }

    public void genKeys() throws Exception {
        // RSA key generation
        KeyPairGenerator gen = KeyPairGenerator.getInstance("RSA");
    }
}