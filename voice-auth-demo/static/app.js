(() => {
  "use strict";

  const CIRC = 2 * Math.PI * 52; // matches gauge radius in CSS

  const el = (id) => document.getElementById(id);

  const state = {
    activeTab: "record",
    audioBlob: null,
    audioBuffer: null,   // decoded AudioBuffer for viz
    useSample: false,
    analyserNode: null,
    audioCtx: null,
    sourceNode: null,
    stream: null,
    rafHandle: null,
    recording: false,
    recordStart: 0,
    timerHandle: null,
    pcmChunks: [],
    pcmSampleRate: 44100,
  };

  // ------------------------------- tabs ---------------------------------

  document.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      state.activeTab = tab;
      document.querySelectorAll(".tab-panel").forEach((p) => {
        p.classList.toggle("hidden", p.dataset.panel !== tab);
      });
    });
  });

  // ------------------------------ mobile sidebar toggle -----------------

  el("sidebarToggle").addEventListener("click", () => {
    el("sidebar").classList.toggle("open");
  });

  // ------------------------------ sliders + gradient -------------------

  const allowMaxEl = el("allowMax");
  const flagMaxEl  = el("flagMax");

  function updateSliderGradient(input, a, f) {
    const total = 100;
    const aPct  = (a / total) * 100;
    const fPct  = (f / total) * 100;
    const g = `linear-gradient(to right,
      var(--allow) 0%, var(--allow) ${aPct}%,
      var(--flag)  ${aPct}%, var(--flag) ${fPct}%,
      var(--block) ${fPct}%, var(--block) 100%)`;
    input.style.setProperty("--slider-gradient", g);
    input.style.background = g;
  }

  function syncThresholds() {
    let a = parseInt(allowMaxEl.value, 10);
    let f = parseInt(flagMaxEl.value, 10);
    if (f < a) { f = a; flagMaxEl.value = f; }
    el("allowMaxLabel").textContent = a;
    el("flagMaxLabel").textContent  = f;
    updateSliderGradient(allowMaxEl, a, f);
    updateSliderGradient(flagMaxEl,  a, f);
  }
  allowMaxEl.addEventListener("input", syncThresholds);
  flagMaxEl.addEventListener("input",  syncThresholds);
  syncThresholds();

  // ------------------------------ recording (AnalyserNode) -------------

  const recordBtn   = el("recordBtn");
  const recordTimer = el("recordTimer");
  const recordWave  = el("recordWave");

  // build bar scaffold
  const BAR_COUNT = 40;
  for (let i = 0; i < BAR_COUNT; i++) {
    const s = document.createElement("span");
    recordWave.appendChild(s);
  }
  const bars = Array.from(recordWave.children);

  function animateBars() {
    if (!state.analyserNode || !state.recording) return;
    const buf = new Uint8Array(state.analyserNode.frequencyBinCount);
    state.analyserNode.getByteFrequencyData(buf);
    const step = Math.floor(buf.length / bars.length) || 1;
    for (let i = 0; i < bars.length; i++) {
      const v = buf[i * step] / 255;
      bars[i].style.height = `${4 + v * 24}px`;
    }
    state.rafHandle = requestAnimationFrame(animateBars);
  }

  function floatTo16WAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view   = new DataView(buffer);
    const str    = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    str(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    str(8, "WAVE"); str(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1,  true);
    view.setUint16(22, 1,  true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2,  true);
    view.setUint16(34, 16, true);
    str(36, "data");
    view.setUint32(40, samples.length * 2, true);
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Blob([view], { type: "audio/wav" });
  }

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const AudioContextCls = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AudioContextCls();

    const source   = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 128;
    analyser.smoothingTimeConstant = 0.8;

    // ScriptProcessor for capturing PCM (deprecated but still universal)
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    const mute      = audioCtx.createGain();
    mute.gain.value  = 0;

    state.pcmChunks    = [];
    state.pcmSampleRate = audioCtx.sampleRate;

    processor.onaudioprocess = (e) => {
      state.pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };

    source.connect(analyser);
    source.connect(processor);
    processor.connect(mute);
    mute.connect(audioCtx.destination);

    state.audioCtx    = audioCtx;
    state.analyserNode = analyser;
    state.sourceNode  = source;
    state.processorNode = processor;
    state.stream      = stream;
    state.recording   = true;
    state.recordStart = Date.now();

    recordBtn.classList.add("recording");
    state.timerHandle = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.recordStart) / 1000);
      const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const ss = String(elapsed % 60).padStart(2, "0");
      recordTimer.textContent = `${mm}:${ss}`;
    }, 200);

    // start live bar animation via rAF
    state.rafHandle = requestAnimationFrame(animateBars);
  }

  function stopRecording() {
    if (!state.recording) return;
    state.recording = false;
    clearInterval(state.timerHandle);
    cancelAnimationFrame(state.rafHandle);
    recordBtn.classList.remove("recording");

    // reset bars
    bars.forEach((b) => (b.style.height = "4px"));

    state.processorNode.disconnect();
    state.sourceNode.disconnect();
    state.stream.getTracks().forEach((t) => t.stop());

    const sampleRate = state.pcmSampleRate;
    const total  = state.pcmChunks.reduce((n, c) => n + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of state.pcmChunks) { merged.set(c, off); off += c.length; }

    const blob = floatTo16WAV(merged, sampleRate);
    state.audioCtx.close();
    handleNewClip(blob, "Live microphone recording");
  }

  recordBtn.addEventListener("click", () => {
    if (state.recording) stopRecording();
    else startRecording().catch((err) => alert("Microphone access failed: " + err.message));
  });

  // ------------------------------- upload ----------------------------------

  const dropzone      = el("dropzone");
  const fileInput     = el("fileInput");
  const dropzoneLabel = el("dropzoneLabel");

  fileInput.addEventListener("change", () => {
    const f = fileInput.files[0];
    if (f) { dropzoneLabel.textContent = f.name; handleNewClip(f, `Uploaded: ${f.name}`); }
  });
  ["dragover", "dragleave", "drop"].forEach((evt) => dropzone.addEventListener(evt, (e) => e.preventDefault()));
  dropzone.addEventListener("drop", (e) => {
    const f = e.dataTransfer.files[0];
    if (f) { dropzoneLabel.textContent = f.name; handleNewClip(f, `Uploaded: ${f.name}`); }
  });

  // ------------------------------ synthetic sample ---------------------------

  el("loadSampleBtn").addEventListener("click", async () => {
    const res = await fetch("/api/sample");
    if (!res.ok) { alert("Bundled sample not found. Run synth_bootstrap.py once, then reload."); return; }
    const blob = await res.blob();
    state.useSample = true;
    handleNewClip(blob, "Bundled synthetic (TTS) sample");
  });

  // ------------------------------ shared clip handling ----------------------

  const player    = el("player");
  const playerRow = el("playerRow");
  const waveCanvas = el("waveCanvas");

  async function handleNewClip(blobOrFile, label) {
    if (state.activeTab !== "synthetic") state.useSample = false;
    state.audioBlob   = blobOrFile;
    state.sourceLabel = label;

    const url = URL.createObjectURL(blobOrFile);
    player.src = url;
    playerRow.classList.remove("hidden");

    // decode for waveform + spectrogram
    try {
      const arrayBuf = await blobOrFile.arrayBuffer();
      const AudioContextCls = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContextCls();
      const audioBuffer = await ctx.decodeAudioData(arrayBuf.slice(0));
      state.audioBuffer = audioBuffer;
      drawWaveformCanvas(waveCanvas, audioBuffer.getChannelData(0));
      ctx.close();

      // show clip info chip with what we know now (duration from decoded buffer)
      showClipInfo({ label, duration: audioBuffer.duration, sr: audioBuffer.sampleRate });
    } catch (e) {
      waveCanvas.classList.add("hidden");
      el("clipInfo").classList.add("hidden");
    }

    el("results").classList.add("hidden");
    el("emptyState").classList.add("hidden");
  }

  function showClipInfo({ label, duration, sr }) {
    const chip = el("clipInfo");
    chip.innerHTML = `
      <strong>${label}</strong>
      <span class="chip-sep"></span>
      ${duration ? `<span>${duration.toFixed(1)}s</span><span class="chip-sep"></span>` : ""}
      ${sr ? `<span>${(sr / 1000).toFixed(1)} kHz</span>` : ""}
    `;
    chip.classList.remove("hidden");
  }

  // ----------------------------- waveform canvas --------------------------

  function drawWaveformCanvas(canvas, data) {
    canvas.classList.remove("hidden");
    const dpr    = window.devicePixelRatio || 1;
    const width  = canvas.clientWidth || 600;
    const height = parseInt(canvas.getAttribute("height"), 10) || 72;
    canvas.width  = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#0071e3";
    ctx.strokeStyle = accent;
    ctx.lineWidth   = 1.4;

    const step = Math.ceil(data.length / width);
    const mid  = height / 2;
    ctx.beginPath();
    for (let x = 0; x < width; x++) {
      let min = 1.0, max = -1.0;
      for (let j = 0; j < step; j++) {
        const v = data[x * step + j] ?? 0;
        if (v < min) min = v;
        if (v > max) max = v;
      }
      ctx.moveTo(x, mid + min * mid);
      ctx.lineTo(x, mid + max * mid);
    }
    ctx.stroke();
  }

  // ----------------------------- spectrogram canvas -----------------------

  function drawSpectrogram(canvas, audioBuffer) {
    const dpr     = window.devicePixelRatio || 1;
    const width   = canvas.clientWidth || 600;
    const height  = parseInt(canvas.getAttribute("height"), 10) || 100;
    canvas.width  = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const data      = audioBuffer.getChannelData(0);
    const fftSize   = 256;
    const hopSize   = Math.floor(data.length / width);
    const numFrames = width;

    // Hann window
    const window_ = new Float32Array(fftSize);
    for (let i = 0; i < fftSize; i++) {
      window_[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (fftSize - 1)));
    }

    // Simple DFT magnitude per column (fast enough for short clips in demo)
    // For performance we only compute magnitudes for the lower half (numBins)
    const numBins = fftSize / 2;

    const colormap = (v) => {
      // viridis-inspired: dark purple → blue → teal → green → yellow
      v = Math.max(0, Math.min(1, v));
      const r = Math.round(Math.max(0, Math.min(255, 255 * (0.8 + 0.8 * (v - 0.7)))));
      const g = Math.round(Math.max(0, Math.min(255, 255 * (1.5 * v - 0.2))));
      const b = Math.round(Math.max(0, Math.min(255, 255 * (0.9 - 1.0 * (v - 0.3)))));
      return `rgb(${r},${g},${b})`;
    };

    const frame = new Float32Array(fftSize);
    const re    = new Float32Array(fftSize);
    const im    = new Float32Array(fftSize);

    for (let col = 0; col < numFrames; col++) {
      const start = col * hopSize;

      // fill frame with windowed samples
      for (let i = 0; i < fftSize; i++) {
        frame[i] = (data[start + i] ?? 0) * window_[i];
      }

      // DFT (O(N²) — fine for fftSize=256 × ~600 columns)
      for (let k = 0; k < numBins; k++) {
        let r = 0, im_ = 0;
        for (let n = 0; n < fftSize; n++) {
          const angle = (2 * Math.PI * k * n) / fftSize;
          r   += frame[n] * Math.cos(angle);
          im_ -= frame[n] * Math.sin(angle);
        }
        re[k] = r;
        im[k] = im_;
      }

      // draw column from bottom (low freq) to top (high freq)
      const binH = height / numBins;
      for (let k = 0; k < numBins; k++) {
        const mag = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
        const db  = 20 * Math.log10(mag + 1e-6);
        // map roughly -80..0 dB → 0..1
        const norm = Math.max(0, Math.min(1, (db + 80) / 80));
        ctx.fillStyle = colormap(norm);
        ctx.fillRect(col, height - (k + 1) * binH, 1, binH + 0.5);
      }
    }
  }

  // -------------------------------- analyze ----------------------------------

  el("analyzeBtn").addEventListener("click", runPipeline);

  async function runPipeline() {
    if (!state.audioBlob) return;
    el("analyzeBtn").disabled = true;

    const pipelinePanel = el("pipelinePanel");
    const progressFill  = el("progressFill");
    const progressLabel = el("progressLabel");
    pipelinePanel.classList.remove("hidden");
    el("results").classList.add("hidden");

    const steps = [
      [20, "Ingesting audio stream…"],
      [55, "Running acoustic authenticity model…"],
      [80, "Combining with call-risk metadata…"],
    ];
    for (const [pct, label] of steps) {
      progressFill.style.width = pct + "%";
      progressLabel.textContent = label;
      await new Promise((r) => setTimeout(r, 200));
    }

    const form = new FormData();
    if (state.useSample) {
      form.append("use_sample", "true");
    } else {
      form.append("audio", state.audioBlob, "clip.wav");
      form.append("use_sample", "false");
    }
    form.append("unknown_number",     el("toggleUnknown").checked);
    form.append("transaction_request", el("toggleTransaction").checked);
    form.append("high_urgency",        el("toggleUrgency").checked);
    form.append("allow_max", allowMaxEl.value);
    form.append("flag_max",  flagMaxEl.value);

    let data;
    try {
      const res = await fetch("/api/analyze", { method: "POST", body: form });
      data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analysis failed");
    } catch (err) {
      progressLabel.textContent = "Error: " + err.message;
      el("analyzeBtn").disabled = false;
      return;
    }

    progressFill.style.width = "100%";
    progressLabel.textContent = "Done.";
    await new Promise((r) => setTimeout(r, 220));
    pipelinePanel.classList.add("hidden");
    progressFill.style.width = "0%";
    el("analyzeBtn").disabled = false;

    renderResults(data);
  }

  // -------------------------------- rendering --------------------------------

  function scoreColor(v) {
    if (v > 65) return "var(--block)";
    if (v > 30) return "var(--flag)";
    return "var(--allow)";
  }

  // Animated counter: counts el from current value to target over `duration` ms
  function animateCounter(domEl, target, duration = 650) {
    const start     = parseInt(domEl.textContent, 10) || 0;
    const startTime = performance.now();
    function step(now) {
      const t = Math.min(1, (now - startTime) / duration);
      // ease-out cubic
      const ease = 1 - Math.pow(1 - t, 3);
      domEl.textContent = Math.round(start + (target - start) * ease);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function setGauge(ringId, valueId, value) {
    const ring   = el(ringId);
    const offset = CIRC - (Math.min(100, Math.max(0, value)) / 100) * CIRC;
    ring.style.stroke = scoreColor(value);
    requestAnimationFrame(() => { ring.style.strokeDashoffset = offset; });
    animateCounter(el(valueId), Math.round(value));
  }

  const ACTION_META = {
    ALLOW:            { label: "Allow",               cls: "allow", icon: '<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' },
    FLAG_FOR_CALLBACK: { label: "Flag for callback",  cls: "flag",  icon: '<path d="M12 9v4m0 4h.01M10.3 3.9 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' },
    BLOCK:            { label: "Block",               cls: "block", icon: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/><path d="m6 6 12 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' },
  };

  function renderResults(data) {
    el("emptyState").classList.add("hidden");
    const resultsEl = el("results");
    resultsEl.classList.remove("hidden");

    setGauge("acousticRing",  "acousticValue",  data.acoustic_risk);
    setGauge("compositeRing", "compositeValue", data.composite_risk);

    // Action badge with entrance animation
    const meta  = ACTION_META[data.action];
    const badge = el("actionBadge");
    badge.className = "action-badge " + meta.cls;
    // re-trigger animation by removing then adding the class
    badge.classList.remove("entering");
    void badge.offsetWidth; // reflow
    badge.classList.add("entering");
    el("actionIcon").innerHTML = meta.icon;
    el("actionLabel").textContent = meta.label;

    // Feature contribution bars
    const barsWrap = el("featureBars");
    barsWrap.innerHTML = "";
    data.feature_contributions.forEach((c) => {
      const row = document.createElement("div");
      row.className = "feature-bar-row";
      row.innerHTML = `
        <span class="feature-bar-label">${c.label}</span>
        <span class="feature-bar-track"><span class="feature-bar-fill"></span></span>
        <span class="feature-bar-num">${Math.round(c.risk_contribution)}</span>
      `;
      barsWrap.appendChild(row);
      const fill = row.querySelector(".feature-bar-fill");
      fill.style.background = scoreColor(c.risk_contribution);
      requestAnimationFrame(() => { fill.style.width = Math.min(100, c.risk_contribution) + "%"; });
    });

    // Metadata list
    const metaWrap = el("metadataList");
    metaWrap.innerHTML = "";
    data.metadata_contributions.forEach((c) => {
      const row = document.createElement("div");
      row.className = "metadata-item" + (c.active ? " active" : "");
      row.innerHTML = `<span class="dot"></span><span>${c.label}</span>${c.active ? `<span class="pts">+${c.points}</span>` : ""}`;
      metaWrap.appendChild(row);
    });

    el("rawFeatures").textContent = JSON.stringify(data.raw_features, null, 2);

    // Update clip info chip with API-returned duration/sr (more accurate than decoded)
    if (data.duration_sec !== undefined) {
      showClipInfo({
        label: state.sourceLabel || "Analyzed clip",
        duration: data.duration_sec,
        sr: data.sample_rate,
      });
    }

    // Draw spectrogram + result waveform if we have a decoded AudioBuffer
    if (state.audioBuffer) {
      const wc = el("waveResultCanvas");
      drawWaveformCanvas(wc, state.audioBuffer.getChannelData(0));
      const sc = el("spectroCanvas");
      // defer slightly so layout is settled and clientWidth is accurate
      requestAnimationFrame(() => drawSpectrogram(sc, state.audioBuffer));
    }
  }

  function showClipInfo({ label, duration, sr }) {
    const chip = el("clipInfo");
    chip.innerHTML = `
      <strong>${label}</strong>
      <span class="chip-sep"></span>
      ${duration !== undefined ? `<span>${Number(duration).toFixed(1)}s</span><span class="chip-sep"></span>` : ""}
      ${sr ? `<span>${(sr / 1000).toFixed(1)} kHz</span>` : ""}
    `;
    chip.classList.remove("hidden");
  }

})();
