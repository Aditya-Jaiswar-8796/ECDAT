// demo_repository/javascript/formatting.js
//
// SAFE DEMO CODE - intentionally contains NO cryptographic usage.
// Used to demonstrate that the scanner correctly produces no findings
// for files with no crypto-related patterns.

function formatCurrency(amount, currency) {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: currency,
    }).format(amount);
}

function upperFirstLetter(word) {
    if (!word) return word;
    return word.charAt(0).toUpperCase() + word.slice(1);
}

module.exports = { formatCurrency, upperFirstLetter };