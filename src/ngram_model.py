"""
ngram_model.py
--------------
Module 3: N-Gram Language Model -- full-scope version (bigram + trigram).

Trains both a bigram AND a trigram language model on the Brown Corpus
(already tokenized and cleaned in Activity 1), both with Laplace
(add-one) smoothing. Next-word prediction uses the trigram model when
the two-word context has been seen during training, and backs off to
the bigram model otherwise (simple backoff, consistent with how the
proposal describes combining bigram/trigram models with smoothing).

Usage:
    from ngram_model import NgramModel
    lm = NgramModel()
    lm.predict_next("the")                  -> top-k using bigram context
    lm.predict_next("the", "of")             -> top-k using trigram context "of the"
    lm.perplexity(held_out_sentences)        -> bigram perplexity
    lm.perplexity_trigram(held_out_sentences) -> trigram (w/ backoff) perplexity
"""

import json
import math
import os
from collections import Counter, defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

START = "<s>"
END = "</s>"


class NgramModel:
    def __init__(self, sentences_path=None, sentences=None):
        if sentences is not None:
            self.sentences = sentences
        else:
            sentences_path = sentences_path or os.path.join(DATA_DIR, "brown_sentences.json")
            with open(sentences_path, encoding="utf-8") as f:
                self.sentences = json.load(f)

        self.unigram_counts = Counter()
        self.bigram_counts = defaultdict(Counter)
        self.trigram_counts = defaultdict(Counter)
        self.vocab = set()

        self._train()

    def _train(self):
        # Pad with two <s> tokens so the trigram model has a well-defined
        # context at the very start of a sentence (standard practice).
        for sent in self.sentences:
            tokens = [START, START] + sent + [END]
            for w in tokens:
                self.unigram_counts[w] += 1
                self.vocab.add(w)
            for i in range(len(tokens) - 1):
                self.bigram_counts[tokens[i]][tokens[i + 1]] += 1
            for i in range(len(tokens) - 2):
                self.trigram_counts[(tokens[i], tokens[i + 1])][tokens[i + 2]] += 1

        self.V = len(self.vocab)

    def prob(self, prev_word, word):
        """Laplace-smoothed bigram P(word | prev_word)."""
        count_bigram = self.bigram_counts[prev_word][word]
        count_prev = self.unigram_counts[prev_word]
        return (count_bigram + 1) / (count_prev + self.V)

    def prob_trigram(self, w1, w2, word):
        """
        Laplace-smoothed trigram P(word | w1, w2), backing off to the
        bigram model P(word | w2) if the (w1, w2) context was never seen
        during training (so an unseen context doesn't just collapse to a
        uniform distribution over the whole vocabulary).
        """
        context_count = self.bigram_counts[w1][w2]
        if context_count == 0:
            return self.prob(w2, word)
        tri_count = self.trigram_counts[(w1, w2)][word]
        return (tri_count + 1) / (context_count + self.V)

    def predict_next(self, prev_word, prev_prev_word=None, top_k=5):
        """
        Return top-k (word, probability) candidates following prev_word.
        If prev_prev_word is given and the (prev_prev_word, prev_word)
        context was seen during training, uses the trigram distribution;
        otherwise falls back to the bigram distribution.
        """
        prev_word = prev_word.lower()

        if prev_word not in self.unigram_counts:
            # Unknown previous word: fall back to overall most frequent words.
            total = sum(self.unigram_counts.values())
            ranked = [(w, c) for w, c in self.unigram_counts.most_common() if w not in (START, END)]
            return [(w, c / total) for w, c in ranked[:top_k]]

        if prev_prev_word is not None:
            prev_prev_word = prev_prev_word.lower()
            context_count = self.bigram_counts[prev_prev_word][prev_word]
            if context_count > 0:
                candidates = self.trigram_counts[(prev_prev_word, prev_word)]
                if candidates:
                    scored = [
                        (w, self.prob_trigram(prev_prev_word, prev_word, w))
                        for w in candidates if w not in (START, END)
                    ]
                    if scored:
                        scored.sort(key=lambda x: -x[1])
                        return scored[:top_k]

        # Bigram fallback.
        candidates = self.bigram_counts[prev_word]
        if not candidates:
            return []
        scored = [(w, self.prob(prev_word, w)) for w in candidates if w not in (START, END)]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    def perplexity(self, held_out_sentences):
        """Bigram perplexity on a list of tokenized sentences."""
        log_prob_sum = 0.0
        n_tokens = 0
        for sent in held_out_sentences:
            tokens = [START] + sent + [END]
            for i in range(len(tokens) - 1):
                p = self.prob(tokens[i], tokens[i + 1])
                log_prob_sum += math.log(p)
                n_tokens += 1
        if n_tokens == 0:
            return float("inf")
        avg_log_prob = log_prob_sum / n_tokens
        return math.exp(-avg_log_prob)

    def perplexity_trigram(self, held_out_sentences):
        """Trigram-with-backoff perplexity on a list of tokenized sentences."""
        log_prob_sum = 0.0
        n_tokens = 0
        for sent in held_out_sentences:
            tokens = [START, START] + sent + [END]
            for i in range(len(tokens) - 2):
                p = self.prob_trigram(tokens[i], tokens[i + 1], tokens[i + 2])
                log_prob_sum += math.log(p)
                n_tokens += 1
        if n_tokens == 0:
            return float("inf")
        avg_log_prob = log_prob_sum / n_tokens
        return math.exp(-avg_log_prob)


if __name__ == "__main__":
    lm = NgramModel()
    print(f"Vocabulary size (incl. <s>/</s>): {lm.V:,}")
    for w in ["the", "he", "language", "zzqxnotaword"]:
        print(f"bigram next after {w!r}: {lm.predict_next(w)}")

    print(f"\ntrigram next after 'of the': {lm.predict_next('the', prev_prev_word='of')}")
    print(f"trigram next after 'he said': {lm.predict_next('said', prev_prev_word='he')}")

    test_sentences = lm.sentences[:500]
    print(f"\nBigram perplexity (first 500 train sentences):  {lm.perplexity(test_sentences):.2f}")
    print(f"Trigram perplexity (first 500 train sentences): {lm.perplexity_trigram(test_sentences):.2f}")
