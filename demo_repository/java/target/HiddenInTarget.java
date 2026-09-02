// dummy file INSIDE the ignored "target" directory.
// This exists ONLY to prove that the scanner skips ignored directories.
// The scanner must never find this file.

import javax.crypto.Cipher;

public class ShouldNeverBeFound {
    public void hidden() throws Exception {
        Cipher c = Cipher.getInstance("RSA");
        System.out.println(c);
    }
}