// tests/fixtures/java/malformed.java
// A deliberately broken Java file: unclosed braces, unterminated strings and
// some invalid bytes. The scanner must survive it without crashing.
package com.demo;

public class Malformed {
    public void broken() {
        String s = "unterminated
        Cipher cipher = Cipher.getInstance("AES");   // AES usage
        int[] arr = {1, 2, 3;
    }