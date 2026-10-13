"""
evaluate.py
-----------
Evaluation harness for Activity 2. Holds out 10% of the Brown Corpus as a
test set (not seen during training), then measures:

    1. Spell Corrector: top-1 correction accuracy on an auto-generated set
       of misspellings (each test word gets exactly one random edit applied).
    2. N-Gram LM: perplexity on held-out sentences.
    3. HMM POS Tagger: per-word tagging accuracy against gold Brown tags.

Also auto-generates the "custom evaluation set" (200 sentences with
induced spelling errors) called for in the proposal, instead of hand-
curating it.

Usage:
    python evaluate.py
"""

import json
import os
import random
import sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from ngram_model import NgramModel
from pos_tagger import HMMPOSTagger
from spell_corrector import SpellCorrector, _edits1_with_ops, _parse_spell_errors

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "report")
RANDOM_SEED = 42
TEST_FRACTION = 0.10
N_EVAL_SENTENCES = 200

random.seed(RANDOM_SEED)


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def train_test_split(data, test_fraction=TEST_FRACTION):
    indices = list(range(len(data)))
    random.Random(RANDOM_SEED).shuffle(indices)
    n_test = int(len(data) * test_fraction)
    test_idx = set(indices[:n_test])
    train = [d for i, d in enumerate(data) if i not in test_idx]
    test = [d for i, d in enumerate(data) if i in test_idx]
    return train, test


def introduce_typo(word):
    """Apply one random edit-distance-1 perturbation to a word."""
    if len(word) < 3:
        return None
    variants = list(_edits1_with_ops(word).keys())
    variants = [v for v in variants if v != word and v.isalpha()]
    if not variants:
        return None
    return random.choice(variants)


def generate_eval_sentences(test_sentences, n=N_EVAL_SENTENCES):
    """Build the 'custom evaluation set': n sentences with one induced typo each."""
    eval_set = []
    pool = [s for s in test_sentences if len(s) >= 4]
    random.shuffle(pool)
    for sent in pool:
        if len(eval_set) >= n:
            break
        word_idx = random.randrange(len(sent))
        typo = introduce_typo(sent[word_idx])
        if typo is None:
            continue
        noisy = sent.copy()
        noisy[word_idx] = typo
        eval_set.append({
            "original_sentence": sent,
            "noisy_sentence": noisy,
            "typo_index": word_idx,
            "original_word": sent[word_idx],
            "typo_word": typo,
        })
    return eval_set


def evaluate_spell_corrector(sc, eval_set):
    correct = 0
    for item in eval_set:
        prediction = sc.correct(item["typo_word"])
        if prediction == item["original_word"]:
            correct += 1
    accuracy = correct / len(eval_set) if eval_set else 0.0
    return accuracy, correct, len(eval_set)


def evaluate_spell_corrector_real_world(sc, held_out_pairs, max_pairs=500):
    """
    Evaluate on a held-out slice of REAL human misspellings (from
    data/raw/spell-errors.txt), rather than synthetic induced typos --
    a stronger, more honest test since the confusion matrix itself was
    trained on a different slice of this same corpus.
    """
    sample = held_out_pairs[:max_pairs]
    correct = 0
    for correct_word, misspelling, _count in sample:
        if sc.correct(misspelling) == correct_word:
            correct += 1
    accuracy = correct / len(sample) if sample else 0.0
    return accuracy, correct, len(sample)


def evaluate_pos_tagger(tagger, test_tagged_sentences, max_sentences=500):
    sample = test_tagged_sentences[:max_sentences]
    correct, total = 0, 0
    confusion = defaultdict(Counter)  # confusion[gold_tag][predicted_tag] = count
    for sent in sample:
        if not sent:
            continue
        words = [w for w, _ in sent]
        gold_tags = [t for _, t in sent]
        pred_tags = [t for _, t in tagger.tag(words)]
        for g, p in zip(gold_tags, pred_tags):
            total += 1
            confusion[g][p] += 1
            if g == p:
                correct += 1
    return (correct / total if total else 0.0), correct, total, confusion


def save_confusion_matrix(confusion, tags, out_dir):
    import csv

    csv_path = os.path.join(out_dir, "pos_confusion_matrix.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["gold\\pred"] + tags)
        for g in tags:
            writer.writerow([g] + [confusion[g][p] for p in tags])
    print(f"      Saved: {csv_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        matrix = np.array([[confusion[g][p] for p in tags] for g in tags])
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        normalized = matrix / row_sums

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(normalized, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(len(tags)))
        ax.set_yticks(range(len(tags)))
        ax.set_xticklabels(tags, rotation=45, ha="right")
        ax.set_yticklabels(tags)
        ax.set_xlabel("Predicted tag")
        ax.set_ylabel("Gold tag")
        ax.set_title("POS Tagger Confusion Matrix (row-normalized)")
        for i in range(len(tags)):
            for j in range(len(tags)):
                if matrix[i, j] > 0:
                    ax.text(j, i, str(matrix[i, j]), ha="center", va="center",
                            fontsize=7, color="white" if normalized[i, j] > 0.5 else "black")
        fig.colorbar(im, ax=ax, label="Proportion of gold tag")
        fig.tight_layout()

        png_path = os.path.join(out_dir, "pos_confusion_matrix.png")
        fig.savefig(png_path, dpi=150)
        plt.close(fig)
        print(f"      Saved: {png_path}")
    except ImportError:
        print("      matplotlib not available — skipped confusion matrix plot (CSV still saved).")


def main():
    print("=" * 60)
    print("  Activity 2 — Model Evaluation")
    print("=" * 60)

    print("\n[1/4] Loading data and splitting train/test (90/10)...")
    brown_sentences = load_json("brown_sentences.json")
    pos_tagged_sentences = load_json("pos_tagged_sentences.json")

    lm_train, lm_test = train_test_split(brown_sentences)
    pos_train, pos_test = train_test_split(pos_tagged_sentences)
    print(f"      LM: {len(lm_train):,} train / {len(lm_test):,} test sentences")
    print(f"      POS: {len(pos_train):,} train / {len(pos_test):,} test sentences")

    spell_errors_path = os.path.join(DATA_DIR, "raw", "spell-errors.txt")
    all_misspelling_pairs = _parse_spell_errors(spell_errors_path)
    misspelling_train, misspelling_test = train_test_split(all_misspelling_pairs)
    print(f"      Misspelling corpus: {len(misspelling_train):,} train / "
          f"{len(misspelling_test):,} test pairs")

    print("\n[2/4] Training models on train split only...")
    lm = NgramModel(sentences=lm_train)
    tagger = HMMPOSTagger(tagged_sentences=pos_train)
    sc = SpellCorrector(confusion_pairs=misspelling_train)  # vocabulary from full Activity 1 corpus
    print(f"      Confusion matrix: {sc.confusion.used_pairs:,} single-edit pairs used "
          f"(of {sc.confusion.total_pairs:,} train pairs)")
    print("      Done.")

    print(f"\n[3/4] Generating {N_EVAL_SENTENCES} evaluation sentences with induced typos...")
    eval_set = generate_eval_sentences(lm_test, n=N_EVAL_SENTENCES)
    os.makedirs(REPORT_DIR, exist_ok=True)
    eval_set_path = os.path.join(REPORT_DIR, "evaluation_set.json")
    with open(eval_set_path, "w", encoding="utf-8") as f:
        json.dump(eval_set, f, indent=2)
    print(f"      Saved {len(eval_set)} sentences to {eval_set_path}")

    print("\n[4/4] Running evaluation...")
    spell_acc, spell_correct, spell_total = evaluate_spell_corrector(sc, eval_set)
    real_acc, real_correct, real_total = evaluate_spell_corrector_real_world(sc, misspelling_test)
    bigram_perplexity = lm.perplexity(lm_test)
    trigram_perplexity = lm.perplexity_trigram(lm_test)
    pos_acc, pos_correct, pos_total, confusion = evaluate_pos_tagger(tagger, pos_test)
    save_confusion_matrix(confusion, tagger.tags, REPORT_DIR)

    results = {
        "spell_corrector": {
            "top1_accuracy_synthetic_typos": round(spell_acc, 4),
            "correct": spell_correct,
            "total": spell_total,
            "top1_accuracy_real_world_misspellings": round(real_acc, 4),
            "real_world_correct": real_correct,
            "real_world_total": real_total,
            "confusion_matrix_train_pairs": sc.confusion.used_pairs,
        },
        "ngram_lm": {
            "bigram_perplexity_on_held_out": round(bigram_perplexity, 2),
            "trigram_perplexity_on_held_out": round(trigram_perplexity, 2),
            "test_sentences": len(lm_test),
        },
        "pos_tagger": {
            "word_accuracy": round(pos_acc, 4),
            "correct_tags": pos_correct,
            "total_tags": pos_total,
        },
    }

    results_path = os.path.join(REPORT_DIR, "evaluation_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("  Results")
    print("=" * 60)
    print(f"  Spell Corrector top-1 (synthetic typos)    : {spell_acc:.2%} ({spell_correct}/{spell_total})")
    print(f"  Spell Corrector top-1 (real misspellings)  : {real_acc:.2%} ({real_correct}/{real_total})")
    print(f"  N-Gram LM bigram perplexity (held-out)     : {bigram_perplexity:.2f}")
    print(f"  N-Gram LM trigram perplexity (held-out)    : {trigram_perplexity:.2f}")
    print(f"  POS Tagger word accuracy                   : {pos_acc:.2%} ({pos_correct}/{pos_total})")
    print(f"\n  Saved: {results_path}")
    print(f"  Saved: {eval_set_path}")


if __name__ == "__main__":
    main()
