"""
spell_corrector.py
-------------------
Module 2: Spelling Corrector (Noisy Channel Model + Edit Distance) --
full-scope version.

Candidate generation: edit-distance-1 AND edit-distance-2 variants of a
misspelled word (insertion, deletion, substitution, transposition),
filtered against the known vocabulary (edit-distance-2 candidates are
only generated from edit-distance-1 forms that aren't themselves real
words, following the standard approach).

Candidate ranking: P(correction | misspelling) ~= P(correction) * P(misspelling | correction),
exactly as described in Kernighan, Church & Gale (1990). P(correction) is
the Laplace-smoothed unigram prior from the Brown Corpus vocabulary.
P(misspelling | correction) -- the channel model -- is no longer a fixed
per-edit-type weight; it is learned from data/raw/spell-errors.txt, a
corpus of ~7,800 real correct-word -> misspelling pairs, by building the
classic del/ins/sub/trans confusion matrices (Kernighan et al., 1990;
Jurafsky & Martin, 2024, Ch. 2) and normalizing them into probabilities
over specific character contexts, rather than generic edit-type weights.

Usage:
    from spell_corrector import SpellCorrector
    sc = SpellCorrector()
    sc.correct("teh")  -> "the"
"""

import json
import os
import re
import string
from collections import Counter, defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LETTERS = string.ascii_lowercase

# Activity 1's preprocessing dropped tokens shorter than 2 characters when
# building the vocabulary (see preprocess.py:is_valid_token), so valid
# single-letter words like "I"/"a" are otherwise never recognized as known.
EXTRA_KNOWN_WORDS = {"i", "a"}

START_SYM = "<"  # synthetic "start of word" context symbol for del/ins at position 0


# ---------------------------------------------------------------------------
# Confusion matrix: learned from real correct -> misspelling pairs.
# ---------------------------------------------------------------------------

def _min_edit_alignment(a, b):
    """
    Classic DP edit-distance alignment between strings a (correct) and
    b (misspelling), returning the list of single-character edit
    operations needed to turn a into b, as (op, x, y) tuples:
        ("del", x, y)   -- a has "...x y..." but b has "...x...": y was deleted after x
        ("ins", x, y)   -- a has "...x..." but b has "...x y...": y was inserted after x
        ("sub", x, y)   -- a has x at a position where b has y: x substituted by y
        ("trans", x, y) -- a has "...x y..." but b has "...y x...": x,y transposed
    Returns None if a and b are not within edit distance 1 of each other
    (this project's confusion matrix is trained only on true single-edit
    pairs, following Kernighan et al., 1990 and the ~80%-single-error
    finding of Damerau, 1964).
    """
    if a == b:
        return []

    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return None

    # Find the first index where a and b differ.
    i = 0
    while i < min(la, lb) and a[i] == b[i]:
        i += 1

    if la == lb:
        # Substitution, or a transposition of two adjacent characters.
        if i + 1 < la and a[i] == b[i + 1] and a[i + 1] == b[i] and a[i + 2:] == b[i + 2:]:
            return [("trans", a[i], a[i + 1])]
        if a[i + 1:] == b[i + 1:]:
            return [("sub", a[i], b[i])]
        return None

    if la == lb + 1:
        # b is missing one character from a: a deletion error (a[i] was deleted).
        if a[i + 1:] == b[i:]:
            x = a[i - 1] if i > 0 else START_SYM
            return [("del", x, a[i])]
        return None

    if lb == la + 1:
        # b has one extra character versus a: an insertion error (b[i] was inserted).
        if a[i:] == b[i + 1:]:
            x = a[i - 1] if i > 0 else START_SYM
            return [("ins", x, b[i])]
        return None

    return None


def _parse_spell_errors(path):
    """Parse data/raw/spell-errors.txt into (correct, misspelling, count) triples."""
    pairs = []
    if not os.path.exists(path):
        return pairs
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            correct, rest = line.split(":", 1)
            correct = correct.strip().lower()
            if not correct.isalpha():
                continue
            for token in rest.split(","):
                token = token.strip()
                if not token:
                    continue
                m = re.match(r"^([a-zA-Z']+)(?:\*(\d+))?$", token)
                if not m:
                    continue
                misspelling = m.group(1).lower()
                count = int(m.group(2)) if m.group(2) else 1
                if misspelling.isalpha():
                    pairs.append((correct, misspelling, count))
    return pairs


class ConfusionMatrix:
    """Learned del/ins/sub/trans confusion counts, normalized to probabilities."""

    def __init__(self, spell_errors_path=None, pairs=None):
        if pairs is None:
            spell_errors_path = spell_errors_path or os.path.join(DATA_DIR, "raw", "spell-errors.txt")
            pairs = _parse_spell_errors(spell_errors_path)

        self.counts = {"del": defaultdict(int), "ins": defaultdict(int),
                        "sub": defaultdict(int), "trans": defaultdict(int)}
        self.context_totals = {"del": defaultdict(int), "ins": defaultdict(int),
                                "sub": defaultdict(int), "trans": defaultdict(int)}

        skipped_multi_edit = 0
        used_pairs = 0
        for correct, misspelling, count in pairs:
            ops = _min_edit_alignment(correct, misspelling)
            if ops is None:
                skipped_multi_edit += 1
                continue
            for op, x, y in ops:
                self.counts[op][(x, y)] += count
                self.context_totals[op][x] += count
            used_pairs += 1

        self.used_pairs = used_pairs
        self.skipped_multi_edit = skipped_multi_edit
        self.total_pairs = len(pairs)

    def prob(self, op, x, y):
        """P(this specific edit | context x), with Laplace smoothing so an
        unseen (x, y) pair still gets a small non-zero probability rather
        than being ruled out entirely."""
        count = self.counts[op][(x, y)]
        total = self.context_totals[op][x]
        # Smoothing denominator uses len(LETTERS) as a rough alphabet-size prior.
        return (count + 1) / (total + len(LETTERS))


# ---------------------------------------------------------------------------
# Candidate generation (edit distance 1 and 2), each tagged with the exact
# edit operation (and characters) needed to go from the CANDIDATE (assumed
# correct) to the INPUT word (the typo) -- i.e. the channel direction.
# ---------------------------------------------------------------------------

def _edits1_with_ops(word):
    """
    All edit-distance-1 strings reachable from `word`, each tagged with the
    (op, x, y) describing the edit applied to `word` to PRODUCE that string.
    (When later scoring a candidate as the assumed-correct word, this is
    exactly the correct->typo edit needed for the channel model.)
    """
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    out = {}

    for left, right in splits:
        if right:
            x = left[-1] if left else START_SYM
            out[left + right[1:]] = ("del", x, right[0])
    for left, right in splits:
        if len(right) > 1:
            out[left + right[1] + right[0] + right[2:]] = ("trans", right[0], right[1])
    for left, right in splits:
        if right:
            for c in LETTERS:
                if c != right[0]:
                    out[left + c + right[1:]] = ("sub", c, right[0])
    for left, right in splits:
        x = left[-1] if left else START_SYM
        for c in LETTERS:
            out[left + c + right] = ("ins", x, c)

    return out


class SpellCorrector:
    def __init__(self, vocab_path=None, spell_errors_path=None, confusion_pairs=None,
                 max_edit_distance=2):
        vocab_path = vocab_path or os.path.join(DATA_DIR, "vocabulary.json")
        with open(vocab_path, encoding="utf-8") as f:
            self.vocab = json.load(f)
        self.total = sum(self.vocab.values())
        self.max_edit_distance = max_edit_distance
        self.confusion = ConfusionMatrix(spell_errors_path, pairs=confusion_pairs)

    def is_known(self, word):
        return word in self.vocab or word in EXTRA_KNOWN_WORDS

    def _prior(self, word):
        return (self.vocab.get(word, 0) + 1) / (self.total + len(self.vocab))

    def _channel_prob(self, ops):
        """Combined channel probability for a (possibly chained, for
        edit-distance-2 candidates) list of edit operations."""
        p = 1.0
        for op, x, y in ops:
            p *= self.confusion.prob(op, x, y)
        return p

    def candidates(self, word, top_k=5):
        """Return up to top_k (candidate, score) pairs for a misspelled word."""
        if self.is_known(word):
            return [(word, 1.0)]

        scored = {}

        # Edit distance 1.
        edits1 = _edits1_with_ops(word)
        for variant, (op, x, y) in edits1.items():
            if variant in self.vocab:
                score = self._prior(variant) * self._channel_prob([(op, x, y)])
                scored[variant] = max(scored.get(variant, 0.0), score)

        # Edit distance 2: chain a second edit onto each edit-distance-1
        # form, but only explore from forms that aren't already real words
        # (standard optimization -- a real word one edit away is already
        # captured above with a higher, single-edit-attributed score).
        if self.max_edit_distance >= 2:
            for mid_variant, (op1, x1, y1) in edits1.items():
                if mid_variant in self.vocab:
                    continue
                edits2 = _edits1_with_ops(mid_variant)
                for variant, (op2, x2, y2) in edits2.items():
                    if variant in self.vocab and variant not in scored:
                        score = self._prior(variant) * self._channel_prob(
                            [(op1, x1, y1), (op2, x2, y2)]
                        )
                        scored[variant] = max(scored.get(variant, 0.0), score)

        if not scored:
            return [(word, 0.0)]

        ranked = sorted(scored.items(), key=lambda kv: -kv[1])
        return ranked[:top_k]

    def correct(self, word):
        """Return the single best correction for a word."""
        return self.candidates(word, top_k=1)[0][0]

    def correct_text(self, words):
        """Correct a list of tokens, returning (corrected_words, flags) where
        flags[i] is True if word i was changed."""
        corrected, flags = [], []
        for w in words:
            c = self.correct(w)
            corrected.append(c)
            flags.append(c != w)
        return corrected, flags


if __name__ == "__main__":
    sc = SpellCorrector()
    print(f"Confusion matrix trained on {sc.confusion.used_pairs:,} single-edit pairs "
          f"(skipped {sc.confusion.skipped_multi_edit:,} multi-edit pairs out of "
          f"{sc.confusion.total_pairs:,} total).")
    tests = ["teh", "recieve", "langauge", "wrok", "helo", "wht", "ovr", "the"]
    for t in tests:
        print(f"{t!r:12} -> {sc.correct(t)!r:12}  candidates: {sc.candidates(t)}")
