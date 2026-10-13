"""One-off script to render the system workflow diagram for the report."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

# Stage order matches src/app.py:analyze() -- the HMM tags the corrected
# text first, then the N-gram LM proposes next words, then the POS filter.
stages = [
    "Raw Text\nInput",
    "Tokenizer\n(regex)",
    "Spell Corrector\n(Noisy Channel,\nedit distance ≤ 2,\nlearned confusion\nmatrix)",
    "HMM POS Tagger\n(Viterbi\ndecoding)",
    "N-Gram LM\n(trigram with\nbigram backoff,\nLaplace)",
    "POS-Aware Filter\n(keep words\nmatching the\nexpected tag)",
    "Flask Web UI\n(live AJAX\nupdates)",
]

fig, ax = plt.subplots(figsize=(13, 2.4))
ax.set_xlim(0, len(stages))
ax.set_ylim(0, 1)
ax.axis("off")

box_w, box_h = 0.88, 0.62
colors = ["#e8eef7", "#dbe7f5", "#cfe3f3", "#c3dff2", "#b7dbf0", "#abd7ee", "#a0d3ed"]

for i, (stage, color) in enumerate(zip(stages, colors)):
    x = i + (1 - box_w) / 2
    y = 0.5 - box_h / 2
    rect = mpatches.FancyBboxPatch(
        (x, y), box_w, box_h,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=1.2, edgecolor="#2c3e50", facecolor=color
    )
    ax.add_patch(rect)
    ax.text(i + 0.5, 0.5, stage, ha="center", va="center", fontsize=9, wrap=True)

    if i < len(stages) - 1:
        arrow = FancyArrowPatch(
            (i + 1 - (1 - box_w) / 2, 0.5), (i + 1 + (1 - box_w) / 2, 0.5),
            arrowstyle="-|>", mutation_scale=14, color="#2c3e50", linewidth=1.2
        )
        ax.add_patch(arrow)

plt.tight_layout()
plt.savefig("assets/system_workflow.png", dpi=150, bbox_inches="tight")
print("Saved assets/system_workflow.png")
