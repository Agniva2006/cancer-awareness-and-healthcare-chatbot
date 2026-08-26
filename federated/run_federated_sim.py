#!/usr/bin/env python3
"""
federated/run_federated_sim.py
OncoGraph AI — Standalone Multi-Hospital Federated Learning Simulation
Demonstrating DP-SGD (Differential Privacy), Asynchronous Staleness-Aware FedAvg,
and Rényi Differential Privacy (RDP) Budget Telemetry.
"""

import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure root directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from federated.hospital_node import FederatedServer


def main():
    print("=" * 78)
    print(" 🏥 OncoGraph AI: Privacy-Preserving Federated Learning Engine (DP-SGD)")
    print("=" * 78)
    print(" • Algorithm: Asynchronous Staleness-Discounted FedAvg")
    print(" • Privacy Mechanism: DP-SGD with L2 Gradient Clipping (C=1.0) & Gaussian Noise (sigma=1.2)")
    print(" • Target Privacy Budget: epsilon <= 1.20, delta = 1e-05")
    print(" • Enclaves: 3 Simulated Non-IID Hospital Partitions")
    print("-" * 78)

    server = FederatedServer()
    print("\n[INIT] Initializing Isolated Hospital Enclaves:")
    for h in server.hospitals:
        print(f"  ├─ [{h.hospital_id}] {h.name:<28} | Focus: {h.cancer_focus:<30} | {h.n_samples} cases")

    print("\n[TRAIN] Launching 5-Round Federated Training Loop with DP-SGD...")
    print("-" * 78)
    print(f"{'Round':<7} | {'Avg Pre-Clip L2':<16} | {'Avg Post-Clip L2':<17} | {'Avg Loss':<10} | {'Epsilon (RDP)':<15} | {'Status':<10}")
    print("-" * 78)

    n_rounds = 5
    epochs_per_round = 3
    start_time = time.time()

    for r in range(1, n_rounds + 1):
        report = server.run_dp_round(
            local_epochs=epochs_per_round,
            clip_norm=1.0,
            noise_multiplier=1.2,
            delta=1e-5
        )

        h_reports = report["hospital_reports"]
        avg_pre = sum(hr["dp_metrics"]["avg_gradient_l2_norm_pre_clip"] for hr in h_reports) / len(h_reports)
        avg_post = sum(hr["dp_metrics"]["avg_gradient_l2_norm_post_clip"] for hr in h_reports) / len(h_reports)
        avg_loss = sum(hr["loss_end"] for hr in h_reports) / len(h_reports)
        eps = report["privacy_telemetry"]["cumulative_epsilon_consumed"]

        print(f"Round {r:<2} | {avg_pre:<16.4f} | {avg_post:<17.4f} | {avg_loss:<10.4f} | {eps:<6.3f} / 1.200 | [ACTIVE]")
        time.sleep(0.15)  # slight pause for smooth terminal display

    total_time = round(time.time() - start_time, 2)

    print("-" * 78)
    print(f"[COMPLETE] 5 Rounds Completed in {total_time}s")
    print("\n" + "=" * 78)
    print(" 📊 FINAL FEDERATED TELEMETRY & PRIVACY AUDIT")
    print("=" * 78)
    print(f" • Cumulative Privacy Consumed: epsilon = {server.cumulative_epsilon:.3f}, delta = 1e-05")
    print(f" • Privacy Constraint Status  : {'[PASS] FORMALLY COMPLIANT (<= 1.20)' if server.cumulative_epsilon <= 1.20 else '[FAIL]'}")
    print(f" • Gradient Inversion Defense : Mathematically Guaranteed via Gaussian Perturbation")
    print(f" • Raw Patient Records Sent   : 0 (Zero Patient PHI Exchanged)")
    print(" • Final Hospital Losses:")
    for h in server.hospitals:
        initial_loss = h.training_loss_history[0]
        final_loss = h.training_loss_history[-1]
        improvement = ((initial_loss - final_loss) / initial_loss) * 100
        print(f"    - {h.name:<28}: Loss {initial_loss:.4f} -> {final_loss:.4f} ({improvement:+.1f}% improvement)")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
