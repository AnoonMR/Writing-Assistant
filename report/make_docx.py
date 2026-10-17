"""Build main.docx (Word version of the report) from main.tex.

LaTeX -> pandoc -> python-docx clean-up (title page, table borders, fonts).
Open the result in Word once and the table of contents fills in automatically
(the script asks Word to update fields on open).

Needs:  pip install pypandoc_binary python-docx
Usage:  python make_docx.py
"""
import os
import re
import subprocess
import sys
import tempfile

import pypandoc
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "main.tex")
OUT = os.path.join(HERE, "main.docx")
FONT = "Cambria"


# ------------------------------------------------------------------ LaTeX prep
def preprocess(tex):
    """Turn \\cite/\\bibitem into plain [n] numbers (pandoc has no .bib here)
    and swap the title page for a marker paragraph we rebuild in Word."""
    keys = re.findall(r"\\bibitem\{([^}]+)\}", tex)
    num = {k: i + 1 for i, k in enumerate(keys)}
    tex = re.sub(r"\\cite\{([^}]+)\}",
                 lambda m: "[" + ", ".join(str(num[k.strip()]) for k in m.group(1).split(",")) + "]",
                 tex)
    tex = re.sub(r"\\bibitem\{([^}]+)\}", lambda m: f"\n\n[{num[m.group(1)]}]~", tex)
    tex = tex.replace("\\begin{thebibliography}{99}", "\\chapter*{Bibliography}\n")
    tex = tex.replace("\\end{thebibliography}", "")

    # Number captions the way LaTeX does (per chapter) and resolve \ref{} to those numbers
    labels = {}
    out, chap, sec, counts, kind = [], 0, 0, {"figure": 0, "table": 0}, None
    for tok in re.split(r"(\\chapter\{|\\section\{|\\begin\{(?:figure|table|longtable)\}|\\caption\{|"
                        r"\\label\{[^}]*\})", tex):
        if tok == "\\chapter{":
            chap += 1
            sec = 0
            counts = {"figure": 0, "table": 0}
        elif tok == "\\section{":
            sec += 1
        elif tok.startswith("\\begin{"):
            kind = "figure" if "figure" in tok else "table"
        elif tok == "\\caption{" and kind:
            counts[kind] += 1
            n = f"{chap}.{counts[kind]}"
            out.append(tok + f"{kind.capitalize()} {n}: ")
            labels["__last__"] = n
            continue
        elif tok.startswith("\\label{"):
            key = tok[7:-1]
            if key.startswith(("fig:", "tab:")):
                labels[key] = labels.get("__last__", "?")
            elif key.startswith("ch:"):
                labels[key] = str(chap)
            elif key.startswith("sec:"):
                labels[key] = f"{chap}.{sec}"
            continue
        out.append(tok)
    tex = "".join(out)
    tex = re.sub(r"\\(?:ref|autoref)\{([^}]+)\}", lambda m: labels.get(m.group(1), "?"), tex)

    title = re.search(r"\\begin\{titlepage\}(.*?)\\end\{titlepage\}", tex, re.S).group(1)
    tex = tex.replace(title, "\nTITLEPAGEMARKER\n")
    tex = re.sub(r"\\(tableofcontents|listoffigures|listoftables)", r"\nTOCMARKER\n", tex, count=1)
    tex = re.sub(r"\\(tableofcontents|listoffigures|listoftables)", "", tex)
    return tex, title


def title_info(title):
    def grab(pattern, default=""):
        m = re.search(pattern, title, re.S)
        return m.group(1).strip() if m else default

    students = re.findall(r"Student \d+:\s*&\s*(.*?)\s*\\\\", title)
    return {
        "university": grab(r"\\textbf\{(JAIN[^}]*)\}"),
        "dept": grab(r"\{\\large (Department[^}]*)\}"),
        "activity": grab(r"\\textbf\{(ACTIVITY[^}]*)\}", "ACTIVITY 2"),
        "kind": grab(r"\{\\Large (Student[^}]*)\}", "Student Research Report"),
        "title": re.sub(r"\s+", " ", grab(r"\\LARGE \\textbf\{(.*?)\}\}")),
        "team": grab(r"\{\\large (Team Name:[^}]*)\}"),
        "students": students,
        "course": grab(r"\\textbf\{Course:\}\s*(.*?)\\\\"),
        "faculty": grab(r"\\textbf\{Faculty:\}\s*(.*?)\\\\"),
        "year": grab(r"\\textbf\{Academic Year:\}\s*(.*?)\\\\").replace("--", "–"),
        # left blank on purpose (filled in by hand on the printout)
        "date": "_" * 22,
    }


# ------------------------------------------------------------------ docx helpers
def para_after(p, text="", style=None):
    new = OxmlElement("w:p")
    p._p.addnext(new)
    from docx.text.paragraph import Paragraph
    np_ = Paragraph(new, p._parent)
    if style:
        np_.style = style
    if text:
        np_.add_run(text)
    return np_


def styled(par, text, size, bold=False, color=None, space_after=0, italic=False):
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(space_after)
    par.paragraph_format.space_before = Pt(0)
    r = par.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    return par


def build_title(doc, marker, info):
    rows = [
        (info["university"], 16, True, None, 2),
        (info["dept"], 13, False, None, 36),
        (info["activity"], 18, True, "1F3864", 2),
        (info["kind"], 14, False, None, 30),
        (info["title"], 20, True, None, 8),
        (info["team"], 13, False, None, 40),
        ("Submitted by", 13, True, None, 8),
    ]
    rows += [(s, 12, False, None, 2) for s in info["students"]]
    rows += [("", 12, False, None, 90),
             (f"Course: {info['course']}", 12, False, None, 2),
             (f"Faculty: {info['faculty']}", 12, False, None, 2),
             (f"Academic Year: {info['year']}", 12, False, None, 14),
             (f"Submission Date: {info['date']}", 12, True, None, 0)]
    cur = marker
    for i, (t, size, bold, color, after) in enumerate(rows):
        p = cur if i == 0 else para_after(cur)
        p.text = ""
        styled(p, t, size, bold, color, after)
        cur = p
    cur.add_run().add_break(WD_BREAK.PAGE)


def build_toc(doc, marker):
    marker.text = ""
    marker.style = doc.styles["Normal"]
    r = marker.add_run("Contents")
    r.bold = True
    r.font.size = Pt(20)
    p = para_after(marker)
    run = p.add_run()
    for tag, text in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None),
                      (None, None), ("end", None)):
        if tag:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), tag)
            run._r.append(fc)
        elif text:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            run._r.append(it)
        else:
            t = OxmlElement("w:t")
            t.text = "Right-click here and choose Update Field to build the table of contents."
            run._r.append(t)


WORD_PS = r"""
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
$d = $w.Documents.Open('{path}')
foreach ($t in $d.TablesOfContents) {{ $t.Update() }}
$d.Fields.Update() | Out-Null
$d.Save()
'pages: ' + $d.ComputeStatistics(2)
$d.Close()
$w.Quit()
"""


def word_update_toc(path, pages_only=False):
    """Let Word fill in the TOC and page numbers (Windows + Word only)."""
    ps = WORD_PS.format(path=path)
    if pages_only:
        ps = ps.replace("$t.Update()", "$t.UpdatePageNumbers()").replace("$d.Fields.Update() | Out-Null", "")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=180)
        print("Word:", (r.stdout or r.stderr).strip())
    except Exception as e:  # no Word: the TOC fills in on first "Update Field" instead
        print("Word update skipped:", e)


def borders(table):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "808080")
        b.append(e)
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    tblPr.append(b)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c in table.rows[0].cells:
        sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear")
        sh.set(qn("w:fill"), "D9E2F3")
        c._tc.get_or_add_tcPr().append(sh)
        for p in c.paragraphs:
            for r in p.runs:
                r.bold = True


def page_numbers(section):
    section.header.is_linked_to_previous = False
    hp = section.header.paragraphs[0]
    hp.text = "Activity 2 – Research Report\tDepartment of MCA"
    hp.paragraph_format.tab_stops.clear_all()
    hp.paragraph_format.tab_stops.add_tab_stop(section.page_width - section.left_margin
                                               - section.right_margin, WD_TAB_ALIGNMENT.RIGHT)
    for r in hp.runs:
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), tag)
            run._r.append(fc)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            run._r.append(it)


def main():
    tex = open(SRC, encoding="utf-8").read()
    pre, title = preprocess(tex)
    info = title_info(title)
    with tempfile.TemporaryDirectory() as td:
        tmp_tex = os.path.join(td, "main_pp.tex")
        tmp_docx = os.path.join(td, "raw.docx")
        open(tmp_tex, "w", encoding="utf-8").write(pre)
        pypandoc.convert_file(tmp_tex, "docx", format="latex", outputfile=tmp_docx,
                              extra_args=[f"--resource-path={HERE}"])
        doc = Document(tmp_docx)

    # Base fonts
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in doc.styles:
            st = doc.styles[name]
            st.font.name = FONT
            st.font.size = Pt(12)
            st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT) if st.element.rPr is not None else None
    for lvl, size in ((1, 20), (2, 15), (3, 13)):
        nm = f"Heading {lvl}"
        if nm in doc.styles:
            st = doc.styles[nm]
            st.font.name = FONT
            st.font.size = Pt(size)
            st.font.bold = True
            st.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
            rf = st.element.rPr.rFonts
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                rf.attrib.pop(qn(a), None)

    # Chapters (Heading 1) start on a new page; number chapters and sections like LaTeX
    chap = sec = 0
    for p in doc.paragraphs:
        name = p.style.name
        if name == "Heading 1":
            p.paragraph_format.page_break_before = True
            if p.text.strip() != "Bibliography":
                chap, sec = chap + 1, 0
                p.runs[0].text = f"Chapter {chap}:  " + p.runs[0].text
        elif name == "Heading 2" and chap:
            sec += 1
            p.runs[0].text = f"{chap}.{sec}  " + p.runs[0].text

    for p in list(doc.paragraphs):
        if p.text.strip() == "TITLEPAGEMARKER":
            build_title(doc, p, info)
        elif p.text.strip() == "TOCMARKER":
            build_toc(doc, p)

    # Compact contents entries so the whole TOC (and its closing paragraph) fits on one page
    from docx.enum.style import WD_STYLE_TYPE
    for lvl in (1, 2):
        # Word finds its TOC styles by styleId "TOC1"/"TOC2" (UI name "toc 1")
        st = next((s for s in doc.styles if s.style_id == f"TOC{lvl}"), None)
        if st is None:
            st = doc.styles.add_style(f"toc {lvl}", WD_STYLE_TYPE.PARAGRAPH)
            st.element.set(qn("w:styleId"), f"TOC{lvl}")
        st.base_style = doc.styles["Normal"]
        st.font.size = Pt(11)
        st.paragraph_format.space_before = Pt(0)
        st.paragraph_format.space_after = Pt(1 if lvl == 2 else 3)
        st.paragraph_format.left_indent = Cm(0 if lvl == 1 else 0.6)

    # Empty paragraphs right before a chapter can spill onto an otherwise blank page
    for p in list(doc.paragraphs):
        nxt = p._p.getnext()
        if (not p.text.strip() and not p._p.xpath(".//w:drawing|.//w:br|.//w:fldChar")
                and nxt is not None and nxt.xpath("./w:pPr/w:pStyle[@w:val='Heading1']")):
            p._p.getparent().remove(p._p)

    for t in doc.tables:
        # longtable's \endfirsthead + \endhead come through as two identical header rows
        if len(t.rows) > 1 and [c.text for c in t.rows[0].cells] == [c.text for c in t.rows[1].cells]:
            t._tbl.remove(t.rows[1]._tr)
        borders(t)

    # Centre figures and captions
    for p in doc.paragraphs:
        if p.style.name in ("Captioned Figure", "Image Caption", "Table Caption") or \
                p._p.xpath(".//pic:pic"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.54))
    sec.different_first_page_header_footer = True
    page_numbers(sec)

    doc.save(OUT)
    print("Saved", OUT)
    if sys.platform == "win32":
        word_update_toc(OUT)
        fix_toc_tail(OUT)
        word_update_toc(OUT, pages_only=True)   # page numbers shift once the blank page is gone
        fix_toc_tail(OUT)


def fix_toc_tail(path):
    """Word leaves the TOC field's end marker in its own paragraph; when the TOC
    fills page 2 that paragraph spills onto a blank page 3. Fold it into the
    last TOC line."""
    doc = Document(path)
    for p in doc.paragraphs:
        runs = p._p.findall(qn("w:r"))
        nxt, prev = p._p.getnext(), p._p.getprevious()
        if (not p.text.strip() and runs and all(r.find(qn("w:fldChar")) is not None or
                                                 not "".join(r.itertext()).strip() for r in runs)
                and p._p.xpath(".//w:fldChar[@w:fldCharType='end']")
                and prev is not None and prev.xpath("./w:pPr/w:pStyle[starts-with(@w:val,'TOC')]")
                and nxt is not None and nxt.xpath("./w:pPr/w:pStyle[@w:val='Heading1']")):
            for r in runs:
                for br in r.findall(qn("w:lastRenderedPageBreak")):
                    r.remove(br)
                prev.append(r)
            p._p.getparent().remove(p._p)
            doc.save(path)
            print("Folded TOC end marker into the last TOC line")
            return


if __name__ == "__main__":
    main()
