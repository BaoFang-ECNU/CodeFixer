function countWords(words) {
  const counts = {};
  for (const word of words) {
    counts[word] = 1;
  }
  return counts;
}
module.exports = { countWords };
