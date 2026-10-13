# Activity 2 — NLP-Based Intelligent Writing Assistant

Phase 2 implementation: five modules that turn the Activity 1 preprocessed
data into a working writing assistant, plus evaluation and reporting.
Full-scope version — bigram + trigram LM, edit-distance-≤2 spell
correction with a real learned confusion matrix, and a live dark-themed
web UI.

**Report:** [`report/main.pdf`](report/main.pdf) ·
**Slides:** [`report/Activity_2_Presentation.pptx`](report/Activity_2_Presentation.pptx) ·
**Activity 1 (dataset download + preprocessing):** [AnoonMR/nlp-a1](https://github.com/AnoonMR/nlp-a1)

## Setup

```bash
pip install -r requirements.txt
```

No internet connection needed to run this — all data (`data/*.json`,
`data/raw/spell-errors.txt`) was already downloaded in Activity 1 /
during development and is included here.

## Run the web app

```bash
cd src
python app.py
```

Open http://127.0.0.1:5000 in a browser. Just start typing (try a sentence
with typos, e.g. "Teh quick brown fox jumpd ovr the lazy dog") — results
update live as you type, no button click needed.

## Run evaluation

```bash
cd src
python evaluate.py
```

Trains on a 90% split, evaluates on the held-out 10%, and writes
`report/evaluation_results.json` and `report/evaluation_set.json` (the
auto-generated 200-sentence test set with induced typos).

## Modules (`src/`)

| File | Module | Notes |
|---|---|---|
| `tokenizer.py` | Tokenizer | Regex-based sentence/word splitting |
| `spell_corrector.py` | Spell Corrector | Noisy Channel + Edit Distance (≤2); channel probabilities learned from a real confusion matrix built from `data/raw/spell-errors.txt` (~7,800 real correct→misspelling pairs), not fixed weights |
| `ngram_model.py` | N-Gram LM | Bigram + trigram (with backoff to bigram for unseen contexts), Laplace smoothing, next-word prediction, perplexity |
| `pos_tagger.py` | HMM POS Tagger | Bigram HMM + Viterbi decoding, trained on Universal-tagset Brown Corpus |
| `app.py` + `templates/index.html` | Web UI | Flask app + JSON API, live debounced AJAX updates (no page reload), dark theme, POS-aware suggestion filtering |
| `evaluate.py` | Evaluation harness | Train/test split (Brown Corpus + misspelling corpus), spell accuracy (synthetic + real-world), bigram/trigram perplexity, POS accuracy, POS confusion matrix |

## Results (last run — see `report/evaluation_results.json` for latest)

| Metric | Value |
|---|---|
| Spell Corrector top-1 accuracy (synthetic typos) | 76.00% (152/200) |
| Spell Corrector top-1 accuracy (real-world misspellings, held-out) | 38.00% (190/500) |
| N-Gram LM bigram perplexity (held-out) | 5595.97 |
| N-Gram LM trigram perplexity (held-out, with backoff) | 13641.36 |
| POS Tagger word accuracy | 91.74% (8242/8984) |

**Honest note on the spell-correction numbers:** the real confusion matrix
directly fixed two specific failures found during manual testing
("wht"→"who" instead of "what"; "ovr"→"or" instead of "over" — both now
correct). However, overall *synthetic*-typo accuracy actually dropped
versus the earlier fixed-weight model (was 85.5%). This isn't a bug: the
learned confusion matrix is sparse (~12K single-edit training pairs spread
across ~2,700 possible character/operation combinations), so it performs
best on realistic typo patterns and can be noisier than a simple universal
heuristic on uniformly-random synthetic edits that don't reflect real
human error patterns. The new **real-world accuracy metric (38%)**,
tested directly against held-out genuine human misspellings, is the more
rigorous and honest number — and a meaningful share of that test set
requires edit distance >2, which this system intentionally doesn't
attempt (see Known limitations).

## Known limitations

- Activity 1's preprocessing filtered out tokens shorter than 2 characters,
  so single-letter words (e.g. "I", "a") never appear in the spell-corrector
  vocabulary or the POS tagger's emission counts. The spell corrector special-
  cases "i"/"a" as always-known; the POS tagger handles them correctly anyway
  via smoothing + transition context (see `pos_tagger.py`).
- The n-gram LM uses full Laplace smoothing over a ~40K-word vocabulary.
  This inflates perplexity for both bigram and (even more so) trigram —
  trigram perplexity is actually *higher* than bigram, because Laplace
  smoothing adds the full vocabulary size to every denominator regardless
  of how frequent the specific context is, which disproportionately
  penalizes the sparser trigram contexts. This is a well-documented
  weakness of add-one smoothing (Chen & Goodman, 1999), not an
  implementation bug — see the report's Error Analysis chapter.
- Spell correction candidates go up to edit distance 2, but roughly 64% of
  the real misspelling corpus requires more edits than that (or isn't a
  pure typo at all, e.g. a stylistic alternate spelling), which is the
  main reason the real-world accuracy number isn't higher.
