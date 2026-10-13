"""
One-off script: fills the Activity 2 PPT template with real project
content, keeping the template's fonts/colours/spacing, and inserts the
real workflow diagram, confusion matrix and app screenshot.

Layout rules this script enforces (so nothing spills off a slide):
  * every bullet paragraph gets a copy of the template's own paragraph
    properties (font size, colour, spacing) plus a bullet marker -- the
    template keeps these on the paragraph, not the run, so new paragraphs
    would otherwise fall back to PowerPoint's default style;
  * images are scaled to fit inside a target box with their aspect ratio
    preserved (never stretched), and centred in that box;
  * all content stays above the footer line (y < 6.9 in).

Run from the report/ folder:  python fill_ppt.py
"""
import copy
import json
import re

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

TEMPLATE = "../template/Activity_2_Research_Presentation_Template.pptx"
OUTPUT = "Activity_2_Presentation.pptx"
GITHUB_URL = "https://github.com/AnoonMR/Writing-Assistant"

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
DARK = RGBColor(0x2D, 0x2D, 0x2D)
NAVY = RGBColor(0x1F, 0x37, 0x50)

with open("evaluation_results.json", encoding="utf-8") as f:
    R = json.load(f)
SPELL, LM, POS = R["spell_corrector"], R["ngram_lm"], R["pos_tagger"]

prs = Presentation(TEMPLATE)
slides = list(prs.slides)


def find_shape(slide, name):
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    return None


def set_bullets(shape, bullets, size=18, bullet=True):
    """Replace a text box's paragraphs with `bullets`, giving every
    paragraph a copy of the template's first-paragraph properties."""
    tf = shape.text_frame
    template_ppr = tf.paragraphs[0]._p.find(A + "pPr")
    tf.clear()
    for i, text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        old = p._p.find(A + "pPr")
        if old is not None:
            p._p.remove(old)
        if template_ppr is not None:
            ppr = copy.deepcopy(template_ppr)
            p._p.insert(0, ppr)
            defrpr = ppr.find(A + "defRPr")
            if defrpr is not None:
                defrpr.set("sz", str(size * 100))
            if bullet:
                ppr.set("marL", "342900")
                ppr.set("indent", "-342900")
                bu_font = etree.Element(A + "buFont", typeface="Arial")
                bu_char = etree.Element(A + "buChar", char="•")
                anchor = defrpr if defrpr is not None else None
                if anchor is not None:
                    anchor.addprevious(bu_font)
                    anchor.addprevious(bu_char)
                else:
                    ppr.append(bu_font)
                    ppr.append(bu_char)
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.name = "Arial"
        run.font.color.rgb = DARK


def clear_text(shape):
    set_bullets(shape, [""], bullet=False)


def add_picture_fit(slide, path, left, top, max_w, max_h):
    """Insert a picture scaled to fit (left, top, max_w, max_h) inches,
    aspect ratio preserved, centred in that box."""
    w_px, h_px = Image.open(path).size
    scale = min(max_w / w_px, max_h / h_px)
    w, h = w_px * scale, h_px * scale
    x = left + (max_w - w) / 2
    y = top + (max_h - h) / 2
    return slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h))


def remove_shape(slide, name):
    shape = find_shape(slide, name)
    if shape is not None:
        shape._element.getparent().remove(shape._element)


def resize(shape, left=None, top=None, width=None, height=None):
    if left is not None:
        shape.left = Inches(left)
    if top is not None:
        shape.top = Inches(top)
    if width is not None:
        shape.width = Inches(width)
    if height is not None:
        shape.height = Inches(height)


def pct(x):
    return f"{x * 100:.2f}%"


# ---------------------------------------------------------------- Slide 1: Cover
s = slides[0]
tb1 = find_shape(s, "TextBox 1")
# The full title is too long for one line at the template's 23 pt, and this
# box doesn't wrap -- split it over two lines with a line break.
tb1.text_frame.paragraphs[2].text = (
    "NLP-Based Intelligent Writing Assistant:\v"
    "Autocorrect, Autocomplete, and POS-Aware Suggestions"
)
tb3 = find_shape(s, "TextBox 3")
tb3.text_frame.paragraphs[0].runs[0].text = "Team Name: SyntaxSquad"
tb3.text_frame.paragraphs[1].runs[0].text = "Student Names and USNs: Anoon M R; [Member 2]; [Member 3]"
tb3.text_frame.paragraphs[2].runs[0].text = "Department of MCA | JAIN (Deemed-to-be University)"
tb3.text_frame.paragraphs[3].runs[0].text = "Faculty: Dr. Sharal Coelho | Date: [DD/MM/YYYY]"

# ---------------------------------------------------------------- Slide 2: Title recap
s = slides[1]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "NLP-Based Intelligent Writing Assistant: Autocorrect, Autocomplete, and POS-Aware Suggestions",
    "Team: SyntaxSquad | Course: Natural Language Processing (25MCAAI303)",
    "MCA - AIML, JAIN (Deemed-to-be University) | Faculty: Dr. Sharal Coelho",
], size=20)

# ---------------------------------------------------------------- Slide 3: Introduction
s = slides[2]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Background: a writing assistant built from scratch in Python - spell correction, "
    "next-word prediction and POS-aware suggestions",
    "Problem: spell checkers ignore real error patterns; autocomplete ignores grammar",
    "Why it matters: email, messages and academic writing all suffer from "
    "context-blind corrections and ungrammatical suggestions",
    "Objectives: tokenizer, Noisy Channel spell corrector (learned confusion matrix, "
    "edit distance ≤ 2), bigram + trigram LM, HMM + Viterbi POS tagger, live Flask UI",
])

# ---------------------------------------------------------------- Slide 4: Literature Survey
s = slides[3]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Damerau (1964), CACM - ~80% of real typos are a single edit",
    "Kernighan, Church & Gale (1990), COLING - Noisy Channel spelling correction with "
    "learned confusion matrices (the basis of our spell corrector)",
    "Church (1988), ANLP - HMM-style POS tagger on the Brown Corpus, 95-99% accuracy",
    "Viterbi (1967), IEEE Trans. Info. Theory - the decoding algorithm our tagger uses",
    "Chen & Goodman (1999), CSL - smoothing survey; explains our perplexity results",
    "Gap: these are usually studied in isolation - we let the HMM filter the "
    "N-gram LM's suggestions in real time",
], size=17)

# ---------------------------------------------------------------- Slide 5: Methodology
s = slides[4]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Spell Corrector: candidates within edit distance 2, ranked by P(word) × P(typo | word); "
    "P(typo | word) learned from 12,356 real single-edit misspellings",
    "N-Gram LM: trigram with back-off to bigram, Laplace smoothing",
    "HMM POS Tagger: bigram HMM, Viterbi decoding, 10 Universal POS tags",
    "POS-aware filter: keep only next-word candidates whose tag matches the tag the HMM expects next",
], size=17)
add_picture_fit(s, "assets/system_workflow.png", 1.0, 4.75, 11.3, 2.1)

# ---------------------------------------------------------------- Slide 6: Dataset & Setup
s = slides[5]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Brown Corpus (NLTK): 54,286 cleaned sentences, 24,891-word vocabulary (freq ≥ 2)",
    "POS data: 54,270 Universal-tagset sentences, 10 tag classes",
    "Misspelling corpus (Norvig): 7,841 words, 38,218 real (correct, misspelling) pairs",
    "Preprocessing (Activity 1): lowercasing, punctuation stripping, tokenization, length filtering",
    "90% / 10% train/test split (seed 42) on all three datasets - every score is on unseen data",
    "Tools: Python 3.12, Flask 3.1.3, matplotlib - no GPU needed",
])

# ---------------------------------------------------------------- Slide 7: Results
s = slides[6]
clear_text(find_shape(s, "TextBox 2"))
rows = [
    ("Metric (held-out test data)", "Result"),
    ("Spell Corrector top-1 accuracy - synthetic typos",
     f"{pct(SPELL['top1_accuracy_synthetic_typos'])} ({SPELL['correct']} / {SPELL['total']})"),
    ("Spell Corrector top-1 accuracy - real human misspellings",
     f"{pct(SPELL['top1_accuracy_real_world_misspellings'])} "
     f"({SPELL['real_world_correct']} / {SPELL['real_world_total']})"),
    ("N-Gram LM bigram perplexity", f"{LM['bigram_perplexity_on_held_out']:.2f}"),
    ("N-Gram LM trigram perplexity (with back-off)", f"{LM['trigram_perplexity_on_held_out']:.2f}"),
    ("HMM POS Tagger word accuracy",
     f"{pct(POS['word_accuracy'])} ({POS['correct_tags']} / {POS['total_tags']})"),
]
table = s.shapes.add_table(len(rows), 2, Inches(1.0), Inches(1.9), Inches(11.3), Inches(2.5)).table
table.columns[0].width = Inches(7.6)
table.columns[1].width = Inches(3.7)
for r, (label, value) in enumerate(rows):
    for c, text in enumerate((label, value)):
        cell = table.cell(r, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if r == 0 else (
            RGBColor(0xFF, 0xFF, 0xFF) if r % 2 else RGBColor(0xEE, 0xF2, 0xF7))
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(16)
                run.font.name = "Arial"
                run.font.bold = r == 0
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if r == 0 else DARK
tb4 = find_shape(s, "TextBox 4")
resize(tb4, top=4.75, height=2.0)
set_bullets(tb4, [
    "Real misspellings: 193 of 500 are 3+ edits away (out of reach by design); "
    "on the 307 within reach, accuracy is 61.9%",
    "Trigram > bigram perplexity: Laplace adds V ≈ 40K to every denominator, "
    "which swamps the sparse trigram counts",
    "Every number reproduces with: python evaluate.py (fixed seed)",
], size=16)

# ---------------------------------------------------------------- Slide 8: Confusion Matrix & Output
s = slides[7]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Left: POS tagger confusion matrix (held-out set) - strongly diagonal; biggest "
    "confusions are NOUN → ADJ (83), DET (80), CONJ (72)",
    "Right: live app - 3 typos fixed, every word tagged, suggestions filtered to the expected tag",
], size=16)
remove_shape(s, "Rectangle 5")
remove_shape(s, "Rectangle 6")
add_picture_fit(s, "assets/pos_confusion_matrix.png", 0.95, 3.25, 5.6, 3.6)
add_picture_fit(s, "assets/app_screenshot.png", 6.75, 3.25, 5.6, 3.6)

# ---------------------------------------------------------------- Slide 9: Error Analysis
s = slides[8]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "23 of 48 synthetic misses: a very common word 2 edits away beat the right word "
    "1 edit away (haed → 'and', not 'head') - the cost of searching edit distance 2",
    "9 misses are real-word typos (will → gill): words are corrected in isolation, "
    "so these are never flagged",
    "Fixed during testing: 'ovr' → 'or' and 'wht' → 'who' (both correct now, "
    "thanks to the learned confusion matrix); 'I' → 'in' (single-letter words)",
    "POS: NOUN confusions on ambiguous words like 'that' - a bigram HMM sees only one previous tag",
    "Next fixes: prefer 1-edit candidates, rank spelling in context, Kneser-Ney smoothing, trigram HMM",
], size=17)

# ---------------------------------------------------------------- Slide 10: Project Proof
s = slides[9]
clear_text(find_shape(s, "TextBox 2"))
tb4 = find_shape(s, "TextBox 4")
resize(tb4, width=6.3)
set_bullets(tb4, [
    f"GitHub: {GITHUB_URL}",
    "Not publicly hosted: runs on localhost and fully offline once the data is downloaded",
    "Run: pip install -r requirements.txt, then cd src and python app.py, "
    "then open http://127.0.0.1:5000",
    "Reproduce all metrics: python evaluate.py",
], size=17)
remove_shape(s, "Rectangle 5")
add_picture_fit(s, "assets/app_screenshot.png", 7.6, 1.85, 4.7, 5.0)

# ---------------------------------------------------------------- Slide 11: Conclusion & Future Work
s = slides[10]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "All 5 modules built at full proposal scope, integrated in a live web app, and evaluated on held-out data",
    f"POS tagging {pct(POS['word_accuracy'])}; spelling {pct(SPELL['top1_accuracy_synthetic_typos'])} "
    "on synthetic typos and 61.9% on real misspellings within reach - all from scratch",
    "Every weakness has a measured cause: frequency bias at edit distance 2, "
    "out-of-range misspellings, Laplace smoothing",
    "Future work: prefer 1-edit candidates, context-aware spelling, "
    "Kneser-Ney smoothing, trigram HMM, optional hosting",
])

# ---------------------------------------------------------------- Slide 12: AI Usage Acknowledgement
# Wording kept from the previous version -- to be finalised with the team
# before submission.
s = slides[11]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Claude (Anthropic's Claude Code) was used throughout: implementing and debugging all 5 modules, "
    "building the evaluation harness, drafting this report/deck, and literature search",
    "All code was executed and tested by the team against real data at every step; "
    "every metric shown here comes from actually running the code",
    "Bugs found during testing (e.g. the single-letter spelling-correction issue) were fixed and re-verified",
    "The team takes full responsibility for the correctness of the final code, results, and this report",
])

# ---------------------------------------------------------------- Slide 13: References
s = slides[12]
clear_text(find_shape(s, "TextBox 2"))
set_bullets(find_shape(s, "TextBox 4"), [
    "Damerau, F. J. (1964). A technique for computer detection and correction of spelling errors. CACM, 7(3).",
    "Kernighan, M. D., Church, K. W., & Gale, W. A. (1990). A spelling correction program based on a noisy channel model. COLING.",
    "Katz, S. M. (1987). Estimation of probabilities from sparse data... IEEE Trans. ASSP, 35(3).",
    "Brown, P. F. et al. (1992). Class-based n-gram models of natural language. Computational Linguistics, 18(4).",
    "Chen, S. F., & Goodman, J. (1999). An empirical study of smoothing techniques for language modeling. CSL, 13(4).",
    "Church, K. W. (1988). A stochastic parts program and noun phrase parser for unrestricted text. ANLP.",
    "Viterbi, A. J. (1967). Error bounds for convolutional codes... IEEE Trans. Information Theory, 13(2).",
    "Norvig, P. (2009). Natural language corpus data. In Beautiful Data, O'Reilly, 219-242.",
    "Brants, T. (2000). TnT - A statistical part-of-speech tagger. ANLP.",
], size=14)

# ---------------------------------------------------------------- Drop slide 2
# The template's slide 2 ("Title Slide") only repeats the cover, so remove
# it, then renumber the footers -- the template types each slide's number
# into its footer text box instead of using a slide-number field.
sld_ids = prs.slides._sldIdLst
dup = sld_ids[1]
prs.part.drop_rel(dup.rId)
sld_ids.remove(dup)

for number, slide in enumerate(prs.slides, start=1):
    for shape in slide.shapes:
        if (shape.has_text_frame and shape.top > Inches(6.9)
                and "Research Presentation" in shape.text_frame.text):
            for p in shape.text_frame.paragraphs:
                for run in p.runs:
                    run.text = re.sub(r"\d+(\s*)$", rf"{number}\g<1>", run.text)

prs.save(OUTPUT)
print(f"Saved {OUTPUT}")
