(() => {
  "use strict";

  const CIRC = 2 * Math.PI * 52; // matches gauge radius in CSS

  const el = (id) => document.getElementById(id);

  const state = {
    activeTab: "record",
    audioBlob: null,
    audioBuffer: null,
    useSample: false,
    // recording + WebSocket streaming
    analyserNode: null,
    audioCtx: null,
    sourceNode: null,
    processorNode: null,
    stream: null,
    rafHandle: null,
    recording: false,
    streaming: false,     // true when a WebSocket stream is active
    ws: null,             // WebSocket instance
    chunkInterval: null,  // setInterval handle for flushing PCM chunks
    pcmChunks: [],      // flushed to WebSocket every 500ms (gets cleared)
    allChunks: [],      // full recording — never cleared until next record session
    pcmSampleRate: 44100,
    recordStart: 0,
    timerHandle: null,
  };

  // ------------------------------- tabs ---------------------------------

  document.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeTab = btn.dataset.tab;
      document.querySelectorAll(".tab-panel").forEach((p) => {
        p.classList.toggle("hidden", p.dataset.panel !== state.activeTab);
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
    const g = `linear-gradient(to right,
      var(--allow) 0%, var(--allow) ${a}%,
      var(--flag)  ${a}%, var(--flag) ${f}%,
      var(--block) ${f}%, var(--block) 100%)`;
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
    // If a stream is live, propagate the new thresholds immediately
    sendMetadataUpdate();
  }
  allowMaxEl.addEventListener("input", syncThresholds);
  flagMaxEl.addEventListener("input",  syncThresholds);
  syncThresholds();

  // Send metadata updates over WS whenever toggles change
  ["toggleUnknown", "toggleTransaction", "toggleUrgency"].forEach((id) => {
    el(id).addEventListener("change", sendMetadataUpdate);
  });

  function sendMetadataUpdate() {
    if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
    state.ws.send(JSON.stringify({
      type:               "metadata",
      unknownNumber:      el("toggleUnknown").checked,
      transactionRequest: el("toggleTransaction").checked,
      highUrgency:        el("toggleUrgency").checked,
      allowMax:           parseFloat(allowMaxEl.value),
      flagMax:            parseFloat(flagMaxEl.value),
    }));
  }

  // ------------------------------ recording (AnalyserNode) + WebSocket --

  const recordBtn   = el("recordBtn");
  const recordTimer = el("recordTimer");
  const recordWave  = el("recordWave");

  // Build bar scaffold
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

  // ---- WebSocket helpers -----------------------------------------------

  function openStreamSocket(sampleRate) {
    const wsUrl = `ws://${location.host}/api/stream`;
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.addEventListener("open", () => {
      // Send init message with sample rate and current metadata/threshold state
      ws.send(JSON.stringify({
        type:               "init",
        sampleRate,
        unknownNumber:      el("toggleUnknown").checked,
        transactionRequest: el("toggleTransaction").checked,
        highUrgency:        el("toggleUrgency").checked,
        allowMax:           parseFloat(allowMaxEl.value),
        flagMax:            parseFloat(flagMaxEl.value),
      }));
      state.streaming = true;
      setLiveMode(true);
    });

    ws.addEventListener("message", (evt) => {
      try {
        const data = JSON.parse(evt.data);
        renderResults(data, true /* liveMode */);
      } catch (e) { /* ignore bad frames */ }
    });

    ws.addEventListener("close", () => {
      state.streaming = false;
      setLiveMode(false);
    });

    ws.addEventListener("error", () => {
      console.warn("WebSocket error — streaming unavailable.");
      state.streaming = false;
      setLiveMode(false);
    });

    return ws;
  }

  // Toggle the LIVE chip and lock the Analyze button during streaming
  function setLiveMode(on) {
    el("liveChip").classList.toggle("hidden", !on);
    el("results").classList.toggle("hidden", !on);
    el("emptyState").classList.add("hidden");
    if (on) {
      el("analyzeBtn").disabled = true;
      el("analyzeBtn").textContent = "Streaming…";
    } else {
      el("analyzeBtn").disabled = false;
      el("analyzeBtn").textContent = "Analyze this clip";
    }
  }

  // ---- Flush accumulated PCM chunks over the WebSocket every 500ms ----

  function startChunkInterval() {
    state.chunkInterval = setInterval(() => {
      if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
      if (state.pcmChunks.length === 0) return;

      const total  = state.pcmChunks.reduce((n, c) => n + c.length, 0);
      const merged = new Float32Array(total);
      let off = 0;
      for (const c of state.pcmChunks) { merged.set(c, off); off += c.length; }
      state.pcmChunks = []; // reset accumulator

      // Convert Float32 → Int16 and send as binary
      const int16 = new Int16Array(merged.length);
      for (let i = 0; i < merged.length; i++) {
        int16[i] = Math.max(-32768, Math.min(32767, merged[i] * 32767));
      }
      state.ws.send(int16.buffer);
    }, 500);
  }

  // ---- Main recording start/stop --------------------------------------

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const AudioContextCls = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AudioContextCls();

    const source   = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 128;
    analyser.smoothingTimeConstant = 0.8;

    // ScriptProcessor captures raw PCM (deprecated but universally supported)
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    const mute      = audioCtx.createGain();
    mute.gain.value = 0;

    state.pcmChunks     = [];
    state.allChunks     = [];   // start fresh for this recording session
    state.pcmSampleRate = audioCtx.sampleRate;

    processor.onaudioprocess = (e) => {
      const data = new Float32Array(e.inputBuffer.getChannelData(0));
      state.pcmChunks.push(data);
      state.allChunks.push(data); // keep full copy — never cleared by the WS flush
    };

    source.connect(analyser);
    source.connect(processor);
    processor.connect(mute);
    mute.connect(audioCtx.destination);

    state.audioCtx      = audioCtx;
    state.analyserNode  = analyser;
    state.sourceNode    = source;
    state.processorNode = processor;
    state.stream        = stream;
    state.recording     = true;
    state.recordStart   = Date.now();

    recordBtn.classList.add("recording");
    state.timerHandle = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.recordStart) / 1000);
      const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const ss = String(elapsed % 60).padStart(2, "0");
      recordTimer.textContent = `${mm}:${ss}`;
    }, 200);

    // Start live bar animation
    state.rafHandle = requestAnimationFrame(animateBars);

    // Open the streaming WebSocket
    state.ws = openStreamSocket(audioCtx.sampleRate);
    startChunkInterval();
  }

  function floatTo16WAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view   = new DataView(buffer);
    const str    = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    str(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    str(8, "WAVE"); str(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
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

  function stopRecording() {
    if (!state.recording) return;
    state.recording = false;
    clearInterval(state.timerHandle);
    clearInterval(state.chunkInterval);
    cancelAnimationFrame(state.rafHandle);
    recordBtn.classList.remove("recording");
    bars.forEach((b) => (b.style.height = "4px"));

    state.processorNode.disconnect();
    state.sourceNode.disconnect();
    state.stream.getTracks().forEach((t) => t.stop());

    // Close the WebSocket gracefully
    if (state.ws && state.ws.readyState === WebSocket.OPEN) state.ws.close();
    state.ws = null;

    // Build the final WAV from the FULL recording (allChunks, never cleared by WS flush)
    const sampleRate = state.pcmSampleRate;
    const total  = state.allChunks.reduce((n, c) => n + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of state.allChunks) { merged.set(c, off); off += c.length; }

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

  const player     = el("player");
  const playerRow  = el("playerRow");
  const waveCanvas = el("waveCanvas");

  async function handleNewClip(blobOrFile, label) {
    if (state.activeTab !== "synthetic") state.useSample = false;
    state.audioBlob   = blobOrFile;
    state.sourceLabel = label;

    const url = URL.createObjectURL(blobOrFile);
    player.src = url;
    playerRow.classList.remove("hidden");

    try {
      const arrayBuf = await blobOrFile.arrayBuffer();
      const AudioContextCls = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContextCls();
      const audioBuffer = await ctx.decodeAudioData(arrayBuf.slice(0));
      state.audioBuffer = audioBuffer;
      drawWaveformCanvas(waveCanvas, audioBuffer.getChannelData(0));
      ctx.close();
      showClipInfo({ label, duration: audioBuffer.duration, sr: audioBuffer.sampleRate });
    } catch (e) {
      waveCanvas.classList.add("hidden");
      el("clipInfo").classList.add("hidden");
    }

    // Only reset results if not in the middle of a stream
    if (!state.streaming) {
      el("results").classList.add("hidden");
      el("emptyState").classList.remove("hidden");
      setLiveMode(false);
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

    const data    = audioBuffer.getChannelData(0);
    const fftSize = 256;
    const hopSize = Math.floor(data.length / width);
    const numBins = fftSize / 2;

    const window_ = new Float32Array(fftSize);
    for (let i = 0; i < fftSize; i++) {
      window_[i] = 0.5 * (1 - Math.cos(2 * Math.PI * i / (fftSize - 1)));
    }

    const colormap = (v) => {
      v = Math.max(0, Math.min(1, v));
      const r = Math.round(Math.max(0, Math.min(255, 255 * (0.8 + 0.8 * (v - 0.7)))));
      const g = Math.round(Math.max(0, Math.min(255, 255 * (1.5 * v - 0.2))));
      const b = Math.round(Math.max(0, Math.min(255, 255 * (0.9 - 1.0 * (v - 0.3)))));
      return `rgb(${r},${g},${b})`;
    };

    const frame = new Float32Array(fftSize);
    const re    = new Float32Array(fftSize);
    const im    = new Float32Array(fftSize);

    for (let col = 0; col < width; col++) {
      const start = col * hopSize;
      for (let i = 0; i < fftSize; i++) {
        frame[i] = (data[start + i] ?? 0) * window_[i];
      }
      for (let k = 0; k < numBins; k++) {
        let r = 0, im_ = 0;
        for (let n = 0; n < fftSize; n++) {
          const angle = (2 * Math.PI * k * n) / fftSize;
          r   += frame[n] * Math.cos(angle);
          im_ -= frame[n] * Math.sin(angle);
        }
        re[k] = r; im[k] = im_;
      }
      const binH = height / numBins;
      for (let k = 0; k < numBins; k++) {
        const mag  = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
        const db   = 20 * Math.log10(mag + 1e-6);
        const norm = Math.max(0, Math.min(1, (db + 80) / 80));
        ctx.fillStyle = colormap(norm);
        ctx.fillRect(col, height - (k + 1) * binH, 1, binH + 0.5);
      }
    }
  }

  // -------------------------------- analyze (REST) -------------------------

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
    form.append("unknown_number",      el("toggleUnknown").checked);
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

    renderResults(data, false);

    if (data.duration_sec !== undefined) {
      showClipInfo({ label: state.sourceLabel || "Analyzed clip", duration: data.duration_sec, sr: data.sample_rate });
    }
  }

  // -------------------------------- rendering --------------------------------

  function scoreColor(v) {
    if (v > 65) return "var(--block)";
    if (v > 30) return "var(--flag)";
    return "var(--allow)";
  }

  // Animated counter — fast in live mode, slow otherwise
  function animateCounter(domEl, target, liveMode) {
    const duration  = liveMode ? 150 : 650;
    const start     = parseInt(domEl.textContent, 10) || 0;
    const startTime = performance.now();
    function step(now) {
      const t    = Math.min(1, (now - startTime) / duration);
      const ease = liveMode ? t : 1 - Math.pow(1 - t, 3); // linear for live, ease-out cubic otherwise
      domEl.textContent = Math.round(start + (target - start) * ease);
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function setGauge(ringId, valueId, value, liveMode) {
    const ring   = el(ringId);
    const offset = CIRC - (Math.min(100, Math.max(0, value)) / 100) * CIRC;
    ring.style.stroke = scoreColor(value);
    requestAnimationFrame(() => { ring.style.strokeDashoffset = offset; });
    animateCounter(el(valueId), Math.round(value), liveMode);
  }

  const ACTION_META = {
    ALLOW:             { label: "Allow",              cls: "allow", icon: '<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' },
    FLAG_FOR_CALLBACK: { label: "Flag for callback",  cls: "flag",  icon: '<path d="M12 9v4m0 4h.01M10.3 3.9 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' },
    BLOCK:             { label: "Block",              cls: "block", icon: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/><path d="m6 6 12 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' },
  };

  // Track last action to only re-animate badge when it actually changes
  let _lastAction = null;

  function renderResults(data, liveMode = false) {
    el("emptyState").classList.add("hidden");
    el("results").classList.remove("hidden");

    setGauge("acousticRing",  "acousticValue",  data.acoustic_risk,  liveMode);
    setGauge("compositeRing", "compositeValue", data.composite_risk, liveMode);

    // Action badge — animate entrance only on change (avoid thrashing during stream)
    const meta  = ACTION_META[data.action];
    const badge = el("actionBadge");
    badge.className = "action-badge " + meta.cls;
    if (data.action !== _lastAction || !liveMode) {
      badge.classList.remove("entering");
      void badge.offsetWidth;
      badge.classList.add("entering");
      _lastAction = data.action;
    }
    el("actionIcon").innerHTML  = meta.icon;
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

    // Raw features (skip in live mode to reduce DOM churn)
    if (!liveMode && data.raw_features) {
      el("rawFeatures").textContent = JSON.stringify(data.raw_features, null, 2);
    }

    // Visualizations — only draw for full-clip analysis (not during streaming)
    if (!liveMode && state.audioBuffer) {
      drawWaveformCanvas(el("waveResultCanvas"), state.audioBuffer.getChannelData(0));
      requestAnimationFrame(() => drawSpectrogram(el("spectroCanvas"), state.audioBuffer));
    }
  }

})();
