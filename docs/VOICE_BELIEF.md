# Voice Belief (Layer 4)

The Voice Belief layer is responsible for fusing the multi-expert `EvidenceVector` emitted by Layer 3 into a single, cohesive, and robust `VoiceBelief` state. This document outlines the mathematical framework and assumptions driving this fusion.

## Core Assumptions

1. **Missing Experts are Not Negative Evidence**: If a model is unavailable (e.g., timeout or un-enrolled speaker), it must not artificially lower the probability of a spoof. Its weight is reduced to `0.0`, and the remaining experts are re-normalized.
2. **Quality Affects Certain Experts More**: Poor audio quality disproportionately degrades the reliability of certain models (e.g., Speaker Verification and Spectro-temporal). The fusion weighting must conditionally discount experts based on their individual sensitivity to noise and the overall call quality metric $q_t$.
3. **Temporal Spikes Should Be Smoothed**: A single anomalous frame (e.g., a cough or compression artifact) should not immediately trigger a `SYNTHETIC_HIGH_CONFIDENCE` decision. We use an Exponential Moving Average (EMA) to smooth predictions over time.
4. **Contradiction Reduces Confidence**: If experts strongly disagree (high variance), the confidence of the overall belief drops. If confidence falls below a threshold, the system flags the frame as `UNCERTAIN` to prevent false positive automated actions.

## Mathematical Formulation

### 1. Quality-Conditioned Weighting
Each expert $i$ has a base weight $w_{base, i}$ and a quality sensitivity $\alpha_i$. For a given frame with acoustic quality $q_t \in [0, 1]$ and reported expert confidence $c_i \in [0, 1]$, the conditioned weight $w'_i$ is:

$w'_i = w_{base, i} \cdot c_i \cdot \max(0, 1 - \alpha_i (1 - q_t))$

If expert $i$ is not `OK`, $w'_i = 0$.

The normalized weight $W_i$ is:

$W_i = \frac{w'_i}{\sum_j w'_j}$

### 2. Frame Probability
The raw spoof probability for the frame is the weighted sum of calibrated probabilities $p_i$:

$P_{frame} = \sum W_i \cdot p_i$

### 3. Temporal Smoothing (EMA)
To prevent erratic frame-to-frame spikes, we apply Exponential Moving Average smoothing with a time constant $\tau$. Given a time step $\Delta t$, the smoothing factor $\beta$ is:

$\beta = \min\left(1.0, \frac{\Delta t}{\tau}\right)$

The smoothed probability $P_{smoothed}$ at time $t$ is:

$P_{smoothed}(t) = (1 - \beta) \cdot P_{smoothed}(t-1) + \beta \cdot P_{frame}(t)$

### 4. Confidence Calculation
Confidence $C$ is penalized if experts are missing or if they contradict each other.

Base confidence measures the proportion of active expert weight:
$C_{base} = \frac{\sum w'_i}{\sum w_{base, i}}$

Variance measures the disagreement among active experts:
$Variance = \sum W_i (p_i - P_{frame})^2$

The final confidence is reduced by a variance penalty $\lambda$:
$C = C_{base} \cdot \max(0, 1 - \lambda \cdot Variance)$

### 5. Decision Bands
The final belief state is categorized into bands based on the smoothed probability and confidence:

1. **`UNCERTAIN`**: If $C < threshold_{conf}$
2. **`SYNTHETIC_HIGH_CONFIDENCE`**: If $P_{smoothed} \ge threshold_{critical}$
3. **`SUSPICIOUS`**: If $P_{smoothed} \ge threshold_{suspicious}$
4. **`GENUINE`**: Otherwise.
