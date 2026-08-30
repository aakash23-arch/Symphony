# VoiceShield Dashboard

React + TypeScript security console for the VoiceShield analysis pipeline. Every
value on screen comes from backend state and updates over WebSocket without a
refresh.

## Running it

```bash
# Terminal 1 - the analysis backend (loads real model weights, ~20 s to start)
python -m uvicorn voiceshield.api.app:app --app-dir backend --port 8000

# Terminal 2 - the dashboard
cd frontend && npm run dev        # http://localhost:5173
```

Vite proxies `/api`, `/ws`, `/v1` and `/health` to port 8000.

```bash
npm run lint     # tsc --noEmit, strict
npm run build    # tsc && vite build
npx playwright test
python e2e/build_artifact.py      # rebuild the verification record
```

## The cardinal rule

`score_semantics` is `UNCALIBRATED_RISK_SCORE`: the score orders calls by
concern, it does **not** estimate a probability that a call is fraudulent. The
interface must never imply certainty the backend does not have. Five guards
enforce this, and they are the parts of the codebase most worth preserving:

| Guard | Where |
|---|---|
| `formatScore()` renders `0.78`, never `78%`; a Playwright test asserts no `%` in the risk panel | `src/lib/risk.ts` |
| `decision: RiskDecision \| null` — no placeholder object exists, so a component *cannot* render `LOW / 0.00` for a session that produced nothing | `src/state/sessionReducer.ts` |
| `<Metric>` renders an em dash plus "no evidence" for null; `?? 0` on a nullable API numeric is banned | `src/components/Metric.tsx` |
| `connectNulls={false}` — the recharts default would draw a trend across windows where the experts said nothing | `src/panels/EvidencePanel.tsx` |
| UNCERTAIN is violet, dashed and hatched, never grey — grey reads as "inactive", i.e. nothing to worry about | `src/lib/risk.ts` |

`fail_safe_engaged`, `analysis_degraded`, `context_degraded` and
`hash_chained: false` all render in the layout rather than behind a tooltip.
They qualify the decision, so hiding them would misrepresent it.

## Architecture

```
types/       contracts.ts (1:1 mirror of the Pydantic models), events.ts (WS union)
api/         client.ts (409-as-value), socket.ts (backoff, terminal-close detection)
state/       sessionReducer.ts (pure), SessionProvider.tsx (all side effects), useSession.ts
lib/         risk.ts (band tokens + score formatting), format.ts, cn.ts
components/  Panel, PanelStates, Badge, Metric, ConnectionDot  — presentational, props only
panels/      the seven panels + DemoControl                    — session-aware
```

Three things are non-obvious enough to state:

**The WS payloads are thin.** `risk.updated` carries no `top_factors` and
`belief.updated` carries no `trajectory`, so the Evidence factor list and the
trajectory chart cannot come from the socket alone. A risk update schedules a
debounced REST refresh of `/evidence` and `/risk`.

**`session.snapshot` is a bare object with `type`; everything else is an
envelope with `event_type`.** The discriminator is which key exists.

**`belief` and `beliefLive` are separate slices.** The socket's thin belief has
no trajectory and no expert list; patching it onto a `VoiceBelief` would produce
an object whose type claims fields it does not have.

## States

Five treatments in `components/PanelStates.tsx`: Loading, Empty, Awaiting,
Disconnected, Error.

**Awaiting** is the one that matters. `GET /risk` returns `409
RISK_NOT_YET_AVAILABLE` until the first assessment exists — deliberate, because
`risk_score` is a non-optional float and a "nothing yet" body would have to
carry `0.0`. The client models it as a value (`{kind: 'awaiting'}`), never
throws, and never logs it: the requirement is a console with no errors in it.

## Verification

`e2e/artifacts/verification.html` — self-contained record of the last Playwright
run: 9/9 passed, zero console errors, with the empty, awaiting, absent-evidence,
live and disconnected states captured at four breakpoints.
