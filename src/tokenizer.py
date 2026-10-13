"""
tokenizer.py
------------
Module 1: Tokenizer.

Splits raw input text into sentences and then into word tokens, handling
punctuation and contractions with regex-based rules (per Unit 1 of the
course syllabus).

Usage:
    from tokenizer import tokenize_sentences, tokenize_words
"""

import re

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")


def tokenize_sentences(text):
    """Split raw text into a list of sentence strings."""
    text = text.strip()
    if not text:
        return []
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]


def tokenize_words(sentence):
    """Split a sentence into lowercase word tokens, keeping contractions intact."""
    return [w.lower() for w in WORD_RE.findall(sentence)]


def tokenize(text):
    """Tokenize raw text into a list of sentences, each a list of word tokens."""
    return [tokenize_words(s) for s in tokenize_sentences(text)]


if __name__ == "__main__":
    sample = "Mr. Smith isn't going. He said he'll arrive by 5pm!"
    for sent in tokenize_sentences(sample):
        print(sent, "->", tokenize_words(sent))
