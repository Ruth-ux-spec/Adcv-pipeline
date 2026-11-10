import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from profiling.metadata import is_missing
from profiling.engine import to_number


def missing_heatmap(df, path):
    grid = pd.DataFrame({c: [1 if is_missing(v) else 0 for v in df[c]] for c in df.columns})
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(grid.values, aspect="auto", cmap="Reds", interpolation="nearest")
    ax.set_xticks(range(len(grid.columns)))
    ax.set_xticklabels(grid.columns, rotation=60, ha="right")
    ax.set_ylabel("row")
    ax.set_title("Missing values (red = missing)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def correlation_heatmap(df, columns, path):
    nums = pd.DataFrame({c: df[c].map(to_number) for c in columns})
    corr = nums.corr()
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(columns, rotation=45, ha="right")
    ax.set_yticks(range(len(columns)))
    ax.set_yticklabels(columns)
    for i in range(len(columns)):
        for j in range(len(columns)):
            ax.text(j, i, round(corr.values[i][j], 2), ha="center", va="center")
    fig.colorbar(im)
    ax.set_title("Correlation of stream columns")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def outlier_plot(df, columns, path):
    nums = pd.DataFrame({c: df[c].map(to_number) for c in columns})
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.boxplot([nums[c].dropna() for c in columns])
    ax.set_xticklabels(columns)
    ax.set_title("Outlier distribution (streams, millions)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
