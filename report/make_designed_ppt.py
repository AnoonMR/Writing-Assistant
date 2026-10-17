"""Build a designed version of the Activity 2 deck (dark navy theme matching the web app).

Writes Activity_2_Presentation_Designed.pptx next to this script. The plain,
template-based deck (fill_ppt.py -> Activity_2_Presentation.pptx) is left as is.

Usage:  python make_designed_ppt.py
"""
import copy
import json
import os

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "Activity_2_Presentation_Designed.pptx")

# ---- Fill these in before submitting -------------------------------------
MEMBERS = ["Anoon M R  ·  25MCAR0179", "Aman Kumawat  ·  25MCAR0023",
           "Adithya Krishnan T N  ·  25MCAR0003"]
# ---------------------------------------------------------------------------

with open(os.path.join(HERE, "evaluation_results.json")) as f:
    EV = json.load(f)

# Palette (same family as src/templates/index.html)
BG = "0B1020"
CARD = "141B33"
CARD2 = "1B2445"
BORDER = "2B3766"
TEXT = "F1F5FF"
MUTED = "A3AECF"
BLUE = "5B8CFF"
PURPLE = "8B5CF6"
PINK = "EC4899"
PINK_L = "F472B6"
LAVENDER = "C4B5FD"
GREEN = "34D399"
AMBER = "FBBF24"
CYAN = "22D3EE"
FONT = "Calibri"
MONO = "Consolas"

SW, SH = 13.333, 7.5
TOTAL = 12


def rgb(h):
    return RGBColor.from_string(h)


# ---------------------------------------------------------------- primitives
def _spPr(shape):
    return shape._element.spPr


def no_effects(shape):
    """Explicit empty effect list so the theme never adds a shadow."""
    spPr = _spPr(shape)
    for e in spPr.findall(qn("a:effectLst")):
        spPr.remove(e)
    etree.SubElement(spPr, qn("a:effectLst"))


def set_alpha(shape, alpha_pct):
    clr = _spPr(shape).find(qn("a:solidFill")).find(qn("a:srgbClr"))
    a = etree.SubElement(clr, qn("a:alpha"))
    a.set("val", str(int(alpha_pct * 1000)))


def soft_edge(shape, inches):
    spPr = _spPr(shape)
    eff = spPr.find(qn("a:effectLst"))
    if eff is None:
        eff = etree.SubElement(spPr, qn("a:effectLst"))
    se = etree.SubElement(eff, qn("a:softEdge"))
    se.set("rad", str(int(Inches(inches))))


def shape(slide, kind, x, y, w, h, fill=None, line=None, line_w=0.75, radius=None, name=None):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(fill)
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(line_w)
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, radius / min(w, h))
    no_effects(s)
    s.text_frame.text = ""
    if name:
        s.name = name
    return s


def gradient(s, c1=BLUE, c2=PINK, angle=0, mid=None):
    s.fill.gradient()
    s.fill.gradient_angle = angle
    stops = s.fill.gradient_stops
    stops[0].color.rgb = rgb(c1)
    stops[0].position = 0
    stops[1].color.rgb = rgb(c2)
    stops[1].position = 1.0
    if mid:
        gsLst = _spPr(s).find(qn("a:gradFill")).find(qn("a:gsLst"))
        gs = copy.deepcopy(gsLst[0])
        gs.set("pos", "50000")
        gs.find(qn("a:srgbClr")).set("val", mid)
        gsLst.insert(1, gs)


def card(slide, x, y, w, h, fill=CARD, line=BORDER, radius=0.14, name=None):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, 0.75, radius, name)


def text(slide, x, y, w, h, paras, size=14, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=FONT, space_after=0, line_spacing=None, name=None):
    """paras: str | list of (str | list of (text, opts dict))."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(paras, str):
        paras = [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if space_after:
            p.space_after = Pt(space_after)
        if line_spacing:
            p.line_spacing = line_spacing
        runs = [(para, {})] if isinstance(para, str) else para
        for t, o in runs:
            r = p.add_run()
            r.text = t
            fnt = r.font
            fnt.name = o.get("font", font)
            fnt.size = Pt(o.get("size", size))
            fnt.bold = o.get("bold", bold)
            fnt.italic = o.get("italic", False)
            fnt.color.rgb = rgb(o.get("color", color))
    return tb


def badge(slide, x, y, d, label, size=14, c1=BLUE, c2=PINK):
    s = shape(slide, MSO_SHAPE.OVAL, x, y, d, d)
    gradient(s, c1, c2, 45)
    text(slide, x, y, d, d, label, size=size, bold=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    return s


def glow(slide, x, y, d, color, alpha):
    s = shape(slide, MSO_SHAPE.OVAL, x, y, d, d, fill=color, name="Ambient glow")
    set_alpha(s, alpha)
    soft_edge(s, d * 0.32)
    return s


# ---------------------------------------------------------------- slide frame
def new_slide(prs, eyebrow=None, title=None, num=None, glows="default"):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(BG)
    if glows == "default":
        glow(s, 10.2, -2.2, 4.6, PURPLE, 22)
        glow(s, -2.0, 5.0, 4.2, BLUE, 16)
    elif glows == "hero":
        glow(s, 8.3, -2.6, 6.4, PURPLE, 30)
        glow(s, -2.4, 3.8, 5.6, BLUE, 24)
        glow(s, 5.0, 5.6, 4.0, PINK, 16)
    if title:
        text(s, 0.6, 0.42, 9, 0.3, eyebrow.upper(), size=12, color=PINK_L, bold=True, name="Eyebrow")
        text(s, 0.6, 0.72, 12.1, 0.7, title, size=34, bold=True, name="Title")
    if num:
        text(s, 0.6, 7.0, 8, 0.25, "SyntaxSquad  ·  NLP-Based Intelligent Writing Assistant",
             size=10, color=MUTED, name="Footer")
        text(s, 11.73, 7.0, 1.0, 0.25, f"{num} / {TOTAL}", size=10, color=MUTED,
             align=PP_ALIGN.RIGHT, name="Slide number")
    return s


def style_chart_text(chart, color=MUTED, size=12):
    chart.font.name = FONT
    chart.font.size = Pt(size)
    chart.font.color.rgb = rgb(color)


# ====================================================================== slides
def slide_title(prs):
    s = new_slide(prs, glows="hero")
    text(s, 0.7, 0.9, 7.6, 0.3, "ACTIVITY 2", size=13,
         color=PINK_L, bold=True)
    text(s, 0.7, 1.4, 7.6, 1.9, "NLP-Based Intelligent Writing Assistant", size=46, bold=True,
         line_spacing=0.95)
    text(s, 0.7, 3.0, 7.4, 0.9, "Autocorrect, Autocomplete, and POS-Aware Suggestions",
         size=22, color=LAVENDER)

    # Motif: the app's correction chips
    chips = [("teh", "the"), ("jumpd", "jumped"), ("ovr", "over")]
    x = 0.7
    for wrong, right in chips:
        w = 0.42 + 0.115 * (len(wrong) + len(right)) + 0.45
        c = card(s, x, 4.15, w, 0.55, fill="2A1F4A", line="5B3F99", radius=0.12)
        text(s, x, 4.15, w, 0.55, [[(wrong, {"color": MUTED}), ("  →  ", {"color": MUTED}),
                                     (right, {"color": PINK_L, "bold": True})]],
             size=15, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += w + 0.2
    text(s, 0.7, 4.95, 7.4, 0.6,
         "Spell correction  ·  next-word prediction  ·  POS tagging — built from scratch in Python",
         size=14, color=MUTED)

    # Info card
    card(s, 8.55, 1.15, 4.1, 3.6, fill=CARD, line=BORDER, radius=0.2)
    rows = [("TEAM", ["SyntaxSquad"]),
            ("MEMBERS", MEMBERS),
            ("FACULTY", ["Dr. Sharal Coelho"]),
            ("COURSE", ["Natural Language Processing (25MCAAI303)"]),
            ("DEPARTMENT", ["MCA · JAIN (Deemed-to-be University)"])]
    paras = []
    for label, vals in rows:
        paras.append([(label, {"size": 10, "color": PINK_L, "bold": True})])
        for v in vals:
            paras.append([(v, {"size": 14, "color": TEXT, "bold": label == "TEAM"})])
    text(s, 8.85, 1.4, 3.5, 4.8, paras, space_after=3)


def slide_intro(prs):
    s = new_slide(prs, "01 · Introduction", "Introduction & Problem Statement", 2)
    items = [
        ("i", "Background", "A writing assistant built from scratch in Python — spell correction, "
                            "next-word prediction and POS-aware suggestions."),
        ("!", "Problem", "Spell checkers ignore real error patterns; autocomplete ignores grammar."),
        ("★", "Why it matters", "Emails, messages and academic writing all suffer from context-blind "
                                "corrections and ungrammatical suggestions."),
    ]
    w, gap = 3.85, 0.3
    for i, (icon, head, body) in enumerate(items):
        x = 0.6 + i * (w + gap)
        card(s, x, 1.7, w, 2.3)
        badge(s, x + 0.3, 1.95, 0.55, icon, size=16)
        text(s, x + 1.0, 2.0, w - 1.2, 0.45, head, size=20, bold=True)
        text(s, x + 0.3, 2.7, w - 0.6, 1.2, body, size=14, color=MUTED)

    text(s, 0.6, 4.3, 6, 0.4, "Objectives — five modules", size=20, bold=True)
    objs = [("Tokenizer", "Regex-based word splitting"),
            ("Spell corrector", "Noisy Channel, learned confusion matrix, edit distance ≤ 2"),
            ("N-Gram LM", "Bigram + trigram with back-off"),
            ("POS tagger", "HMM decoded with Viterbi"),
            ("Live Flask UI", "Debounced AJAX, updates as you type")]
    w, gap = 2.25, 0.22
    for i, (head, body) in enumerate(objs):
        x = 0.6 + i * (w + gap)
        card(s, x, 4.85, w, 1.85, fill=CARD2)
        badge(s, x + 0.22, 5.05, 0.45, str(i + 1), size=13)
        text(s, x + 0.22, 5.62, w - 0.4, 0.35, head, size=15, bold=True)
        text(s, x + 0.22, 5.98, w - 0.4, 0.7, body, size=12, color=MUTED)


def slide_literature(prs):
    s = new_slide(prs, "02 · Literature", "Literature Survey", 3)
    refs = [("1964", "Damerau", "CACM", "~80% of real typos are a single edit"),
            ("1967", "Viterbi", "IEEE Trans. Info. Theory",
             "The decoding algorithm our POS tagger uses"),
            ("1988", "Church", "ANLP", "HMM-style POS tagger on the Brown Corpus, 95–99% accuracy"),
            ("1990", "Kernighan, Church & Gale", "COLING",
             "Noisy Channel spelling correction with learned confusion matrices — basis of our corrector"),
            ("1999", "Chen & Goodman", "CSL", "Smoothing survey; explains our perplexity results")]
    w, gap = 2.25, 0.2
    line = shape(s, MSO_SHAPE.RECTANGLE, 0.6 + w / 2, 2.13, 4 * (w + gap), 0.04)
    gradient(line, BLUE, PINK, 0, PURPLE)
    for i, (yr, who, venue, finding) in enumerate(refs):
        x = 0.6 + i * (w + gap)
        cx = x + w / 2
        badge(s, cx - 0.5, 1.65, 1.0, yr, size=15)
        card(s, x, 2.95, w, 2.45)
        text(s, x + 0.2, 3.15, w - 0.4, 0.3, venue, size=11, color=PINK_L, bold=True)
        text(s, x + 0.2, 3.45, w - 0.4, 0.65, who, size=15, bold=True)
        text(s, x + 0.2, 4.15, w - 0.4, 1.2, finding, size=12, color=MUTED)

    g = card(s, 0.6, 5.7, 12.13, 0.95, fill="2A1F4A", line="5B3F99")
    text(s, 0.95, 5.7, 11.5, 0.95,
         [[("Research gap:  ", {"bold": True, "color": PINK_L}),
           ("these techniques are usually studied in isolation — we let the HMM filter the "
            "N-gram LM's suggestions in real time.", {})]],
         size=16, anchor=MSO_ANCHOR.MIDDLE)


def slide_method(prs):
    s = new_slide(prs, "03 · Methodology", "Proposed Methodology", 4)
    stages = [("Raw text", "user input"), ("Tokenizer", "regex"), ("Spell corrector", "Noisy Channel"),
              ("POS tagger", "HMM + Viterbi"), ("N-Gram LM", "trigram → bigram"),
              ("POS filter", "match expected tag"), ("Flask UI", "live AJAX")]
    cols = ["5B8CFF", "6A80FB", "7974F8", "8B5CF6", "AB55E0", "CB4EC1", "EC4899"]
    w, gap = 1.5, 0.27
    for i, (head, sub) in enumerate(stages):
        x = 0.6 + i * (w + gap)
        c = card(s, x, 1.65, w, 1.15, fill=CARD, line=cols[i], radius=0.14)
        c.line.width = Pt(1.5)
        text(s, x + 0.08, 1.8, w - 0.16, 0.4, head, size=14, bold=True, align=PP_ALIGN.CENTER)
        text(s, x + 0.08, 2.22, w - 0.16, 0.4, sub, size=11, color=MUTED, align=PP_ALIGN.CENTER)
        if i < len(stages) - 1:
            a = shape(s, MSO_SHAPE.ISOSCELES_TRIANGLE, x + w + 0.07, 2.13, 0.16, 0.18, fill=cols[i + 1])
            a.rotation = 90

    det = [("Spell corrector",
            "Candidates within edit distance 2, ranked by P(word) × P(typo | word). "
            f"P(typo | word) learned from {EV['spell_corrector']['confusion_matrix_train_pairs']:,} "
            "real single-edit misspellings.", BLUE),
           ("N-Gram language model",
            "Trigram with back-off to bigram, Laplace smoothing; trained on Brown Corpus sentences.",
            PURPLE),
           ("HMM POS tagger",
            "Bigram HMM over 10 Universal POS tags, decoded with the Viterbi algorithm.", "AB55E0"),
           ("POS-aware filter",
            "Keep only next-word candidates whose tag matches the tag the HMM expects next.", PINK)]
    w, gap = 5.915, 0.3
    for i, (head, body, col) in enumerate(det):
        x = 0.6 + (i % 2) * (w + gap)
        y = 3.2 + (i // 2) * 1.85
        card(s, x, y, w, 1.6)
        dot = shape(s, MSO_SHAPE.OVAL, x + 0.3, y + 0.33, 0.2, 0.2, fill=col)
        text(s, x + 0.65, y + 0.22, w - 0.95, 0.4, head, size=17, bold=True)
        text(s, x + 0.3, y + 0.7, w - 0.6, 0.85, body, size=14, color=MUTED)


def slide_data(prs):
    s = new_slide(prs, "04 · Data", "Dataset & Experimental Setup", 5)
    stats = [("54,286", "cleaned sentences", "Brown Corpus (NLTK)"),
             ("24,891", "vocabulary words", "frequency ≥ 2"),
             ("54,270", "POS-tagged sentences", "10 Universal tags"),
             ("38,218", "real misspelling pairs", "Norvig corpus, 7,841 words")]
    w, gap = 2.8, 0.31
    for i, (big, lab, src) in enumerate(stats):
        x = 0.6 + i * (w + gap)
        card(s, x, 1.6, w, 1.75)
        text(s, x + 0.3, 1.72, w - 0.6, 0.75, big, size=38, bold=True,
             color=[BLUE, PURPLE, "B455DA", PINK][i])
        text(s, x + 0.3, 2.48, w - 0.6, 0.35, lab, size=16, bold=True)
        text(s, x + 0.3, 2.85, w - 0.6, 0.35, src, size=12, color=MUTED)

    # Where the data was downloaded from
    card(s, 0.6, 3.55, 12.13, 0.75, fill="2A1F4A", line="5B3F99")
    text(s, 0.9, 3.55, 11.6, 0.75,
         [[("Downloaded from:  ", {"bold": True, "color": PINK_L}),
           ("Brown Corpus ", {"bold": True, "color": TEXT}),
           ("— NLTK data (nltk.download('brown'), nltk.org/nltk_data)     ", {}),
           ("Misspellings ", {"bold": True, "color": TEXT}),
           ("— norvig.com/ngrams/spell-errors.txt", {})]],
         size=13, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)

    # Preprocessing flow
    top = 4.5
    card(s, 0.6, top, 5.9, 2.2)
    text(s, 0.9, top + 0.18, 5.3, 0.4, "Preprocessing (Activity 1)", size=18, bold=True)
    steps = ["Lowercase", "Strip punctuation", "Tokenize", "Length filter"]
    for i, st in enumerate(steps):
        y = top + 0.7 + i * 0.36
        badge(s, 0.9, y, 0.3, str(i + 1), size=10)
        text(s, 1.36, y, 4.5, 0.3, st, size=14, anchor=MSO_ANCHOR.MIDDLE)

    # Setup with split bar
    card(s, 6.8, top, 5.93, 2.2)
    text(s, 7.1, top + 0.18, 5.3, 0.4, "Experimental setup", size=18, bold=True)
    bw = 5.33
    by = top + 0.68
    b1 = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.1, by, bw * 0.9 - 0.04, 0.38, radius=0.08)
    gradient(b1, BLUE, PURPLE, 0)
    b2 = shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 7.1 + bw * 0.9 + 0.04, by, bw * 0.1 - 0.04, 0.38,
               fill=PINK, radius=0.08)
    text(s, 7.25, by, 3, 0.38, "90% train", size=13, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 7.1, by + 0.42, 2.5, 0.3, "seed 42", size=12, color=MUTED)
    text(s, 7.1 + bw * 0.9 - 0.9, by + 0.42, 1.5, 0.3, "10% test", size=12, color=PINK_L,
         bold=True, align=PP_ALIGN.RIGHT)
    text(s, 7.1, by + 0.8, 5.33, 0.7,
         ["Applied to all three datasets — every score is on unseen data.",
          [("Tools: ", {"bold": True, "color": TEXT}),
           ("Python 3.12 · Flask 3.1.3 · matplotlib", {})]],
         size=13, color=MUTED, space_after=6)


def slide_results(prs):
    s = new_slide(prs, "05 · Results", "Results & Evaluation", 6)
    sc, pos, lm = EV["spell_corrector"], EV["pos_tagger"], EV["ngram_lm"]
    within = 307
    card(s, 0.6, 1.65, 7.4, 5.05)
    text(s, 0.9, 1.85, 7, 0.4, "Accuracy on held-out test data", size=18, bold=True)
    cd = CategoryChartData()
    cd.categories = [f"POS tagger  ({pos['correct_tags']:,} / {pos['total_tags']:,})",
                     f"Spelling — synthetic typos  ({sc['correct']} / {sc['total']})",
                     f"Spelling — real, within reach  ({sc['real_world_correct']} / {within})",
                     f"Spelling — real, all  ({sc['real_world_correct']} / {sc['real_world_total']})"]
    vals = [pos["word_accuracy"] * 100, sc["top1_accuracy_synthetic_typos"] * 100,
            sc["real_world_correct"] / within * 100, sc["top1_accuracy_real_world_misspellings"] * 100]
    cd.add_series("Accuracy", vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.8), Inches(2.35), Inches(7.0),
                            Inches(4.25), cd)
    gf.name = "Accuracy chart"
    ch = gf.chart
    style_chart_text(ch, MUTED, 12)
    ch.has_legend = False
    ch.has_title = False
    plot = ch.plots[0]
    plot.gap_width = 55
    plot.vary_by_categories = False
    for i, col in enumerate([GREEN, BLUE, PURPLE, PINK]):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(col)
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = '0.0"%"'
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size = Pt(14)
    dl.font.bold = True
    dl.font.color.rgb = rgb(TEXT)
    ca = ch.category_axis
    ca.reverse_order = True
    ca.tick_labels.font.size = Pt(12)
    ca.tick_labels.font.color.rgb = rgb(MUTED)
    ca.format.line.color.rgb = rgb(BORDER)
    ca.has_major_gridlines = False
    va = ch.value_axis
    va.minimum_scale, va.maximum_scale = 0, 115
    va.has_major_gridlines = False
    va.visible = False

    # Perplexity cards
    x, w = 8.3, 4.43
    for i, (big, lab, col) in enumerate([
            (f"{lm['bigram_perplexity_on_held_out']:,.0f}", "Bigram perplexity", BLUE),
            (f"{lm['trigram_perplexity_on_held_out']:,.0f}", "Trigram perplexity (with back-off)", PINK)]):
        y = 1.65 + i * 1.5
        card(s, x, y, w, 1.3)
        text(s, x + 0.3, y + 0.15, w - 0.6, 0.65, big, size=34, bold=True, color=col)
        text(s, x + 0.3, y + 0.82, w - 0.6, 0.35, lab, size=13, color=MUTED)
    card(s, x, 4.7, w, 2.0, fill="2A1F4A", line="5B3F99")
    text(s, x + 0.3, 4.88, w - 0.6, 1.7,
         [[("Why is trigram higher?  ", {"bold": True, "color": PINK_L}),
           ("Laplace adds V ≈ 40K to every denominator, which swamps the sparse trigram counts.", {})],
          [("193 of 500 ", {"bold": True, "color": TEXT}),
           ("real misspellings are 3+ edits away — out of reach by design.", {})]],
         size=13, color=MUTED, space_after=8)


def _img(slide, path, x, y, max_w, max_h, name):
    from PIL import Image
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    pic = slide.shapes.add_picture(path, Inches(x + (max_w - w) / 2), Inches(y + (max_h - h) / 2),
                                   Inches(w), Inches(h))
    pic.name = name
    return pic


def slide_outputs(prs):
    s = new_slide(prs, "06 · Outputs", "Confusion Matrix & Live Output", 7)
    w = 5.915
    card(s, 0.6, 1.65, w, 4.25, fill="FFFFFF", line=BORDER)
    _img(s, os.path.join(ASSETS, "pos_confusion_matrix.png"), 0.75, 1.75, w - 0.3, 4.05,
         "POS confusion matrix")
    card(s, 0.6 + w + 0.3, 1.65, w, 4.25, fill="0E1428", line=BORDER)
    _img(s, os.path.join(ASSETS, "app_screenshot.png"), 0.75 + w + 0.3, 1.75, w - 0.3, 4.05,
         "App screenshot")
    caps = [("POS tagger confusion matrix", "Held-out set, strongly diagonal. Biggest confusions: "
                                            "NOUN → ADJ (83), DET (80), CONJ (72)."),
            ("Live web app", "3 typos fixed, every word tagged, next-word suggestions filtered "
                             "to the expected tag.")]
    for i, (head, body) in enumerate(caps):
        x = 0.6 + i * (w + 0.3)
        badge(s, x, 6.1, 0.4, "L" if i == 0 else "R", size=11)
        text(s, x + 0.55, 6.08, w - 0.6, 0.85,
             [[(head, {"bold": True, "color": TEXT, "size": 15})], body], size=12, color=MUTED)


def slide_errors(prs):
    s = new_slide(prs, "07 · Error analysis", "Error Analysis", 8)
    card(s, 0.6, 1.65, 5.9, 5.05)
    text(s, 0.9, 1.85, 5.3, 0.4, "Why the 48 synthetic-typo misses happened", size=17, bold=True)
    parts = [(23, "ED-2 word with a huge prior beat the ED-1 answer (haed → “and”, not “head”)", BLUE),
             (11, "A different edit-distance-1 word won", PURPLE),
             (9, "Real-word typos (will → gill) — never flagged", PINK),
             (5, "Target word not in the vocabulary", AMBER)]
    cd = CategoryChartData()
    cd.categories = [p[1] for p in parts]
    cd.add_series("Misses", [p[0] for p in parts])
    gf = s.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(0.8), Inches(2.4), Inches(2.3),
                            Inches(2.3), cd)
    gf.name = "Error donut"
    ch = gf.chart
    style_chart_text(ch, TEXT, 12)
    ch.has_legend = False
    ch.has_title = False
    plot = ch.plots[0]
    for i, p in enumerate(parts):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(p[2])
        pt.format.line.color.rgb = rgb(CARD)
    hole = ch._chartSpace.find(".//" + qn("c:holeSize"))
    if hole is None:
        hole = etree.SubElement(ch._chartSpace.find(".//" + qn("c:doughnutChart")), qn("c:holeSize"))
    hole.set("val", "62")
    text(s, 0.8, 3.2, 2.3, 0.45, "48", size=30, bold=True, align=PP_ALIGN.CENTER)
    text(s, 0.8, 3.65, 2.3, 0.3, "misses", size=12, color=MUTED, align=PP_ALIGN.CENTER)
    # Legend beside the donut
    short = ["ED-2 word beat ED-1", "Other ED-1 word won", "Real-word typo", "Not in vocabulary"]
    for i, ((n, _, col), lab) in enumerate(zip(parts, short)):
        y = 2.5 + i * 0.55
        shape(s, MSO_SHAPE.OVAL, 3.35, y + 0.1, 0.18, 0.18, fill=col)
        text(s, 3.65, y, 2.7, 0.38,
             [[(f"{n}  ", {"bold": True, "color": col, "size": 16}), (lab, {})]],
             size=13, anchor=MSO_ANCHOR.MIDDLE)
    card(s, 0.9, 5.0, 5.3, 1.25, fill=CARD2, line=BORDER)
    text(s, 1.15, 5.15, 4.8, 1.2,
         [[("haed → “and”, not “head”: ", {"bold": True, "color": TEXT}),
           ("a very common word 2 edits away outranks the right word 1 edit away.", {})],
          [("will → gill: ", {"bold": True, "color": TEXT}),
           ("a real word, so words corrected in isolation never flag it.", {})]],
         size=12, color=MUTED, space_after=5)

    right = [("Fixed during testing", GREEN,
              "“ovr” used to give “or” and “wht” gave “who” — both now give “over” and “what”, "
              "thanks to the learned confusion matrix. Single-letter “I” → “in” also fixed."),
             ("POS confusions", AMBER,
              "NOUN mix-ups on noun/adjective words (green, public) and unseen names — a bigram HMM only sees one previous tag."),
             ("Next fixes", PINK_L,
              "Prefer 1-edit candidates · rank spelling in context · Kneser-Ney smoothing · trigram HMM.")]
    for i, (head, col, body) in enumerate(right):
        y = 1.65 + i * 1.75
        card(s, 6.8, y, 5.93, 1.55)
        text(s, 7.1, y + 0.2, 5.3, 0.4, head, size=17, bold=True, color=col)
        text(s, 7.1, y + 0.62, 5.33, 0.9, body, size=13, color=MUTED)


def slide_proof(prs):
    s = new_slide(prs, "08 · Project proof", "Project Proof", 9)
    card(s, 0.6, 1.65, 7.3, 1.25)
    badge(s, 0.9, 1.95, 0.65, "</>", size=13)
    text(s, 1.8, 1.85, 5.9, 0.35, "Source code on GitHub", size=13, color=MUTED)
    text(s, 1.8, 2.2, 5.9, 0.45, "github.com/AnoonMR/Writing-Assistant", size=20, bold=True,
         color=TEXT)

    term = card(s, 0.6, 3.15, 7.3, 2.6, fill="070B16", line=BORDER)
    for i, col in enumerate(["F87171", AMBER, GREEN]):
        shape(s, MSO_SHAPE.OVAL, 0.85 + i * 0.25, 3.35, 0.14, 0.14, fill=col)
    cmd = lambda c, note="": [("$ ", {"color": PINK_L}), (c, {"color": TEXT}),
                              (note, {"color": "6B7799"})]
    text(s, 0.9, 3.7, 6.8, 1.95,
         [cmd("pip install -r requirements.txt"),
          cmd("cd src"),
          cmd("python app.py"),
          [("→ open http://127.0.0.1:5000", {"color": GREEN})],
          cmd("python evaluate.py", "   # reproduce every metric")],
         size=14, font=MONO, space_after=5)

    card(s, 0.6, 6.0, 7.3, 0.7, fill="2A1F4A", line="5B3F99")
    text(s, 0.9, 6.0, 6.8, 0.7,
         [[("Not publicly hosted — ", {"bold": True, "color": PINK_L}),
           ("runs on localhost, fully offline once the data is downloaded.", {})]],
         size=13, anchor=MSO_ANCHOR.MIDDLE)

    card(s, 8.2, 1.65, 4.53, 5.05, fill="0E1428", line=BORDER)
    _img(s, os.path.join(ASSETS, "app_screenshot.png"), 8.3, 1.75, 4.33, 4.85, "App screenshot")


def slide_conclusion(prs):
    s = new_slide(prs, "09 · Conclusion", "Conclusion & Future Work", 10, glows="hero")
    sc = EV["spell_corrector"]
    cards = [("5 / 5", "modules built", "At full proposal scope, integrated in one live web app and "
                                         "evaluated on held-out data.", BLUE),
             (f"{EV['pos_tagger']['word_accuracy'] * 100:.2f}%", "POS tagging accuracy",
              f"Spelling: {sc['top1_accuracy_synthetic_typos'] * 100:.2f}% on synthetic typos and "
              "61.9% on real misspellings within reach — all from scratch.", PURPLE),
             ("3", "weak spots, all diagnosed", "Each has a measured cause: frequency bias at edit "
                                              "distance 2, out-of-range misspellings, Laplace "
                                              "smoothing.", PINK)]
    w, gap = 3.85, 0.3
    for i, (big, lab, body, col) in enumerate(cards):
        x = 0.6 + i * (w + gap)
        card(s, x, 1.65, w, 2.55)
        text(s, x + 0.3, 1.85, w - 0.6, 0.85, big, size=42, bold=True, color=col)
        text(s, x + 0.3, 2.7, w - 0.6, 0.4, lab, size=17, bold=True)
        text(s, x + 0.3, 3.15, w - 0.6, 1.3, body, size=13, color=MUTED)

    text(s, 0.6, 4.6, 6, 0.4, "Future work", size=20, bold=True)
    fut = ["Prefer 1-edit candidates", "Context-aware spelling", "Kneser-Ney smoothing",
           "Trigram HMM", "Optional hosting"]
    w, gap = 2.25, 0.22
    for i, f in enumerate(fut):
        x = 0.6 + i * (w + gap)
        card(s, x, 5.15, w, 0.85, fill=CARD2, line=BORDER, radius=0.3)
        text(s, x, 5.15, w, 0.85, f, size=14, bold=True, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)


def slide_ai(prs):
    s = new_slide(prs, "10 · Acknowledgement", "AI Usage Acknowledgement", 11)
    card(s, 1.6, 2.2, 10.13, 2.9, fill=CARD, line=BORDER, radius=0.25)
    badge(s, 6.665 - 0.45, 2.55, 0.9, "AI", size=20)
    text(s, 2.2, 3.7, 8.93, 1.5,
         "This project was developed with the assistance of Claude (Anthropic), an AI tool, "
         "which was used for code implementation and debugging.",
         size=20, align=PP_ALIGN.CENTER, line_spacing=1.1)


def slide_refs(prs):
    s = new_slide(prs, "11 · References", "References", 12)
    refs = [
        "Damerau, F. J. (1964). A technique for computer detection and correction of spelling errors. CACM, 7(3).",
        "Kernighan, M. D., Church, K. W., & Gale, W. A. (1990). A spelling correction program based on a noisy channel model. COLING.",
        "Katz, S. M. (1987). Estimation of probabilities from sparse data... IEEE Trans. ASSP, 35(3).",
        "Brown, P. F. et al. (1992). Class-based n-gram models of natural language. Computational Linguistics, 18(4).",
        "Chen, S. F., & Goodman, J. (1999). An empirical study of smoothing techniques for language modeling. CSL, 13(4).",
        "Church, K. W. (1988). A stochastic parts program and noun phrase parser for unrestricted text. ANLP.",
        "Viterbi, A. J. (1967). Error bounds for convolutional codes... IEEE Trans. Information Theory, 13(2).",
        "Norvig, P. (2009). Natural language corpus data. In Beautiful Data, O'Reilly, 219–242.",
        "Brants, T. (2000). TnT — A statistical part-of-speech tagger. ANLP.",
    ]
    w, gap = 5.915, 0.3
    for i, r in enumerate(refs):
        col, row = (0, i) if i < 5 else (1, i - 5)
        x = 0.6 + col * (w + gap)
        y = 1.7 + row * 1.0
        badge(s, x, y + 0.05, 0.4, str(i + 1), size=11)
        text(s, x + 0.6, y, w - 0.6, 0.9, r, size=14, color=MUTED)


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
    for fn in (slide_title, slide_intro, slide_literature, slide_method, slide_data, slide_results,
               slide_outputs, slide_errors, slide_proof, slide_conclusion, slide_ai, slide_refs):
        fn(prs)
    prs.core_properties.title = "NLP-Based Intelligent Writing Assistant"
    prs.core_properties.author = "SyntaxSquad"
    prs.save(OUT)
    print("Saved", OUT)


if __name__ == "__main__":
    main()
