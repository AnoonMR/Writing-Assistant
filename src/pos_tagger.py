"""
pos_tagger.py
-------------
Module 4: HMM POS Tagger with Viterbi Decoding.

Trains a bigram Hidden Markov Model on the POS-tagged Brown Corpus
(Universal tagset, cleaned in Activity 1):
    - Transition probabilities A: P(tag_t | tag_{t-1})
    - Emission probabilities B:   P(word | tag)
    - Initial probabilities pi:   P(tag at sentence start)

The Viterbi algorithm then decodes the most likely tag sequence for an
input sentence. Add-one (Laplace) smoothing is applied throughout so
unseen words/transitions get a small non-zero probability instead of
breaking the product to 0.

Usage:
    from pos_tagger import HMMPOSTagger
    tagger = HMMPOSTagger()
    tagger.tag(["the", "dog", "runs"])  -> [("the","DET"), ("dog","NOUN"), ("runs","VERB")]
"""

import json
import os
from collections import Counter, defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class HMMPOSTagger:
    def __init__(self, tagged_sentences_path=None, tagged_sentences=None):
        if tagged_sentences is not None:
            self.tagged_sentences = tagged_sentences
        else:
            tagged_sentences_path = tagged_sentences_path or os.path.join(
                DATA_DIR, "pos_tagged_sentences.json"
            )
            with open(tagged_sentences_path, encoding="utf-8") as f:
                self.tagged_sentences = json.load(f)

        self.tags = set()
        self.initial_counts = Counter()
        self.transition_counts = defaultdict(Counter)
        self.emission_counts = defaultdict(Counter)
        self.tag_totals = Counter()

        self._train()

    def _train(self):
        for sent in self.tagged_sentences:
            if not sent:
                continue
            first_word, first_tag = sent[0]
            self.initial_counts[first_tag] += 1

            prev_tag = None
            for word, tag in sent:
                self.tags.add(tag)
                self.emission_counts[tag][word] += 1
                self.tag_totals[tag] += 1
                if prev_tag is not None:
                    self.transition_counts[prev_tag][tag] += 1
                prev_tag = tag

        self.tags = sorted(self.tags)
        self.n_tags = len(self.tags)
        self.n_sentences = len(self.tagged_sentences)

    def _initial_prob(self, tag):
        return (self.initial_counts[tag] + 1) / (self.n_sentences + self.n_tags)

    def _transition_prob(self, prev_tag, tag):
        total = sum(self.transition_counts[prev_tag].values())
        return (self.transition_counts[prev_tag][tag] + 1) / (total + self.n_tags)

    def _emission_prob(self, tag, word):
        vocab_size = len(self.emission_counts[tag]) or 1
        return (self.emission_counts[tag][word] + 1) / (self.tag_totals[tag] + vocab_size)

    def tag(self, words):
        """Viterbi decoding: return [(word, tag), ...] for the input word list."""
        if not words:
            return []

        n = len(words)
        viterbi = [dict() for _ in range(n)]
        backpointer = [dict() for _ in range(n)]

        for t in self.tags:
            viterbi[0][t] = self._initial_prob(t) * self._emission_prob(t, words[0])
            backpointer[0][t] = None

        for i in range(1, n):
            for t in self.tags:
                best_prob, best_prev = -1.0, None
                emission = self._emission_prob(t, words[i])
                for prev_t in self.tags:
                    prob = viterbi[i - 1][prev_t] * self._transition_prob(prev_t, t) * emission
                    if prob > best_prob:
                        best_prob, best_prev = prob, prev_t
                viterbi[i][t] = best_prob
                backpointer[i][t] = best_prev

        best_last_tag = max(self.tags, key=lambda t: viterbi[n - 1][t])

        tags_seq = [best_last_tag]
        for i in range(n - 1, 0, -1):
            tags_seq.append(backpointer[i][tags_seq[-1]])
        tags_seq.reverse()

        return list(zip(words, tags_seq))

    def expected_next_tag(self, prev_tag):
        """Most likely POS tag to follow prev_tag, via the transition model."""
        return max(self.tags, key=lambda t: self._transition_prob(prev_tag, t))

    def most_likely_tag(self, word):
        """Most likely POS tag for a word, via P(tag | word) ~= P(word | tag) * P(tag)."""
        total_tagged = sum(self.tag_totals.values())
        best_tag, best_score = None, -1.0
        for t in self.tags:
            prior = self.tag_totals[t] / total_tagged
            score = self._emission_prob(t, word) * prior
            if score > best_score:
                best_score, best_tag = score, t
        return best_tag


if __name__ == "__main__":
    tagger = HMMPOSTagger()
    print(f"Tags learned ({tagger.n_tags}): {tagger.tags}")

    tests = [
        ["the", "dog", "runs", "fast"],
        ["she", "sells", "sea", "shells"],
        ["he", "said", "that", "the", "election", "was", "fair"],
    ]
    for words in tests:
        print(words, "->", tagger.tag(words))
