"""Architectural import boundary tests enforcing the module dependency DAG (§5)."""

import ast
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent / "backend" / "voiceshield"

FORBIDDEN_IMPORTS = {
    # Layer 1 (Ingestion) must not import higher layers
    "ingestion": ["signal_processing", "models", "fusion", "context", "risk", "decision", "assurance"],
    # Layer 2 (Signal Processing) must not import higher layers
    "signal_processing": ["models", "fusion", "context", "risk", "decision", "assurance"],
    # Layer 3 (Models) must not import decision/fusion/assurance
    "models": ["fusion", "context", "risk", "decision", "assurance"],
    # Orchestration composes every analysis layer, which is precisely why it
    # must never reach UP into transport. It may import the layers below it
    # (including transactions, for L5 action dispatch); it may not import api.
    "orchestration": ["api", "demo"],
    # The demo transaction environment is a leaf: it must not reach back into
    # the analysis stack. It exists to be acted upon by L5, not to inspect audio.
    "transactions": [
        "ingestion",
        "signal_processing",
        "models",
        "fusion",
        "context",
        "risk",
        "decision",
        "assurance",
        "api",
    ],
    # Contracts must not import application logic modules
    "contracts": [
        "voiceshield.ingestion",
        "voiceshield.signal_processing",
        "voiceshield.models",
        "voiceshield.fusion",
        "voiceshield.context",
        "voiceshield.risk",
        "voiceshield.decision",
        "voiceshield.assurance",
        "voiceshield.api",
        "voiceshield.demo",
        "voiceshield.transactions",
        "voiceshield.orchestration",
    ],
}


def test_layer_isolation_rules():
    """Verify that no module imports forbidden higher-layer modules."""
    for module_dir, forbidden_targets in FORBIDDEN_IMPORTS.items():
        module_path = BACKEND_ROOT / module_dir
        if not module_path.exists():
            continue

        for py_file in module_path.glob("**/*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in forbidden_targets:
                            target = forbidden if forbidden.startswith("voiceshield.") else f"voiceshield.{forbidden}"
                            assert not alias.name.startswith(target), (
                                f"Architectural violation in {py_file}: imports forbidden module '{alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        for forbidden in forbidden_targets:
                            target = forbidden if forbidden.startswith("voiceshield.") else f"voiceshield.{forbidden}"
                            assert not node.module.startswith(target), (
                                f"Architectural violation in {py_file}: imports from forbidden module '{node.module}'"
                            )



# --- ML library isolation (L3) --------------------------------------------------
#
# The L3 requirement is that "the UI and risk engine never depend directly on a
# specific ML library." That is enforced structurally: only the adapter package
# may import torch or transformers. Everything else talks to the protocols in
# models/interfaces.py.

ML_LIBRARIES = {"torch", "transformers", "torchaudio", "speechbrain", "onnxruntime"}

#: The only modules permitted to import an ML library.
ML_ALLOWED_SUFFIXES = (
    ("models", "adapters"),
    ("models", "runtime.py"),
)


def _imports_ml_library(tree):
    """Return the set of ML libraries imported at any depth in a module."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in ML_LIBRARIES:
                    found.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                root = node.module.split(".")[0]
                if root in ML_LIBRARIES:
                    found.add(root)
    return found


def _is_ml_allowed(py_file):
    parts = py_file.parts
    return "adapters" in parts or py_file.name == "runtime.py"


def test_experts_do_not_import_ml_libraries():
    """Experts, registry and interfaces must stay ML-library agnostic."""
    models_path = BACKEND_ROOT / "models"
    if not models_path.exists():
        return

    for py_file in models_path.glob("**/*.py"):
        if _is_ml_allowed(py_file):
            continue
        with open(py_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        found = _imports_ml_library(tree)
        assert not found, (
            f"ML library isolation violated in {py_file}: imports {sorted(found)}. "
            "Only models/adapters/ and models/runtime.py may touch an ML library."
        )


def test_evidence_and_contracts_are_ml_free():
    """The evidence and contract layers must never import an ML library."""
    for module_dir in ("evidence", "contracts", "speaker", "transactions"):
        module_path = BACKEND_ROOT / module_dir
        if not module_path.exists():
            continue
        for py_file in module_path.glob("**/*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
            found = _imports_ml_library(tree)
            assert not found, f"{py_file} imports {sorted(found)}"


def test_models_package_imports_without_torch():
    """Importing L3 must not require an ML stack (availability must stay truthful)."""
    import importlib

    module = importlib.import_module("voiceshield.models")
    assert hasattr(module, "ExpertRegistry")
    assert hasattr(module, "AntiSpoofingModel")
