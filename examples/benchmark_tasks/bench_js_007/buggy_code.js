function safeAverage(values) {
  return values.reduce((total, value) => total + value, 0) / values.length;
}
module.exports = { safeAverage };
