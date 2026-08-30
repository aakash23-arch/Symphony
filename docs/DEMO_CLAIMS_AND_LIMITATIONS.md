# Demo Claims and Limitations

This document serves as the canonical record of truthfulness, scope, and limitations for the Voice Shield internal demonstration. It is designed to explicitly clarify the boundaries of this prototype to evaluation panels, technical judges, and internal stakeholders.

## Core Distinctions

This system strictly distinguishes between what is implemented in this repository and what belongs to a production target state. The following definitions apply to all claims made about this system:

- **REAL IMPLEMENTATION**: The code, models, and UI that actually execute in this repository when started. This includes the L1-L5 analysis pipeline, the PyTorch model inference loop (for available models), and the React frontend.
- **SIMULATION**: Behavior that acts realistically but is driven by deterministic logic rather than external systems. This includes the transaction state machine, which simulates a core banking integration without moving funds.
- **DEMO FIXTURE**: Pre-recorded, offline assets used to ensure a reliable and repeatable demonstration environment. This includes the `clean_speechlike.wav` and `noisy_speechlike.wav` audio fixtures used during scenarios.
- **FUTURE INTEGRATION**: Architectural capabilities designed into the system (e.g., SIP/RTP telecom endpoints, external banking APIs, full Kubernetes deployment) that are deliberately excluded from this internal prototype.

## Limitations and Exclusions

To ensure absolute integrity during evaluation, the following limitations are explicitly declared:

### 1. No Production Deployment
This repository represents an internal prototype. It is not configured for production deployment. The use of Docker Compose, SQLite, and a local Vite dev server are for demonstration ease, not a scalable architecture.

### 2. No Real Telecom Integration
The system ingests audio via a WebSocket endpoint and processes it from a ring buffer. It does **not** integrate with a real telecom carrier (no SIP/RTP gateways or VoIP infrastructure). The audio ingestion boundary is simulated using DEMO FIXTURE files.

### 3. No Real Banking Integration or Financial Execution
The transaction panel and risk actions are a SIMULATION. The system does **not** connect to any external banking system, core banking platform, or payment gateway. No real funds are moved. The transaction simulator demonstrates how the security layer *would* communicate with such a system.

### 4. Model Capabilities and Accuracy
- **No Accuracy Claim**: No accuracy, EER (Equal Error Rate), or detection-rate figures are claimed. No evaluation dataset exists in this workspace.
- **No Guaranteed Detection or Zero False Positives/Negatives**: The models are capable of producing both false positives and false negatives. The L4 fusion layer and L5 policy engine are explicitly designed to handle uncertainty, falling back to a `STEP_UP` verification action when confidence is low.
- **No Calibrated Probability**: The risk scores output by the system are heuristic combinations of model confidence and contextual flags, not strictly calibrated probabilities.

### 5. No Universal Multilingual Support
While the system processes acoustic features that are generally language-agnostic, the current implementation and demo scenarios are tested strictly against the provided English/Hindi test fixtures. Universal multilingual support is a FUTURE INTEGRATION.

### 6. No Regulatory Certification
This prototype has not undergone compliance auditing, security penetration testing, or regulatory certification.
