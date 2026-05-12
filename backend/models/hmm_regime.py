"""
Hidden Markov Model for Argentine real estate market regime detection.

Architecture: 3-state Gaussian HMM trained **unsupervised** on three
data-driven features:
  1. quarterly CABA USD/m² price change (z-scored)
  2. annual transaction-volume YoY change, propagated quarterly (z-scored)
  3. composite macro stress index = z(inflation) + z(FX YoY) + z(BCRA rate)

State labels (Crisis / Recovery / Boom) are assigned *post-training* by
mapping each fitted state to the hand-annotated regime that best matches
its observation history via the Hungarian (linear-assignment) algorithm.
The hand labels are used ONLY for naming the states — they never enter
the likelihood. The pre-fit-vs-hand-label agreement rate is exported as
a diagnostic the frontend can surface.

If hmmlearn is unavailable (fresh clone, no pip install), the model
degrades to a fully data-driven k-means clustering on the same feature
matrix, with the same Hungarian post-hoc labeling — still data-driven,
just without Markov dynamics.
"""

from __future__ import annotations

import json
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.optimize import linear_sum_assignment

from .calibration_data import CalibrationData

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=UserWarning)

try:
    from hmmlearn import hmm

    HMM_AVAILABLE = True
except ImportError:  # pragma: no cover
    HMM_AVAILABLE = False

# Where the trained HMM persists its diagnostics for the API to surface.
_DIAG_PATH = Path(__file__).parent / "diagnostics" / "hmm_diagnostics.json"


@dataclass
class RegimeState:
    """Market regime state information."""

    regime: str
    probability: float
    description: str


class HMMRegimeDetector:
    """
    Unsupervised Markov regime detector with post-hoc semantic labeling.
    """

    REGIME_NAMES = {0: "crisis", 1: "recovery", 2: "boom"}

    REGIME_DESCRIPTIONS = {
        "crisis": "Capital flight, restricted credit access, transaction volume collapse",
        "recovery": "Credit restoration, volume growth, price stabilization",
        "boom": "Speculative investment, rapid price appreciation, policy risks",
    }

    def __init__(self, calibration_data: CalibrationData):
        self.calibration_data = calibration_data
        self.scaler = StandardScaler()
        self.model: Optional[Any] = None  # hmmlearn GaussianHMM
        self.kmeans_fallback: Optional[KMeans] = None
        self.is_trained = False
        self.training_method: str = "unfitted"

        # Filled in by train(): how the model's raw cluster IDs map onto
        # the semantic Crisis/Recovery/Boom labels.
        self.state_to_regime: Dict[int, int] = {0: 0, 1: 1, 2: 2}

        # Diagnostic artefacts produced by training.
        self.transition_matrix: Optional[np.ndarray] = None
        self.fitted_state_sequence: Optional[np.ndarray] = None
        self.label_agreement_rate: Optional[float] = None
        self.diagnostics: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self) -> bool:
        """
        Fit the regime detector on real historical features.

        Returns True iff a Gaussian HMM was fitted; False indicates the
        k-means fallback path was used (still data-driven).
        """
        training_data = self.calibration_data.get_regime_training_data()
        features: np.ndarray = training_data["features"]  # already z-scored
        hand_labels: np.ndarray = training_data["regime_labels"]
        quarters: List[str] = list(training_data["quarters"])

        # We standardize a second time defensively — z-scoring twice is
        # idempotent up to rounding, but means downstream consumers don't
        # need to know whether features were pre-scaled.
        features_scaled = self.scaler.fit_transform(features)

        if HMM_AVAILABLE:
            success = self._fit_hmm(features_scaled, hand_labels, quarters)
            if success:
                self.is_trained = True
                self._persist_diagnostics(features_scaled)
                return True

        # Fallback: k-means on the same features. We still produce a
        # transition matrix by counting empirical transitions in the
        # resulting state sequence — that gives the Markov layer something
        # non-trivial to surface even without hmmlearn.
        self._fit_kmeans(features_scaled, hand_labels, quarters)
        self.is_trained = True
        self._persist_diagnostics(features_scaled)
        return False

    def _fit_hmm(
        self,
        features: np.ndarray,
        hand_labels: np.ndarray,
        quarters: List[str],
    ) -> bool:
        """Fit the unsupervised Gaussian HMM. Returns success flag."""
        try:
            # Multiple random initialisations — pick the one with the best
            # log-likelihood. Single-init Gaussian HMM is brittle on small
            # samples like ours (n=32).
            best_model = None
            best_score = -np.inf
            for seed in (7, 13, 21, 42, 99):
                candidate = hmm.GaussianHMM(
                    n_components=3,
                    covariance_type="diag",  # diag is more stable than full for n=32
                    n_iter=200,
                    tol=1e-3,
                    random_state=seed,
                )
                try:
                    candidate.fit(features)
                    score = candidate.score(features)
                    if score > best_score and np.isfinite(score):
                        best_score = score
                        best_model = candidate
                except Exception as exc:  # pragma: no cover
                    logger.debug("HMM init seed=%d failed: %s", seed, exc)

            if best_model is None:
                return False

            self.model = best_model
            self.training_method = "hmm_unsupervised"

            # Viterbi state sequence over the training data.
            raw_states = best_model.predict(features)
            self.fitted_state_sequence = raw_states

            # Hungarian-align raw states to {Crisis, Recovery, Boom} so the
            # regime names mean the same thing across runs / seeds.
            self.state_to_regime = self._align_states_to_labels(
                raw_states, hand_labels
            )

            # Permute transition matrix accordingly.
            self.transition_matrix = self._reorder_transition_matrix(
                best_model.transmat_, self.state_to_regime
            )

            # Diagnostic: agreement vs hand labels.
            aligned = np.array([self.state_to_regime[s] for s in raw_states])
            self.label_agreement_rate = float(np.mean(aligned == hand_labels))

            self.diagnostics = {
                "training_method": self.training_method,
                "n_observations": int(len(features)),
                "n_states": 3,
                "log_likelihood": float(best_score),
                "label_agreement_rate": self.label_agreement_rate,
                "transition_matrix": self.transition_matrix.tolist(),
                "state_sequence": [
                    {"quarter": q, "fitted_state": int(s), "regime": self.REGIME_NAMES[self.state_to_regime[int(s)]]}
                    for q, s in zip(quarters, raw_states)
                ],
                "feature_names": ["price_change_z", "volume_yoy_z", "macro_stress_z"],
                "state_means_aligned": self._aligned_state_means(best_model.means_),
            }
            return True

        except Exception as exc:  # pragma: no cover
            logger.warning("HMM fit failed: %s", exc)
            return False

    def _fit_kmeans(
        self,
        features: np.ndarray,
        hand_labels: np.ndarray,
        quarters: List[str],
    ) -> None:
        """Fall-back: k=3 clusters on real features. No Markov dynamics."""
        km = KMeans(n_clusters=3, n_init=10, random_state=42).fit(features)
        self.kmeans_fallback = km
        self.training_method = "kmeans_unsupervised"
        raw_states = km.labels_
        self.fitted_state_sequence = raw_states
        self.state_to_regime = self._align_states_to_labels(raw_states, hand_labels)

        # Empirical transition matrix from the assigned state sequence —
        # so even the k-means path gets a 3x3 Markov layer.
        emp = np.zeros((3, 3))
        aligned = np.array([self.state_to_regime[s] for s in raw_states])
        for i in range(len(aligned) - 1):
            emp[aligned[i], aligned[i + 1]] += 1
        row_sums = emp.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        self.transition_matrix = emp / row_sums

        self.label_agreement_rate = float(np.mean(aligned == hand_labels))
        self.diagnostics = {
            "training_method": self.training_method,
            "n_observations": int(len(features)),
            "n_states": 3,
            "log_likelihood": None,
            "label_agreement_rate": self.label_agreement_rate,
            "transition_matrix": self.transition_matrix.tolist(),
            "state_sequence": [
                {"quarter": q, "fitted_state": int(s), "regime": self.REGIME_NAMES[self.state_to_regime[int(s)]]}
                for q, s in zip(quarters, raw_states)
            ],
            "feature_names": ["price_change_z", "volume_yoy_z", "macro_stress_z"],
            "state_means_aligned": self._aligned_state_means(km.cluster_centers_),
        }

    @staticmethod
    def _align_states_to_labels(
        raw_states: np.ndarray, hand_labels: np.ndarray
    ) -> Dict[int, int]:
        """
        Solve the assignment problem: map each fitted state ∈ {0,1,2} to a
        regime label ∈ {0,1,2} maximising overlap with hand annotations.

        This is the standard cluster-label-alignment via Hungarian — we
        cost the assignment with NEGATIVE overlap and minimise.
        """
        cost = np.zeros((3, 3), dtype=int)
        for fitted in range(3):
            for regime in range(3):
                cost[fitted, regime] = -int(
                    np.sum((raw_states == fitted) & (hand_labels == regime))
                )
        row_ind, col_ind = linear_sum_assignment(cost)
        return {int(r): int(c) for r, c in zip(row_ind, col_ind)}

    @staticmethod
    def _reorder_transition_matrix(
        transmat: np.ndarray, state_to_regime: Dict[int, int]
    ) -> np.ndarray:
        """Permute rows+cols so the matrix is indexed by regime not raw state."""
        perm = np.zeros((3, 3))
        for raw_from in range(3):
            for raw_to in range(3):
                perm[state_to_regime[raw_from], state_to_regime[raw_to]] = transmat[
                    raw_from, raw_to
                ]
        return perm

    def _aligned_state_means(self, raw_means: np.ndarray) -> Dict[str, List[float]]:
        """Return each regime's z-scored feature centroid for diagnostics."""
        aligned: Dict[str, List[float]] = {}
        for raw_state, regime_idx in self.state_to_regime.items():
            regime_name = self.REGIME_NAMES[regime_idx]
            aligned[regime_name] = [float(v) for v in raw_means[raw_state]]
        return aligned

    def _persist_diagnostics(self, features: np.ndarray) -> None:
        """Write the diagnostics blob so the API and UI can read it."""
        _ = features
        try:
            _DIAG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _DIAG_PATH.write_text(json.dumps(self.diagnostics, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to persist HMM diagnostics: %s", exc)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def detect_current_regime(self) -> Dict[str, Any]:
        """
        Posterior over Crisis/Recovery/Boom at the most recent training
        quarter. This is the live forecast service's primary entry point.
        """
        if not self.is_trained:
            self.train()

        # Use the fitted state sequence's tail. Since the training matrix
        # already includes 2026Q1, the "current" quarter is the last row.
        features_full = self.scaler.transform(
            self.calibration_data.get_regime_training_data()["features"]
        )

        if self.model is not None:
            # hmmlearn predict_proba returns the smoothed posterior over
            # states at each timestep — robust and correct for a single
            # current observation in the context of full history.
            posteriors = self.model.predict_proba(features_full)
            last_post = posteriors[-1]  # 3-vector summing to 1
            # Permute into regime order.
            regime_probs = np.zeros(3)
            for raw_state, regime_idx in self.state_to_regime.items():
                regime_probs[regime_idx] = last_post[raw_state]
        elif self.kmeans_fallback is not None:
            # k-means: posterior is one-hot at the last quarter.
            last_raw = int(self.kmeans_fallback.labels_[-1])
            regime_probs = np.zeros(3)
            regime_probs[self.state_to_regime[last_raw]] = 1.0
        else:
            regime_probs = np.array([0.10, 0.80, 0.10])

        regime_idx = int(np.argmax(regime_probs))
        regime_name = self.REGIME_NAMES[regime_idx]
        confidence = float(regime_probs[regime_idx])

        # Build the named transition row.
        if self.transition_matrix is not None:
            row = self.transition_matrix[regime_idx]
        else:
            row = np.array([0.10, 0.80, 0.10])
        transitions: Dict[str, float] = {}
        for to_regime_idx, to_name in self.REGIME_NAMES.items():
            key = f"remain_{regime_name}" if to_regime_idx == regime_idx else f"transition_to_{to_name}"
            transitions[key] = float(row[to_regime_idx])

        current_context = self.calibration_data.get_current_market_context()

        return {
            "current_regime": regime_name,
            "regime_probability": confidence,
            "regime_state_id": regime_idx,
            "regime_posterior": {
                self.REGIME_NAMES[i]: float(regime_probs[i]) for i in range(3)
            },
            "description": self.REGIME_DESCRIPTIONS[regime_name],
            "transition_probabilities": transitions,
            "training_method": self.training_method,
            "label_agreement_rate": self.label_agreement_rate,
            "context_indicators": {
                "transaction_volume_yoy": current_context.get(
                    "latest_transaction_volume_yoy", 0
                ),
                "price_change_yoy": current_context.get("latest_price_change_yoy", 0),
                "inflation_monthly": current_context.get("current_inflation_monthly", 0),
                "bcra_rate": current_context.get("current_bcra_rate", 0),
            },
        }

    def get_regime_history(self) -> List[Dict[str, Any]]:
        """
        Return the fitted regime sequence — one entry per training quarter,
        with the model's own state assignment (not the hand label).
        """
        if not self.is_trained:
            self.train()
        seq = self.diagnostics.get("state_sequence", [])
        # Add a 'probability' field for downstream rendering (constant for
        # k-means; proper smoothed posterior for HMM).
        out: List[Dict[str, Any]] = []
        if self.model is not None:
            features_full = self.scaler.transform(
                self.calibration_data.get_regime_training_data()["features"]
            )
            posteriors = self.model.predict_proba(features_full)
            for entry, post in zip(seq, posteriors):
                regime_idx = next(
                    i for i, n in self.REGIME_NAMES.items() if n == entry["regime"]
                )
                # find raw state for that regime
                raw_state = next(
                    rs for rs, rg in self.state_to_regime.items() if rg == regime_idx
                )
                out.append(
                    {
                        "period": entry["quarter"],
                        "regime": entry["regime"],
                        "probability": float(post[raw_state]),
                    }
                )
            return out
        return [
            {"period": e["quarter"], "regime": e["regime"], "probability": 1.0}
            for e in seq
        ]

    def get_transition_matrix(self) -> Dict[str, Dict[str, float]]:
        if not self.is_trained:
            self.train()
        if self.transition_matrix is None:
            return {}
        out: Dict[str, Dict[str, float]] = {}
        for i, from_name in self.REGIME_NAMES.items():
            out[from_name] = {
                self.REGIME_NAMES[j]: float(self.transition_matrix[i, j]) for j in range(3)
            }
        return out

    def predict_regime_probabilities(self, horizon_quarters: int = 4) -> List[Dict[str, Any]]:
        """Iterate the transition matrix forward from today's posterior."""
        if not self.is_trained:
            self.train()
        current = self.detect_current_regime()
        probs = np.array(
            [
                current["regime_posterior"]["crisis"],
                current["regime_posterior"]["recovery"],
                current["regime_posterior"]["boom"],
            ]
        )
        T = self.transition_matrix if self.transition_matrix is not None else np.eye(3)
        forecast: List[Dict[str, Any]] = []
        for q in range(1, horizon_quarters + 1):
            probs = probs @ T
            forecast.append(
                {
                    "quarter": q,
                    "crisis_probability": float(probs[0]),
                    "recovery_probability": float(probs[1]),
                    "boom_probability": float(probs[2]),
                    "most_likely_regime": self.REGIME_NAMES[int(np.argmax(probs))],
                }
            )
        return forecast
