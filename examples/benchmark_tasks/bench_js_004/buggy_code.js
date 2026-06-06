function parseIntOrDefault(text, defaultValue = 0) {
  return Number.parseInt(text, 10);
}
module.exports = { parseIntOrDefault };
