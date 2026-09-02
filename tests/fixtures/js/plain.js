// tests/fixtures/js/plain.js
function capitalize(text) {
    if (!text) return text;
    return text.charAt(0).toUpperCase() + text.slice(1);
}

const greeting = "hello world";

module.exports = { capitalize, greeting };