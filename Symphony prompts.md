# VoiceShield — Agent Build Prompt Sequence

**A controlled build program for Antigravity or Claude Code.**
Companion document to `VoiceShield_Symphony_Final_Architecture.md`.

---

## How to use this document

Treat this as a **controlled build program**, not one giant "build my app" prompt.

The objective is to make the agent do the implementation, testing, browser verification, and iterative correction while **you retain architectural control.**

**Do not give the agent unrestricted autonomy immediately.** High-autonomy modes ("Always Proceed"-style automatic terminal execution) are higher-risk; for a student project, use controlled approvals initially and increase autonomy only after the repository is stable.

**Do not give all 19 prompts at once.** Run them as **gates.** At each gate, the agent must **run and verify**, not merely write code.

```text
REQUIREMENTS
     ↓
ARCHITECTURE GATE
     ↓
STACK GATE
     ↓
SKELETON GATE
     ↓
INGESTION GATE
     ↓
DSP GATE
     ↓
ML GATE
     ↓
RISK GATE
     ↓
BACKEND GATE
     ↓
FRONTEND GATE
     ↓
DEMO GATE
     ↓
QA GATE
     ↓
JUDGE GATE
     ↓
REHEARSAL GATE
     ↓
                 READY
```

That is the difference between:

> "AI built our project."

and:

> **"We used an agentic engineering workflow to build, test, browser-verify and rehearse an executable vertical slice of the complete proposed architecture."**

---

## Before you start — the human workflow

1. Create a fresh Git repository, e.g. `voiceshield-demo/`
2. Create the requirement documents **before asking the agent to implement anything:**

```text
PS.md
SYMPHONY_REFERENCE.md
DEMO_SCOPE.md
ARCHITECTURE.md
TECH_STACK.md
DEMO_SCENARIOS.md
```

   - Your existing problem statement goes into `PS.md`.
   - Your existing Symphony document goes into `SYMPHONY_REFERENCE.md`.
3. Open the repository in the agent environment.
4. Give **Prompt 0**.
5. Review the resulting architecture artifact.
6. Correct anything that doesn't match your intended design.
7. Then progressively give the remaining prompts, one gate at a time.

---

## The two rules that must appear in every implementation prompt

> **Do not guess when the repository does not establish the answer. Inspect, verify, or explicitly report the ambiguity.**

> **Never claim that a command, test, model, API, or browser flow succeeded unless you actually executed and verified it.**

The first rule saves enormous amounts of debugging. The second matters because an agent can otherwise produce a convincing-looking implementation report without having genuinely exercised the complete application.

---

## The multi-agent operating model

Don't put everything into one conversation. Use separate focused agent conversations where useful.

```text
MASTER ARCHITECT
       │
       ├── Backend Agent
       ├── ML Agent
       ├── Frontend Agent
       ├── QA Agent
       └── Demo/Integration Agent
```

**But do not let them independently redesign interfaces. The architecture documents are the source of truth.**

Role framings for each agent:

- **Agent 1 — Architect:** *Read `ARCHITECTURE.md` and `PS.md`. Do not modify implementation. Produce the repository structure, interfaces, data contracts and implementation plan.*
- **Agent 2 — Backend:** *Implement the FastAPI backend exactly according to the architecture and data contracts. Do not invent new architectural layers. Add tests.*
- **Agent 3 — Audio/ML:** *Implement the ingestion, preprocessing, feature extraction, speaker verification and anti-spoofing pipeline. Create clean interfaces so models can be replaced independently.*
- **Agent 4 — Frontend:** *Build the dashboard from the defined API contracts. Do not create mock values except where the backend explicitly exposes demo simulation data.*
- **Agent 5 — QA:** *Run the complete application. Test the WebSocket stream, API endpoints, ML inference, risk transitions and UI. Identify failures and fix only verified problems.*

### Toolchain

**Primary — Google Antigravity:** architecture · coding · terminal · browser testing · debugging · multi-agent tasks. (Currently listed as available at no charge for developers.)

**Secondary — GitHub:** version control · issue tracking · backup · final repository.

**Optional — Cline:** a second agentic coding environment for difficult implementation/debugging tasks; open-source and model-agnostic, and still an active option per current 2026 comparisons.

**Do not** build the workflow around Continue — current 2026 sources indicate the project is winding down after acquisition.

**Local AI option — Ollama:** only if you want local models for experimentation. Don't sacrifice development quality merely to avoid API costs.

---

# GATE 0 — REQUIREMENTS AUDIT

## Prompt 0 — Establish the engineering contract

```text
You are the lead software architect and implementation engineer for this repository.

IMPORTANT:
Do not write application code yet.

First inspect every file currently present in the workspace.

The authoritative source documents are:

1. PS.md
2. SYMPHONY_REFERENCE.md
3. DEMO_SCOPE.md
4. ARCHITECTURE.md
5. TECH_STACK.md
6. DEMO_SCENARIOS.md

Treat these files as requirements documents.

Your task in this phase is ONLY to understand and audit the project.

Do NOT:
- invent requirements
- silently change architecture
- replace defined terminology
- add unnecessary technologies
- claim production functionality that is not implemented
- fabricate ML accuracy
- fabricate datasets
- fabricate real-time telecom integration
- fabricate banking integration
- create mock ML results disguised as real ML results

Separate every requirement into:

A. REQUIRED FOR THIS INTERNAL DEMO
B. REQUIRED BY THE ORIGINAL PROBLEM STATEMENT BUT DEFERRED
C. OPTIONAL FUTURE/PRODUCTION CAPABILITY
D. EXPLICITLY OUT OF SCOPE FOR THIS DEMO

Then produce an implementation-readiness report.

The report must identify:

- architecture
- components
- interfaces
- data contracts
- dependencies
- external software
- datasets/models required
- runtime requirements
- risks
- ambiguities
- items requiring a real implementation
- items that may legitimately be simulated for the demo

Do not modify source code.

Create:

docs/IMPLEMENTATION_READINESS.md

At the end, give me:
1. repository understanding
2. proposed implementation sequence
3. unresolved blockers
4. exact files that should be created next

STOP after producing the report.
```

**Do not let it code yet.** Review the artifact.

---

# GATE 1 — ARCHITECTURE

## Prompt 1 — Freeze the architecture

```text
Using the requirements and architecture documents already present, create the executable architecture specification for this internal-round demo.

Do not implement application features yet.

Create:

docs/EXECUTABLE_ARCHITECTURE.md

The document must define:

1. System boundaries
2. Components
3. Responsibilities of every component
4. Inputs and outputs
5. Data contracts
6. API contracts
7. WebSocket message contracts
8. ML inference contracts
9. Risk-engine contracts
10. Frontend/backend boundaries
11. Demo simulator boundary
12. Storage boundary
13. Error handling
14. Logging
15. Test strategy
16. Startup sequence
17. Shutdown sequence
18. Dependency graph
19. Runtime architecture
20. Demo execution flow

For every component explicitly state:

- what it does
- what it does NOT do
- what consumes its output
- what input it expects
- failure behavior
- test method

The architecture must remain modular.

The following logical layers MUST remain distinguishable:

L1 Audio Ingestion
L2 Signal Processing
L3 ML / Evidence Generation
L4 Voice Belief + Contextual Risk
L5 Decision + Output

The demo audio source must be replaceable later by SIP/RTP/VoIP ingestion without rewriting the downstream ML and decision layers.

Do not introduce microservices unless they provide a concrete benefit for this demo.

Do not add Kubernetes.

Do not add unnecessary cloud dependencies.

Do not create production claims.

STOP after producing the architecture document.
```

---

# GATE 2 — STACK

## Prompt 2 — Lock the technology stack

```text
Now create docs/EXECUTION_TECH_STACK.md.

Use the existing architecture as the authority.

Select the minimum technically credible stack required to execute the complete internal demo.

Preferred stack unless a concrete compatibility issue requires a change:

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Recharts

Backend:
- Python
- FastAPI
- Uvicorn
- Pydantic

Realtime:
- WebSocket

Audio:
- FFmpeg
- librosa
- soundfile
- NumPy
- SciPy

ML:
- PyTorch
- SpeechBrain where useful
- an appropriate anti-spoofing implementation/model

Testing:
- pytest
- Playwright

Storage:
- SQLite for demo persistence

Packaging:
- Docker Compose where practical

The technology stack must remain simple enough for a student team to run locally.

For every dependency specify:

- purpose
- version policy
- installation method
- whether it is mandatory
- whether it requires GPU
- whether it requires internet access
- whether it has licensing considerations
- fallback if unavailable

Do NOT invent package versions.

If a library/model/version cannot be verified from the available environment or official documentation, mark it as requiring verification rather than guessing.

Also produce:

docs/DEPENDENCY_MATRIX.md

with:
dependency | purpose | required | installation | verification command | fallback

Do not implement code yet.
```

*This prompt is what prevents the agent from casually installing 70 packages.*

---

# GATE 3 — SKELETON

## Prompt 3 — Build the repository skeleton

```text
Implement ONLY the repository foundation.

Create the directory structure defined in EXECUTABLE_ARCHITECTURE.md.

The repository must contain separate modules for:

- ingestion
- signal_processing
- models
- evidence
- speaker
- context
- risk
- decision
- API
- demo
- frontend
- tests
- configuration
- documentation

Do not implement fake ML logic.

Do not create hardcoded risk scores.

Do not create placeholder functions that silently return successful results.

Where implementation is not yet available, create explicit interfaces with clear NotImplementedError behavior and tests for the interfaces.

Create:

- README.md
- .gitignore
- .env.example
- backend requirements/configuration
- frontend package configuration
- pytest configuration
- basic health endpoint
- application configuration module
- logging configuration

Add:

GET /health

It must report application health and dependency readiness.

Do not add unnecessary infrastructure.

Run the backend test suite.

Run frontend type checking/build.

Fix all errors before stopping.

At the end report:

- files created
- commands executed
- tests executed
- test results
- unresolved issues

Do not claim success unless the commands actually succeeded.
```

---

# GATE 4 — INGESTION

## Prompt 4 — Build audio ingestion

```text
Implement Layer 1: Audio Ingestion.

Requirements:

1. Support prerecorded WAV input for deterministic demo execution.
2. Support microphone input if the local environment allows it.
3. Normalize incoming audio into the internal PCM representation defined by the architecture.
4. Implement configurable chunking.
5. Attach timestamps to every chunk.
6. Maintain stream/session identifiers.
7. Implement buffering.
8. Implement VAD.
9. Calculate basic audio quality indicators.
10. Produce the exact FrameObject contract defined in EXECUTABLE_ARCHITECTURE.md.
11. Expose a WebSocket stream interface for the frontend/demo.
12. Keep the source implementation independent from downstream ML.
13. Provide a simulator that can replay an audio file as if it were arriving in real time.
14. The simulator must preserve monotonically increasing timestamps.
15. It must support configurable playback speed for testing.
16. It must expose start/stop/error states.

Important:

Do not make the ingestion layer perform ML classification.

Do not generate synthetic detection scores here.

Do not hardcode the final risk result.

Add unit tests for:

- WAV loading
- normalization
- chunk generation
- timestamps
- buffering
- VAD
- invalid audio
- empty audio
- unsupported format
- stream termination
- WebSocket disconnect

Add one deterministic integration test that streams a small fixture audio file through the ingestion layer.

Run all tests.

Fix failures before stopping.
```

---

# GATE 5 — DSP

## Prompt 5 — Build the DSP layer

```text
Implement Layer 2: Signal Processing.

Use the architecture and data contracts already defined.

Implement:

1. audio normalization
2. resampling
3. log-mel spectrogram generation
4. MFCC extraction
5. RMS/energy
6. zero-crossing rate
7. pitch/F0 estimation where reliable
8. speaking-rate estimation
9. pause/silence statistics
10. basic prosodic features
11. spectral statistics
12. frame-level feature timestamps

Requirements:

- deterministic output
- configurable parameters
- no hidden global state
- clear typed interfaces
- graceful handling of poor-quality audio
- explicit handling of missing/invalid features
- unit-testable functions

Do NOT yet implement the final risk engine.

Do NOT fabricate feature values.

Do NOT hardcode a fake deepfake result.

Save feature extraction output in the internal EvidenceVector-compatible structure.

Create tests using local fixture audio.

Tests must verify:
- shape
- type
- timestamp alignment
- numerical validity
- silence handling
- noisy input handling
- short audio handling

Generate a small developer diagnostic that can render a spectrogram for a test fixture.

Run the complete backend test suite.

Fix every failure before stopping.
```

---

# GATE 6 — ML

## Prompt 6 — Implement the ML engine

*This prompt needs special caution. It is one of the most important because it prevents the agent from quietly building a "deep learning" façade.*

```text
Implement Layer 3: ML / Evidence Generation.

Before coding, inspect the local environment and determine whether the selected pretrained models can actually be installed and executed.

Do NOT invent a model.
Do NOT claim an unavailable model exists.
Do NOT fabricate accuracy.
Do NOT create fake ML outputs that appear to be real inference.

The system must use real model inference wherever the required model is available.

The implementation must expose interchangeable interfaces:

AntiSpoofingModel
SpeakerVerificationModel
ProsodyModel
RepresentationModel

Each model must return a typed result containing:

- score
- confidence if available
- model identifier
- model version
- inference timestamp
- latency
- error state if applicable

Implement a model adapter layer so that the UI and risk engine never depend directly on a specific ML library.

For speaker verification:
- generate embeddings
- compare current speaker representation with the registered reference representation
- expose similarity
- expose threshold configuration

For anti-spoofing:
- produce a synthetic/spoof probability only when actual model inference succeeds.

For unavailable optional models:
- return an explicit UNAVAILABLE state
- do not silently substitute a fabricated score.

The evidence layer must aggregate available expert outputs into the defined EvidenceVector.

Implement:
- model loading
- lazy initialization if beneficial
- CPU execution fallback where feasible
- clear model-loading errors
- inference timing
- deterministic evaluation mode where appropriate

Add tests for:
- successful inference
- model unavailable
- malformed input
- short audio
- model initialization failure
- inference timeout/error
- output schema validation

Before stopping, actually execute the models on at least one local fixture if technically possible.

Report the exact models actually executed.
```

---

# GATE 7 — VOICE BELIEF

## Prompt 7 — Build the voice-belief engine

```text
Implement the Voice Belief layer.

Inputs:

EvidenceVector from the ML layer.

Outputs:

VoiceBelief containing:

- spoof probability
- speaker consistency
- confidence
- evidence quality
- risk band
- suspicious temporal spans where supported
- contributing evidence
- unavailable evidence
- model provenance

Do not simply average scores without justification.

Implement a clearly documented fusion strategy.

The fusion strategy must:
- handle missing experts
- distinguish confidence from risk
- prevent unavailable models from being treated as negative evidence
- apply temporal smoothing
- prevent single-frame spikes from immediately causing a critical decision
- retain the underlying evidence for explanation

Add configuration for thresholds.

Do not optimize thresholds against a single demo recording.

Create unit tests for:
- all experts available
- one expert unavailable
- poor audio
- contradictory evidence
- high spoof evidence
- high speaker mismatch
- low confidence
- temporal smoothing

Document the mathematical formula and assumptions in:

docs/VOICE_BELIEF.md

Run tests and fix all failures.
```

---

# GATE 8 — RISK

## Prompt 8 — Build contextual risk

*Now the system becomes a cybersecurity product.*

```text
Implement the Context and Risk Engine.

The engine must combine:

VOICE SIGNALS
- spoof evidence
- speaker consistency
- acoustic evidence
- prosody evidence
- confidence
- audio quality

CALL CONTEXT
- caller identity
- caller number status
- known contact status
- call source
- language
- session history

TRANSACTION CONTEXT
- transaction value
- transaction type
- beneficiary novelty
- urgency
- sensitive-action classification

BEHAVIORAL / SECURITY CONTEXT
- unusual request indicators
- previous fraud indicators if present
- high-risk workflow state

The engine must output:

- overall risk score
- risk band
- confidence
- action
- reason codes
- top contributing factors
- evidence references
- timestamp
- policy version

Use a transparent and explainable scoring mechanism.

Do not claim that the risk score is a calibrated probability unless calibration has actually been performed.

Label it as a risk score when appropriate.

Implement configurable policies:

LOW
MEDIUM
HIGH
CRITICAL

Create explicit policies for:

1. ordinary call
2. suspicious voice but low-value action
3. suspicious voice + high-value transaction
4. strong speaker mismatch
5. poor audio + insufficient confidence
6. model unavailable

The engine must fail safely.

If evidence is insufficient, it must prefer:
UNCERTAIN / STEP-UP VERIFICATION

rather than inventing certainty.

Add comprehensive unit tests.

Run all tests.
```

---

# GATE 9 — TRANSACTION SIMULATOR

## Prompt 9 — Build the transaction simulator

*One of the highest-value demo components.*

```text
Build a deterministic banking transaction simulator for the internal demo.

This is NOT a real banking integration.

Clearly label it:

DEMO TRANSACTION ENVIRONMENT

The simulator must support:

- caller identity
- transaction amount
- beneficiary
- beneficiary novelty
- transaction state

States:

PENDING
APPROVED
HELD
REJECTED
CANCELLED

Create API endpoints to:

- create transaction
- view transaction
- update transaction state
- place transaction on hold
- release transaction after verification

The risk engine must be able to request:

HOLD
STEP_UP
ESCALATE
ALLOW

Every state change must produce an audit event.

Do not perform real financial transactions.

Do not connect to external banking systems.

Add tests for all state transitions and invalid transitions.
```

---

# GATE 10 — BACKEND

## Prompt 10 — Build the backend API

```text
Implement the complete FastAPI backend around the existing modules.

Do not duplicate business logic inside API routes.

Routes should call the underlying services.

Implement:

GET /health

POST /api/sessions

GET /api/sessions/{session_id}

POST /api/sessions/{session_id}/start

POST /api/sessions/{session_id}/stop

GET /api/sessions/{session_id}/risk

GET /api/sessions/{session_id}/evidence

GET /api/sessions/{session_id}/timeline

POST /api/transactions

GET /api/transactions/{transaction_id}

POST /api/transactions/{transaction_id}/hold

POST /api/transactions/{transaction_id}/release

WS /ws/sessions/{session_id}

Use Pydantic schemas for all external contracts.

Validate all inputs.

Return structured errors.

Do not expose internal Python exceptions directly.

Do not expose raw sensitive audio through API responses.

Ensure all timestamps are explicit.

Add API tests.

Run the backend.
Run the tests.
Fix all failures.
```

---

# GATE 11 — FRONTEND

## Prompt 11 — Build the frontend

*Now let the agent build the "wow" layer.*

```text
Build the React/TypeScript dashboard for VoiceShield.

The UI must look like a professional enterprise cybersecurity product, not a student CRUD application.

Design principles:

- dark professional security-console aesthetic
- restrained typography
- strong hierarchy
- minimal clutter
- excellent spacing
- clear status colors
- responsive layout
- accessible contrast
- subtle animation only where useful
- no unnecessary gradients
- no decorative elements that distract from the security decision

Main screen:

HEADER
VoiceShield
Real-Time Voice Integrity & Impersonation Defense
Live status indicator

CALL PANEL
Caller
Number
Call duration
Language
Call source
Transaction context

CENTRAL RISK PANEL
Large risk score
Risk band
Confidence
Current action

EVIDENCE PANEL
Acoustic
Synthetic speech
Speaker consistency
Prosody
Audio quality

TIMELINE
Live event stream

TRANSACTION PANEL
Amount
Beneficiary
Status
Security action

RECOMMENDATION PANEL
Human-readable recommended action

Create a clear visual distinction between:

LOW
MEDIUM
HIGH
CRITICAL
UNCERTAIN

Do not hardcode demo values.

All displayed values must come from backend state.

The UI must subscribe to WebSocket events.

It must update:
- risk
- evidence
- timeline
- transaction state
- call state

without requiring page refresh.

Implement loading, empty, disconnected and error states.

Do not leave console errors.

After implementation:
- build frontend
- run lint/typecheck
- launch locally
- use browser testing to inspect the page
- fix layout/runtime problems
- verify WebSocket updates visually

Create a browser verification artifact.
```

*The browser agent can interact with local Chrome pages and capture browser recordings — useful here for validating the demo rather than trusting the agent's claim that the UI works.*

---

# GATE 12 — DEMO

## Prompt 12 — Build the demo scenario engine

*This makes the presentation deterministic.*

```text
Implement the Demo Scenario Engine.

The demo must contain at least these scenarios:

SCENARIO 1 — GENUINE EXECUTIVE

Caller:
CFO

Transaction:
₹25,00,000

Expected outcome:
LOW RISK / ALLOW

SCENARIO 2 — AI VOICE IMPERSONATION

Caller:
CFO

Transaction:
₹25,00,000

Expected outcome:
HIGH or CRITICAL RISK / HOLD

SCENARIO 3 — UNCERTAIN / POOR AUDIO

Expected outcome:
UNCERTAIN / STEP-UP VERIFICATION

Important:

The scenario engine must NOT directly set the risk score.

It may only:
- select audio fixture
- provide context
- provide transaction context
- start the session

The real pipeline must produce the result.

Create a demo control API that starts a named scenario.

Create a UI control accessible only through a clearly labeled DEMO MODE panel.

Display:

DEMO MODE
This environment uses controlled test audio and simulated transaction context.

Do not call the scenarios production functionality.

Add automated tests confirming that each scenario reaches the expected decision class.
```

---

# GATE 13 — ONE-COMMAND RUN

## Prompt 13 — Make the entire thing actually run with one command

*This is where you remove friction.*

```text
Make the complete project executable by a new developer with minimal manual setup.

Create:

docker-compose.yml

and/or the simplest reliable local startup mechanism supported by the environment.

Provide:

scripts/setup
scripts/start
scripts/stop
scripts/test
scripts/demo

Use platform-appropriate equivalents where required.

The target workflow should be:

1. install documented prerequisites
2. run setup
3. run start
4. open the dashboard
5. click Demo Mode
6. select scenario
7. click Start Simulation

Do not assume undocumented environment variables.

Create .env.example.

Perform a clean-start test from the repository.

Verify:
- backend starts
- frontend starts
- database initializes
- models load or fail explicitly
- WebSocket connects
- demo audio streams
- risk updates
- transaction state changes
- UI updates

If any dependency cannot be automated, document exactly why and provide the smallest possible manual step.

Do not claim one-command startup until you have actually tested it.
```

---

# GATE 14 — QA

## Prompt 14 — The brutal QA pass

*This prompt is critical.*

```text
Act as a hostile SIH technical judge AND senior QA engineer.

Do not modify anything initially.

Run the complete application from a clean state.

Test the system as if you know nothing about its internals.

Test:

1. genuine scenario
2. impersonation scenario
3. uncertain scenario
4. malformed audio
5. empty audio
6. very short audio
7. disconnected WebSocket
8. backend restart
9. model unavailable
10. frontend refresh during active session
11. transaction hold
12. transaction release
13. multiple sessions sequentially
14. invalid API inputs
15. missing context
16. missing speaker reference
17. poor audio quality
18. slow inference
19. frontend console errors
20. backend exceptions

Also inspect:

- browser console
- network requests
- WebSocket messages
- backend logs
- API schemas
- model loading
- UI responsiveness

Do not fix anything yet.

Create:

docs/QA_FINDINGS.md

Classify every finding:

P0 = demo-breaking
P1 = major
P2 = moderate
P3 = cosmetic

For every issue include:
- reproduction
- expected
- actual
- probable cause
- proposed fix

STOP.
```

## Prompt 15 — Fix only verified problems

```text
Using docs/QA_FINDINGS.md, fix every P0 and P1 issue first.

Do not redesign the architecture.

Do not introduce new dependencies unless necessary.

For every fix:

1. reproduce the problem
2. implement the smallest correct fix
3. add or update a regression test
4. rerun the affected tests
5. rerun the full test suite

After all P0/P1 issues are resolved, address P2 issues that affect the live demo.

Do not spend time on purely cosmetic P3 issues until functionality is stable.

At the end create:

docs/QA_REMEDIATION.md

containing:
- issue
- fix
- regression test
- verification result

Do not claim an issue is fixed unless it was actually reproduced and verified.
```

---

# GATE 15 — HONESTY AUDIT

## Prompt 16 — Security and honesty audit

*This is where you prevent dangerous judge questions.*

```text
Perform a truthfulness, security and claim audit of the entire repository.

Search all source code, documentation, UI text and README content.

Identify any statement that could falsely imply:

- production deployment
- telecom integration
- banking integration
- regulatory certification
- calibrated probability
- guaranteed detection
- universal multilingual support
- zero false positives
- zero false negatives
- real financial transaction execution
- real-time performance that has not been measured
- model accuracy that has not been measured
- dataset usage that has not been verified

Replace unsupported claims with technically accurate language.

Explicitly distinguish:

REAL IMPLEMENTATION
SIMULATION
DEMO FIXTURE
FUTURE INTEGRATION

Also verify that no secret/API key is committed.

Verify .gitignore.

Verify raw audio fixtures are not accidentally exposed through public API routes.

Create:

docs/DEMO_CLAIMS_AND_LIMITATIONS.md

This document must provide concise answers to likely judge questions.

Do not change functionality unless required to correct a security or truthfulness issue.
```

---

# GATE 16 — JUDGE

## Prompt 17 — The final "judge attack"

*Consider this prompt mandatory.*

```text
You are now an extremely skeptical SIH Grand Finale judge.

You have 10 minutes to evaluate this project.

Interact with the actual application through the browser.

Do not read the source code first.

Evaluate:

1. Can I understand the product in 10 seconds?
2. Can I understand the problem in 30 seconds?
3. Does the genuine call behave differently from the impersonation call?
4. Does the risk score visibly evolve?
5. Are the reasons for the decision understandable?
6. Does the system actually trigger a protective action?
7. Does the transaction become held?
8. Does the UI recover from errors?
9. Does the system appear technically credible?
10. Can I identify which parts are real ML?
11. Can I identify which parts are simulated?
12. Is the architecture consistent with the problem statement?
13. Is privacy addressed?
14. Is multilingual support represented honestly?
15. Is the system plausibly extensible to SIP/RTP/VoIP?
16. Is there any obvious fake/demo-only behavior that undermines credibility?
17. What would make you reject this project?

Create:

docs/JUDGE_REVIEW.md

Give:
- score /10
- strongest aspects
- weakest aspects
- demo-breaking risks
- likely judge questions
- precise answers
- five highest-impact improvements

Do not make changes yet.
```

## Prompt 18 — Final polish

*Only after the judge review.*

```text
Implement ONLY the highest-impact improvements identified in docs/JUDGE_REVIEW.md that are feasible without destabilizing the system.

Priority:

P0 demo reliability
P1 technical credibility
P1 visual clarity
P1 explanation quality
P2 polish

Do not add new architecture.

Do not introduce new ML models unless explicitly required and already validated.

After every modification:
- run relevant tests
- run full tests
- build frontend
- launch backend/frontend
- perform browser verification

Do not stop at code compilation.

Verify the complete user journey end-to-end.
```

---

# GATE 17 — REHEARSAL

## Prompt 19 — Final autonomous rehearsal

*The last prompt before the competition.*

```text
Perform a complete autonomous rehearsal of the internal SIH demonstration.

Start from a clean application state.

Execute exactly this sequence:

1. Launch the system.
2. Open the dashboard.
3. Confirm system health.
4. Enter Demo Mode.
5. Start the genuine executive scenario.
6. Allow the complete audio stream to finish.
7. Verify the final decision.
8. Reset the session.
9. Start the AI impersonation scenario.
10. Allow the complete audio stream to run.
11. Verify that evidence appears progressively.
12. Verify that risk changes progressively.
13. Verify that the critical alert appears.
14. Verify that the transaction changes to HOLD.
15. Verify that secondary verification options appear.
16. Open the evidence explanation.
17. Open the event timeline.
18. Reset the system.
19. Run the uncertain scenario.
20. Verify STEP-UP / UNCERTAIN behavior.
21. Refresh the browser.
22. Restart the backend.
23. Repeat the impersonation scenario.

Capture all failures.

Do not modify anything until the rehearsal is complete.

Create:

docs/FINAL_REHEARSAL.md

Include:
- exact startup commands
- exact demo sequence
- observed outputs
- failures
- fixes required
- final readiness status

If the demo cannot complete successfully from a clean state, mark it NOT READY.
```

---

## Prompt index

| Gate | Prompt | Purpose | Output artifact |
|---|---|---|---|
| 0 | Prompt 0 | Engineering contract / requirements audit | `docs/IMPLEMENTATION_READINESS.md` |
| 1 | Prompt 1 | Freeze the architecture | `docs/EXECUTABLE_ARCHITECTURE.md` |
| 2 | Prompt 2 | Lock the technology stack | `docs/EXECUTION_TECH_STACK.md`, `docs/DEPENDENCY_MATRIX.md` |
| 3 | Prompt 3 | Repository skeleton | repo structure, `GET /health` |
| 4 | Prompt 4 | Layer 1 — audio ingestion | ingestion module + simulator |
| 5 | Prompt 5 | Layer 2 — DSP | signal_processing module |
| 6 | Prompt 6 | Layer 3 — ML / evidence | model adapters, EvidenceVector |
| 7 | Prompt 7 | Voice belief engine | `docs/VOICE_BELIEF.md` |
| 8 | Prompt 8 | Context + risk engine | risk module + policies |
| 9 | Prompt 9 | Transaction simulator | demo transaction environment |
| 10 | Prompt 10 | Backend API | FastAPI routes + WS |
| 11 | Prompt 11 | Frontend dashboard | React UI + browser verification artifact |
| 12 | Prompt 12 | Demo scenario engine | demo control API + DEMO MODE panel |
| 13 | Prompt 13 | One-command run | `docker-compose.yml`, `scripts/*` |
| 14 | Prompt 14 | Brutal QA pass | `docs/QA_FINDINGS.md` |
| 14 | Prompt 15 | Fix verified problems | `docs/QA_REMEDIATION.md` |
| 15 | Prompt 16 | Security + honesty audit | `docs/DEMO_CLAIMS_AND_LIMITATIONS.md` |
| 16 | Prompt 17 | Judge attack | `docs/JUDGE_REVIEW.md` |
| 16 | Prompt 18 | Final polish | verified end-to-end journey |
| 17 | Prompt 19 | Autonomous rehearsal | `docs/FINAL_REHEARSAL.md` |
