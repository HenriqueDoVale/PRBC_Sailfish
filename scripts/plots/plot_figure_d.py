"""
Figure D — throughput vs end-to-end latency, PRBC-Sailfish against Narwhal
Sailfish, one panel per committee size. 50-machine cluster, one node per
machine, 512 B transactions, 60 s runs.

Points follow the sweep in order of offered rate, so a curve that bends back
to the left has saturated: delivered throughput falls while latency climbs.

    pip install matplotlib
    python scripts/plots/plot_figure_d.py   ->  figure_d.pdf  +  figure_d.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator

OURS = "#0b6fc4"
BASE = "#bf6708"

# (delivered tx/s, end-to-end latency ms), in sweep order of offered rate
PANELS = [
    dict(n=10, ours_cfg="500 tx", base_cfg="50 ms",
         ours=[(99842, 131.4), (115080, 366.7), (119730, 838.6), (125100, 1501.2)],
         base=[(148976, 2530), (196010, 4381), (243467, 3043),
               (260601, 2565), (268354, 2489)]),
    dict(n=20, ours_cfg="500 tx", base_cfg="50 ms",
         ours=[(79680, 310.2), (99700, 265.2), (116340, 395.2),
               (119175, 604.4), (121004, 823.3)],
         base=[(198503, 3049), (238879, 2784), (252146, 2611), (107983, 2835)]),
    dict(n=30, ours_cfg="500 tx", base_cfg="50 ms",
         ours=[(99192, 417.4), (106433, 552.5), (108142, 815.5), (109167, 1194.0)],
         base=[(197878, 1593), (218017, 1657), (241016, 2041), (243488, 1681)]),
    dict(n=50, ours_cfg="500 tx", base_cfg="400 ms",
         ours=[(64175, 1000.0), (69175, 946.8), (74167, 903.2),
               (72750, 888.2), (72300, 929.5), (40225, 2413.2)],
         base=[(74050, 5043), (99126, 3735), (123809, 2120),
               (148031, 848), (172314, 785), (194695, 1145)]),
]

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.7,
    "axes.edgecolor": "#555555",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "legend.frameon": False,
})

fig, axes = plt.subplots(2, 2, figsize=(6.8, 5.0), sharex=True, sharey=True)

for ax, p in zip(axes.flat, PANELS):
    bx, by = zip(*p["base"])
    ox, oy = zip(*p["ours"])

    ax.plot(bx, by, color=BASE, lw=1.6, ls=(0, (5, 2)), marker="o", ms=3.6,
            mec="white", mew=0.7, zorder=2, label="Narwhal Sailfish")
    ax.plot(ox, oy, color=OURS, lw=1.6, marker="o", ms=3.6,
            mec="white", mew=0.7, zorder=3, label="PRBC-Sailfish")

    ax.set_yscale("log")
    ax.set_xlim(0, 285000)
    ax.set_ylim(90, 7000)
    ax.grid(True, which="major", axis="both", lw=0.5, color="#e3e3e3", zorder=0)
    ax.set_axisbelow(True)

    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 3.0)))
    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda v, _: f"{v/1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.xaxis.set_major_formatter(FuncFormatter(
        lambda v, _: "0" if v == 0 else f"{v/1000:g}k"))
    ax.set_xticks([0, 100000, 200000])

    ax.set_title(f"$n$ = {p['n']}", fontsize=9.5, pad=6, loc="left")
    ax.text(0.98, 0.95,
            f"ours {p['ours_cfg']} · Narwhal {p['base_cfg']}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=7, color="#666666")

for ax in axes[1, :]:
    ax.set_xlabel("delivered throughput (tx/s)")
for ax in axes[:, 0]:
    ax.set_ylabel("end-to-end latency (ms)")

handles, labels = axes[0, 0].get_legend_handles_labels()
order = [1, 0]  # ours first
fig.legend([handles[i] for i in order], [labels[i] for i in order],
           loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.015),
           fontsize=9, handlelength=2.6, columnspacing=2.2)

fig.tight_layout(rect=(0, 0, 1, 0.955))
fig.savefig("figure_d.pdf")
fig.savefig("figure_d.png", dpi=300)
print("wrote figure_d.pdf and figure_d.png")
