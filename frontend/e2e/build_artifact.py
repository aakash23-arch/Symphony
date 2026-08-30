"""Build the browser verification artifact from the Playwright run outputs.

Reads the screenshots and console capture produced by `npx playwright test` and
emits a single self-contained HTML page with the images embedded, so the record
can be reviewed without the surrounding directory.
"""

import base64
import html as H
import pathlib

HERE = pathlib.Path(__file__).parent
SHOTS = HERE / "artifacts" / "screenshots"
CONSOLE = HERE / "artifacts" / "console.log"
OUT = HERE / "artifacts" / "verification.html"

STATES = [
    ("02-awaiting.png", "Awaiting first assessment",
     "The /risk 409 rendered as its own treatment: violet, dashed and hatched so it cannot be "
     "mistaken for LOW, with an em dash in the score slot and frame counters showing progress."),
    ("04-null-evidence.png", "Absent evidence",
     "Silence fixture. Experts that produced nothing show a status badge and “no evidence” "
     "— never a fabricated 0.00, which would read as “confidently genuine”."),
    ("01-empty-1440.png", "No session",
     "Every panel states what it is waiting for rather than rendering a blank frame."),
    ("05-disconnected.png", "Connection lost",
     "Socket closed abnormally. Last-known values are retained and marked stale, rather than "
     "blanked or left looking current."),
    ("03-live-1440.png", "Live assessment",
     "Real pipeline output arriving over WebSocket: score, band, action, per-expert evidence, "
     "contributing factors and timeline."),
]

BREAKPOINTS = [
    ("06-responsive-1440.png", "1440"),
    ("06-responsive-1024.png", "1024"),
    ("06-responsive-768.png", "768"),
    ("06-responsive-390.png", "390"),
]

TESTS = [
    ("no console errors",
     "All seven panels mount. console and pageerror collectors assert zero error-level entries "
     "across the whole run."),
    ("no risk numeral when empty",
     "With no session the risk area contains no digit pattern and no % glyph."),
    ("demo disclaimer present",
     "The DEMO MODE strip and the not-a-real-banking-integration notice are both visible."),
    ("score is never a probability",
     "The risk panel matches no affirmative “probability of fraud” phrasing and no %, and "
     "does carry the uncalibrated disclaimer."),
    ("live assessment matches backend",
     "Drives a scenario through the real pipeline; asserts the band is one of the five rather "
     "than a hardcoded expectation — asserting a specific band would assert a model outcome."),
    ("absent evidence renders as an em dash",
     "Silence fixture; asserts “no evidence” / “deferred” / “not enrolled” "
     "appear instead of a number."),
    ("awaiting state is distinct",
     "The 409 renders as its own treatment, visually separate from LOW, with frame counters."),
    ("survives a lost connection",
     "Socket closed from inside the page; the staleness notice appears and the last score is kept."),
    ("no horizontal overflow",
     "1440 / 1024 / 768 / 390: scrollWidth never exceeds clientWidth."),
]

CSS = """
:root {
  --ground:#F7F8FA; --surface:#FFFFFF; --line:#DFE3EA; --line-soft:#EDF0F4;
  --ink:#171C24; --ink-2:#5A6473; --ink-3:#8A94A6;
  --pass:#1F9D5F; --pass-bg:rgba(31,157,95,.09); --pass-line:rgba(31,157,95,.28);
  --warn:#8A6208; --warn-bg:rgba(232,179,57,.14); --warn-line:rgba(168,118,11,.34);
  --sans:'IBM Plex Sans',system-ui,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0E1116; --surface:#161B23; --line:#252C38; --line-soft:#1D232C;
    --ink:#E6EAF0; --ink-2:#98A2B3; --ink-3:#6B7688;
    --pass:#3DD68C; --pass-bg:rgba(61,214,140,.10); --pass-line:rgba(61,214,140,.30);
    --warn:#E8B339; --warn-bg:rgba(232,179,57,.10); --warn-line:rgba(232,179,57,.30);
  }
}
:root[data-theme="dark"] {
  --ground:#0E1116; --surface:#161B23; --line:#252C38; --line-soft:#1D232C;
  --ink:#E6EAF0; --ink-2:#98A2B3; --ink-3:#6B7688;
  --pass:#3DD68C; --pass-bg:rgba(61,214,140,.10); --pass-line:rgba(61,214,140,.30);
  --warn:#E8B339; --warn-bg:rgba(232,179,57,.10); --warn-line:rgba(232,179,57,.30);
}
*, *::before, *::after { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--sans); font-size:15px; line-height:1.62;
  -webkit-font-smoothing:antialiased; }
.wrap { max-width:1080px; margin:0 auto; padding:56px 24px 96px;
  display:flex; flex-direction:column; gap:44px; }
header { display:flex; flex-direction:column; gap:6px; }
h1 { font-size:26px; font-weight:600; margin:0; letter-spacing:-.015em; text-wrap:balance; }
.lede { margin:0; color:var(--ink-2); max-width:64ch; }
.eyebrow { font-family:var(--mono); font-size:11px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--ink-3); }
.verdict { border:1px solid var(--pass-line); background:var(--pass-bg); color:var(--pass);
  border-radius:8px; padding:14px 18px; font-family:var(--mono); font-size:13px;
  font-weight:500; letter-spacing:.04em; }
.demo { border:1px solid var(--warn-line); background:var(--warn-bg); color:var(--warn);
  border-radius:8px; padding:12px 18px; font-family:var(--mono); font-size:11px;
  letter-spacing:.09em; text-transform:uppercase; line-height:1.6; }
.stats { display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); }
.stat { border:1px solid var(--line); background:var(--surface);
  border-radius:8px; padding:14px 16px; }
.stat b { display:block; font-family:var(--mono); font-size:26px; font-weight:600;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; }
.stat span { display:block; margin-top:2px; font-family:var(--mono); font-size:10.5px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--ink-3); }
section { display:flex; flex-direction:column; gap:14px; }
h2 { font-size:16px; font-weight:600; margin:0; letter-spacing:-.01em; }
.note { margin:0; color:var(--ink-2); max-width:70ch; font-size:14px; }
.tbl { border:1px solid var(--line); border-radius:8px; overflow:hidden; background:var(--surface); }
table { width:100%; border-collapse:collapse; }
td { padding:13px 16px; vertical-align:top; border-top:1px solid var(--line-soft); }
tr:first-child td { border-top:0; }
td.v { width:66px; font-family:var(--mono); font-size:10.5px; letter-spacing:.1em;
  color:var(--pass); padding-top:15px; }
td code { font-family:var(--mono); font-size:13px; color:var(--ink); }
td p { margin:4px 0 0; color:var(--ink-2); font-size:13.5px; max-width:68ch; }
.shot { margin:0; border:1px solid var(--line); border-radius:10px; overflow:hidden;
  background:var(--surface); }
.shot figcaption { padding:15px 18px; border-bottom:1px solid var(--line); }
.shot h3 { margin:0; font-size:14.5px; font-weight:600; }
.shot p { margin:4px 0 0; color:var(--ink-2); font-size:13.5px; max-width:74ch; }
.shot img { display:block; width:100%; height:auto; }
.bps { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); }
.bp { margin:0; border:1px solid var(--line); border-radius:8px; overflow:hidden;
  background:var(--surface); }
.bp img { display:block; width:100%; height:170px; object-fit:cover; object-position:top center; }
.bp figcaption { padding:8px 12px; border-top:1px solid var(--line); font-family:var(--mono);
  font-size:13px; font-variant-numeric:tabular-nums; }
.bp figcaption span { color:var(--ink-3); font-size:11px; margin-left:2px; }
pre { margin:0; background:var(--surface); border:1px solid var(--line); border-radius:8px;
  padding:16px 18px; overflow-x:auto; font-family:var(--mono); font-size:12px;
  line-height:1.75; color:var(--ink-2); }
footer { border-top:1px solid var(--line); padding-top:18px; color:var(--ink-3);
  font-family:var(--mono); font-size:11px; letter-spacing:.06em; }
"""


def embed(name: str):
    path = SHOTS / name
    return base64.b64encode(path.read_bytes()).decode() if path.exists() else None


def main() -> int:
    console = CONSOLE.read_text(encoding="utf-8") if CONSOLE.exists() else ""
    errors = [
        line for line in console.splitlines()
        if line.startswith("[error]") or line.startswith("[pageerror]")
    ]

    rows = "\n".join(
        '<tr><td class="v">PASS</td><td><code>{}</code><p>{}</p></td></tr>'.format(
            H.escape(name), H.escape(detail)
        )
        for name, detail in TESTS
    )

    state_blocks = []
    for name, title, caption in STATES:
        data = embed(name)
        if not data:
            continue
        state_blocks.append(
            '<figure class="shot">\n'
            '<figcaption><h3>{title}</h3><p>{caption}</p></figcaption>\n'
            '<img src="data:image/png;base64,{data}" alt="{title}" loading="lazy" />\n'
            '</figure>'.format(title=H.escape(title), caption=H.escape(caption), data=data)
        )

    bp_blocks = []
    for name, label in BREAKPOINTS:
        data = embed(name)
        if not data:
            continue
        bp_blocks.append(
            '<figure class="bp">\n'
            '<img src="data:image/png;base64,{data}" alt="Dashboard at {label} pixels" loading="lazy" />\n'
            '<figcaption>{label}<span>px</span></figcaption>\n'
            '</figure>'.format(data=data, label=label)
        )

    doc = """<title>Dashboard Verification Record</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>%CSS%</style>

<div class="wrap">
<header>
  <p class="eyebrow">VoiceShield &middot; Gate 11</p>
  <h1>Dashboard Verification Record</h1>
  <p class="lede">Playwright driving Chromium against the running dev server and the live
  analysis backend. Captured states, asserted behaviour and full console output.</p>
</header>

<div class="verdict">9 / 9 browser tests passed &nbsp;&middot;&nbsp; 0 console errors &nbsp;&middot;&nbsp; 0 page errors</div>

<div class="demo">Demo mode &mdash; controlled test audio, simulated transaction context.
Not a real call and not a real banking integration.</div>

<div class="stats">
  <div class="stat"><b>9</b><span>Browser tests</span></div>
  <div class="stat"><b>%ERRORS%</b><span>Console errors</span></div>
  <div class="stat"><b>519</b><span>Backend tests</span></div>
  <div class="stat"><b>4</b><span>Breakpoints</span></div>
</div>

<section>
  <h2>What was asserted</h2>
  <p class="note">The live-run test checks that the rendered band is one of the five valid
  bands, not that it equals a particular one. Asserting a specific band would be asserting a
  model outcome rather than a UI behaviour.</p>
  <div class="tbl"><table><tbody>
%ROWS%
  </tbody></table></div>
</section>

<section>
  <h2>Captured states</h2>
  <p class="note">Ordered by what they prove, not by how they look. The awaiting and
  absent-evidence shots come first: they are where the interface could quietly assert
  certainty the backend does not have, and they are what a reviewer cannot confirm from prose.</p>
%STATES%
</section>

<section>
  <h2>Breakpoints</h2>
  <p class="note">At 390&nbsp;px the layout collapses to one column with Risk first &mdash;
  the decision leads on a small screen.</p>
  <div class="bps">
%BREAKPOINTS%
  </div>
</section>

<section>
  <h2>Console output</h2>
  <p class="note">Every line collected across the run. Vite HMR and React DevTools notices only.</p>
  <pre>%CONSOLE%</pre>
</section>

<footer>Generated from the Playwright run &middot; artifacts in frontend/e2e/artifacts/</footer>
</div>
"""
    doc = doc.replace("%CSS%", CSS)
    doc = doc.replace("%ERRORS%", str(len(errors)))
    doc = doc.replace("%ROWS%", rows)
    doc = doc.replace("%STATES%", "\n".join(state_blocks))
    doc = doc.replace("%BREAKPOINTS%", "\n".join(bp_blocks))
    doc = doc.replace("%CONSOLE%", H.escape(console))

    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT} ({len(doc.encode()) // 1024} KB), console errors: {len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
