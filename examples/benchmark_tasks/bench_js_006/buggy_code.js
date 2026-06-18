function topScores(scores, k) {
  return scores.slice().sort((a, b) => a - b).slice(0, k);
}
module.exports = { topScores };
