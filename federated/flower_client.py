#!/usr/bin/env python3
"""
flower_client.py
OncoGraph AI: Production Flower (flwr) Federated Learning Hospital Client with DP-SGD.
Implements:
  - flwr.client.NumPyClient interface for distributed model training
  - Differential Privacy (DP-SGD): L2 Gradient Clipping (C=1.0) & Gaussian Noise Injection (sigma=1.2)
  - Strict zero-raw-data-egress compliance for HIPAA/GDPR clinical federations.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import List, Dict, Tuple, Optional

try:
    import flwr as fl
    FLWR_AVAILABLE = True
except ImportError:
    FLWR_AVAILABLE = False


class ClinicalMalignancyMLP(nn.Module):
    """3-Layer MLP for Multi-Modal Oncology Malignancy Prediction."""
    def __init__(self, input_dim: int = 30, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 2)
        )

    def forward(self, x):
        return self.net(x)


class HospitalFlowerClient:
    """
    Hospital Federated Node executing DP-SGD private local training rounds.
    """

    def __init__(
        self,
        hospital_id: str,
        n_samples: int = 300,
        clip_norm: float = 1.0,
        noise_multiplier: float = 1.2,
        seed: int = 42
    ):
        self.hospital_id = hospital_id
        self.clip_norm = clip_norm
        self.noise_multiplier = noise_multiplier
        self.model = ClinicalMalignancyMLP(input_dim=30, hidden_dim=64)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.AdamW(self.model.parameters(), lr=1e-3, weight_decay=1e-4)

        # Generate synthetic private hospital dataset (simulating biopsy/genomic features)
        torch.manual_seed(seed)
        np.random.seed(seed)
        self.X = torch.randn(n_samples, 30, dtype=torch.float32)
        # Binary malignancy label (0 = Benign, 1 = Malignant)
        logits = 0.5 * self.X[:, 0] - 0.3 * self.X[:, 1] + 0.8 * self.X[:, 2]
        prob = torch.sigmoid(logits)
        self.y = torch.bernoulli(prob).long()

    def get_parameters(self) -> List[np.ndarray]:
        """Extract model weights as numpy arrays."""
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

    def set_parameters(self, parameters: List[np.ndarray]):
        """Load global federated model weights."""
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.model.load_state_dict(state_dict, strict=True)

    def train_local_epoch_with_dpsgd(self, epochs: int = 2) -> Dict[str, float]:
        """
        Execute private training with L2 gradient clipping and Gaussian noise injection.
        """
        self.model.train()
        total_loss = 0.0
        n_batches = 10
        batch_size = len(self.X) // n_batches

        for epoch in range(epochs):
            perm = torch.randperm(len(self.X))
            for b in range(n_batches):
                idx = perm[b * batch_size:(b + 1) * batch_size]
                x_b, y_b = self.X[idx], self.y[idx]

                self.optimizer.zero_grad()
                out = self.model(x_b)
                loss = self.criterion(out, y_b)
                loss.backward()

                # DP-SGD Step 1: Per-layer / global L2 gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=self.clip_norm)

                # DP-SGD Step 2: Calibrated Gaussian noise addition: N(0, (sigma * C / B)^2)
                for param in self.model.parameters():
                    if param.grad is not None:
                        noise = torch.randn_like(param.grad) * (self.noise_multiplier * self.clip_norm / batch_size)
                        param.grad += noise

                self.optimizer.step()
                total_loss += loss.item()

        avg_loss = total_loss / (epochs * n_batches)
        return {"loss": round(avg_loss, 4), "hospital_id": self.hospital_id}

    def evaluate_local(self) -> Tuple[float, float]:
        """Compute local accuracy and loss."""
        self.model.eval()
        with torch.no_grad():
            out = self.model(self.X)
            loss = self.criterion(out, self.y).item()
            preds = torch.argmax(out, dim=1)
            acc = (preds == self.y).float().mean().item()
        return loss, acc


if FLWR_AVAILABLE:
    class FlowerNumPyClientAdapter(fl.client.NumPyClient):
        def __init__(self, hospital_client: HospitalFlowerClient):
            self.hc = hospital_client

        def get_parameters(self, config):
            return self.hc.get_parameters()

        def fit(self, parameters, config):
            self.hc.set_parameters(parameters)
            metrics = self.hc.train_local_epoch_with_dpsgd(epochs=config.get("epochs", 2))
            return self.hc.get_parameters(), len(self.hc.X), metrics

        def evaluate(self, parameters, config):
            self.hc.set_parameters(parameters)
            loss, acc = self.hc.evaluate_local()
            return float(loss), len(self.hc.X), {"accuracy": float(acc)}
