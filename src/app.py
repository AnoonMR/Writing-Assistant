"""
app.py
------
Module 5: Flask Web UI -- full-scope version.

Live (debounced AJAX) interface tying together the tokenizer, spell
corrector (Noisy Channel + real confusion matrix, edit distance <= 2),
n-gram predictor (trigram with bigram backoff), and HMM POS tagger
(Viterbi). As the user types, the page calls a JSON API endpoint and
updates in place -- no full-page reload.

Usage:
    python app.py
    -> open http://127.0.0.1:5000 in a browser
"""

from flask import Flask, jsonify, render_template, request

from tokenizer import tokenize_words
from spell_corrector import SpellCorrector
from ngram_model import NgramModel
from pos_tagger import HMMPOSTagger

app = Flask(__name__)

print("Loading models (this runs once at startup)...")
spell_corrector = SpellCorrector()
ngram_model = NgramModel()
pos_tagger = HMMPOSTagger()
print("Models loaded. Ready.")


def analyze(text):
    words = tokenize_words(text)
    if not words:
        return None

    corrected_words, corrected_flags = spell_corrector.correct_text(words)
    tagged = pos_tagger.tag(corrected_words)

    last_tag = tagged[-1][1]
    expected_tag = pos_tagger.expected_next_tag(last_tag)

    prev_prev_word = corrected_words[-2] if len(corrected_words) >= 2 else None
    raw_suggestions = ngram_model.predict_next(
        corrected_words[-1], prev_prev_word=prev_prev_word, top_k=15
    )

    # POS-aware filter: prefer n-gram candidates whose most likely POS tag
    # matches what the HMM expects to follow the last word's tag.
    pos_matched = [
        (w, p) for w, p in raw_suggestions
        if pos_tagger.most_likely_tag(w) == expected_tag
    ]
    suggestions = (pos_matched or raw_suggestions)[:5]

    return {
        "tokens": [
            {"original": o, "corrected": c, "changed": f, "tag": t}
            for o, c, f, (_, t) in zip(words, corrected_words, corrected_flags, tagged)
        ],
        "suggestions": [{"word": w, "prob": p} for w, p in suggestions],
        "expected_tag": expected_tag,
        "corrected_text": " ".join(corrected_words),
        "used_trigram_context": prev_prev_word is not None,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    result = analyze(text)
    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True)
