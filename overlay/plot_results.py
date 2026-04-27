"""Visualize benchmark results from CSV files."""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# --- Load CSVs ---
df_board = None
df_laptop = None
df_power = None

if os.path.exists("results/bench_fpga_results.csv"):
    df_board = pd.read_csv("results/bench_fpga_results.csv")
    print(f"Loaded bench_fpga_results.csv: {len(df_board)} rows")

if os.path.exists("results/bench_cpu_results.csv"):
    df_laptop = pd.read_csv("results/bench_cpu_results.csv")
    print(f"Loaded bench_cpu_results.csv: {len(df_laptop)} rows")

if os.path.exists("results/bench_power_results.csv"):
    df_power = pd.read_csv("results/bench_power_results.csv")
    print(f"Loaded bench_power_results.csv: {len(df_power)} rows")

if df_board is None and df_laptop is None:
    print("No CSV files found. Run the benchmarks first.")
    exit(1)
print()


def save_and_show(fig, name):
    fig.tight_layout()
    path = os.path.join("plots", name)
    fig.savefig(path, dpi=150)
    print(f"Saved {path}")
    plt.show()


# ==========================================================
# Plot 1: Board — ARM NumPy, ARM Python loop, FPGA
# ==========================================================
if df_board is not None:
    fig, ax = plt.subplots(figsize=(10, 6))
    max_runs = df_board["n_runs"].max()
    subset = df_board[df_board["n_runs"] == max_runs]

    for method, color, marker in [("FPGA (DMA)", "#4CAF50", "D"),
                                   ("CPU NumPy", "#2196F3", "o"),
                                   ("CPU Python loop", "#FF9800", "s")]:
        data = subset[subset["method"] == method].sort_values("array_size")
        if not data.empty:
            label = f"ARM {method}" if "CPU" in method else "FPGA DMA"
            ax.plot(data["array_size"], data["median_us"],
                    marker=marker, color=color, linewidth=2, markersize=8,
                    label=label)

    ax.set_xlabel("Array size")
    ax.set_ylabel("Median latency (us)")
    ax.set_title(f"Board (Ultra96-V2) — Latency vs Array Size (n_runs={max_runs})")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_and_show(fig, "plot_board_latency.png")

# ==========================================================
# Plot 2: Laptop — Intel NumPy, Intel Python loop
# ==========================================================
if df_laptop is not None:
    fig, ax = plt.subplots(figsize=(10, 6))
    max_runs = df_laptop["n_runs"].max()
    subset = df_laptop[df_laptop["n_runs"] == max_runs]

    for method, color, marker in [("CPU NumPy", "#2196F3", "o"),
                                   ("CPU Python loop", "#FF9800", "s")]:
        data = subset[subset["method"] == method].sort_values("array_size")
        if not data.empty:
            ax.plot(data["array_size"], data["median_us"],
                    marker=marker, color=color, linewidth=2, markersize=8,
                    label=f"Intel {method}")

    ax.set_xlabel("Array size")
    ax.set_ylabel("Median latency (us)")
    ax.set_title(f"Laptop (Intel i7) — Latency vs Array Size (n_runs={max_runs})")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_and_show(fig, "plot_laptop_latency.png")

# ==========================================================
# Plot 3: All 5 methods combined
# ==========================================================
if df_board is not None and df_laptop is not None:
    fig, ax = plt.subplots(figsize=(12, 6))
    board_max = df_board["n_runs"].max()
    laptop_max = df_laptop["n_runs"].max()

    # Board methods (solid lines)
    for method, color, marker in [("FPGA (DMA)", "#4CAF50", "D"),
                                   ("CPU NumPy", "#2196F3", "o"),
                                   ("CPU Python loop", "#FF9800", "s")]:
        data = df_board[(df_board["n_runs"] == board_max) &
                        (df_board["method"] == method)].sort_values("array_size")
        if not data.empty:
            label = f"Board ARM {method}" if "CPU" in method else "Board FPGA DMA"
            ax.plot(data["array_size"], data["median_us"],
                    marker=marker, color=color, linewidth=2, markersize=8,
                    linestyle="-", label=label)

    # Laptop CPU methods (dashed lines)
    for method, color, marker in [("CPU NumPy", "#2196F3", "^"),
                                   ("CPU Python loop", "#FF9800", "v")]:
        data = df_laptop[(df_laptop["n_runs"] == laptop_max) &
                         (df_laptop["method"] == method)].sort_values("array_size")
        if not data.empty:
            ax.plot(data["array_size"], data["median_us"],
                    marker=marker, color=color, linewidth=2, markersize=8,
                    linestyle="--", label=f"Laptop Intel {method}")

    ax.set_xlabel("Array size")
    ax.set_ylabel("Median latency (us)")
    ax.set_title("All Platforms — Latency vs Array Size")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    save_and_show(fig, "plot_all_platforms.png")

# ==========================================================
# Plot 4: Power (board only)
# ==========================================================
if df_power is not None:
    fig, ax = plt.subplots(figsize=(8, 5))

    methods = df_power["method"].tolist()
    idle = df_power["idle_w"].values[0]
    active = df_power["active_w"].tolist()
    delta = df_power["delta_w"].tolist()

    colors_pwr = ["#4CAF50" if "FPGA" in m else
                  "#2196F3" if "NumPy" in m else
                  "#FF9800" for m in methods]

    x = np.arange(len(methods))
    width = 0.35
    bars1 = ax.bar(x - width/2, [idle] * len(methods), width,
                   label="Idle", color="#BDBDBD")
    bars2 = ax.bar(x + width/2, active, width,
                   label="Active", color=colors_pwr)

    ax.set_ylabel("Power (W)")
    ax.set_title("Board Power — Idle vs Active (2s measurement window)")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=10)
    ax.legend()
    ax.bar_label(bars1, fmt="%.3f", fontsize=8)
    ax.bar_label(bars2, fmt="%.3f", fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    save_and_show(fig, "plot_power.png")

print("\nAll plots saved.")
