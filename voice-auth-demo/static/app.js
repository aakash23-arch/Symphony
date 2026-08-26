(() => {
  "use strict";

  const CIRC = 2 * Math.PI * 52; // matches gauge radius in CSS

  const el = (id) => document.getElementById(id);

  const state = {
    activeTab: "record",
    audioBlob: null,
    useSample: false,
    mediaRecorder: null,
    audioCtx: null,
    processorNode: null,
    sourceNode: null,
    pcmChunks: [],
    recording: false,
    recordStart: 0,
    timerHandle: null,
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

  // ------------------------------ sliders ---------------------------------

  const allowMax = el("allowMax");
  const flagMax = el("flagMax");
  const allowMaxLabel = el("allowMaxLabel");
  const flagMaxLabel = el("flagMaxLabel");

  function syncThresholds() {
    let a = parseInt(allowMax.value, 10);
    let f = parseInt(flagMax.value, 10);
    if (f < a) { f = a; flagMax.value = f; }
    allowMaxLabel.textContent = a;
    flagMaxLabel.textContent = f;
  }
  allowMax.addEventListener("input", syncThresholds);
  flagMax.addEventListener("input", syncThresholds);

  // ------------------------------ recording --------------------------------

  const recordBtn = el("recordBtn");
  const recordTimer = el("recordTimer");
  const recordWave = el("recordWave");

  // build a small static bar visualizer scaffold
  const BAR_COUNT = 40;
  for (let i = 0; i < BAR_COUNT; i++) {
    const s = document.createElement("span");
    recordWave.appendChild(s);
  }
  const bars = Array.from(recordWave.children);

  function floatTo16WAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeStr = (offset, str) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };

    writeStr(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, "data");
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
    const source = audioCtx.createMediaStreamSource(stream);
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    const mute = audioCtx.createGain();
    mute.gain.value = 0;

    state.pcmChunks = [];
    processor.onaudioprocess = (e) => {
      const data = e.inputBuffer.getChannelData(0);
      state.pcmChunks.push(new Float32Array(data));
      updateBars(data);
    };

    source.connect(processor);
    processor.connect(mute);
    mute.connect(audioCtx.destination);

    state.audioCtx = audioCtx;
    state.sourceNode = source;
    state.processorNode = processor;
    state.stream = stream;
    state.recording = true;
    state.recordStart = Date.now();

    recordBtn.classList.add("recording");
    state.timerHandle = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.recordStart) / 1000);
      const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const ss = String(elapsed % 60).padStart(2, "0");
      recordTimer.textContent = `${mm}:${ss}`;
    }, 200);
  }

  function updateBars(data) {
    const step = Math.floor(data.length / bars.length) || 1;
    for (let i = 0; i < bars.length; i++) {
      const v = Math.abs(data[i * step] || 0);
      bars[i].style.height = `${4 + Math.min(1, v * 4) * 24}px`;
    }
  }

  function stopRecording() {
    if (!state.recording) return;
    state.recording = false;
    clearInterval(state.timerHandle);
    recordBtn.classList.remove("recording");

    state.processorNode.disconnect();
    state.sourceNode.disconnect();
    state.stream.getTracks().forEach((t) => t.stop());

    const sampleRate = state.audioCtx.sampleRate;
    const total = state.pcmChunks.reduce((n, c) => n + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of state.pcmChunks) { merged.set(c, off); off += c.length; }

    const blob = floatTo16WAV(merged, sampleRate);
    state.audioCtx.close();
    handleNewClip(blob, "Live microphone recording");
  }

  recordBtn.addEventListener("click", () => {
    if (state.recording) stopRecording();
    else startRecording().catch((err) => {
      alert("Microphone access failed: " + err.message);
    });
  });

  // ------------------------------- upload ----------------------------------

  const dropzone = el("dropzone");
  const fileInput = el("fileInput");
  const dropzoneLabel = el("dropzoneLabel");

  fileInput.addEventListener("change", () => {
    const f = fileInput.files[0];
    if (f) {
      dropzoneLabel.textContent = f.name;
      handleNewClip(f, `Uploaded file: ${f.name}`);
    }
  });

  ["dragover", "dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => e.preventDefault());
  });
  dropzone.addEventListener("drop", (e) => {
    const f = e.dataTransfer.files[0];
    if (f) {
      dropzoneLabel.textContent = f.name;
      handleNewClip(f, `Uploaded file: ${f.name}`);
    }
  });

  // ------------------------------ synthetic sample ---------------------------

  el("loadSampleBtn").addEventListener("click", async () => {
    const res = await fetch("/api/sample");
    if (!res.ok) {
      alert("Bundled sample not found. Run synth_bootstrap.py once, then reload.");
      return;
    }
    const blob = await res.blob();
    state.useSample = true;
    handleNewClip(blob, "Bundled synthetic (TTS) sample");
  });

  // ------------------------------ shared clip handling ------------------------

  const player = el("player");
  const playerRow = el("playerRow");
  const waveCanvas = el("waveCanvas");
  const analyzeBtn = el("analyzeBtn");

  async function handleNewClip(blobOrFile, label) {
    if (state.activeTab !== "synthetic") state.useSample = false;
    state.audioBlob = blobOrFile;
    state.sourceLabel = label;

    const url = URL.createObjectURL(blobOrFile);
    player.src = url;
    playerRow.classList.remove("hidden");

    try {
      const arrayBuf = await blobOrFile.arrayBuffer();
      const AudioContextCls = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContextCls();
      const audioBuffer = await ctx.decodeAudioData(arrayBuf.slice(0));
      drawWaveform(audioBuffer.getChannelData(0));
      ctx.close();
    } catch (e) {
      waveCanvas.classList.add("hidden");
    }

    el("results").classList.add("hidden");
    el("emptyState").classList.add("hidden");
  }

  function drawWaveform(data) {
    waveCanvas.classList.remove("hidden");
    const dpr = window.devicePixelRatio || 1;
    const width = waveCanvas.clientWidth || 600;
    const height = 72;
    waveCanvas.width = width * dpr;
    waveCanvas.height = height * dpr;
    const ctx = waveCanvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const styles = getComputedStyle(document.documentElement);
    ctx.strokeStyle = styles.getPropertyValue("--accent").trim() || "#0071e3";
    ctx.lineWidth = 1.4;

    const step = Math.ceil(data.length / width);
    const mid = height / 2;
    ctx.beginPath();
    for (let x = 0; x < width; x++) {
      let min = 1.0, max = -1.0;
      for (let j = 0; j < step; j++) {
        const idx = x * step + j;
        if (idx >= data.length) break;
        const v = data[idx];
        if (v < min) min = v;
        if (v > max) max = v;
      }
      ctx.moveTo(x, mid + min * mid);
      ctx.lineTo(x, mid + max * mid);
    }
    ctx.stroke();
  }

  // -------------------------------- analyze ----------------------------------

  analyzeBtn.addEventListener("click", runPipeline);

  async function runPipeline() {
    if (!state.audioBlob) return;
    analyzeBtn.disabled = true;

    const pipelinePanel = el("pipelinePanel");
    const progressFill = el("progressFill");
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
      await new Promise((r) => setTimeout(r, 180));
    }

    const form = new FormData();
    if (state.useSample) {
      form.append("use_sample", "true");
    } else {
      form.append("audio", state.audioBlob, "clip.wav");
      form.append("use_sample", "false");
    }
    form.append("unknown_number", el("toggleUnknown").checked);
    form.append("transaction_request", el("toggleTransaction").checked);
    form.append("high_urgency", el("toggleUrgency").checked);
    form.append("allow_max", allowMax.value);
    form.append("flag_max", flagMax.value);

    let data;
    try {
      const res = await fetch("/api/analyze", { method: "POST", body: form });
      data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analysis failed");
    } catch (err) {
      progressLabel.textContent = "Error: " + err.message;
      analyzeBtn.disabled = false;
      return;
    }

    progressFill.style.width = "100%";
    progressLabel.textContent = "Done.";
    await new Promise((r) => setTimeout(r, 200));
    pipelinePanel.classList.add("hidden");
    progressFill.style.width = "0%";
    analyzeBtn.disabled = false;

    renderResults(data);
  }

  function scoreColor(v) {
    if (v > 65) return "var(--block)";
    if (v > 30) return "var(--flag)";
    return "var(--allow)";
  }

  function setGauge(ringId, valueId, value) {
    const ring = el(ringId);
    const offset = CIRC - (Math.min(100, Math.max(0, value)) / 100) * CIRC;
    ring.style.stroke = scoreColor(value);
    requestAnimationFrame(() => { ring.style.strokeDashoffset = offset; });
    el(valueId).textContent = Math.round(value);
  }

  const ACTION_META = {
    ALLOW: { label: "Allow", cls: "allow", icon: '<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' },
    FLAG_FOR_CALLBACK: { label: "Flag for callback", cls: "flag", icon: '<path d="M12 9v4m0 4h.01M10.3 3.9 2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' },
    BLOCK: { label: "Block", cls: "block", icon: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/><path d="m6 6 12 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' },
  };

  function renderResults(data) {
    el("emptyState").classList.add("hidden");
    el("results").classList.remove("hidden");

    setGauge("acousticRing", "acousticValue", data.acoustic_risk);
    setGauge("compositeRing", "compositeValue", data.composite_risk);

    const meta = ACTION_META[data.action];
    const badge = el("actionBadge");
    badge.className = "action-badge " + meta.cls;
    el("actionIcon").innerHTML = meta.icon;
    el("actionLabel").textContent = meta.label;

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

    const metaWrap = el("metadataList");
    metaWrap.innerHTML = "";
    data.metadata_contributions.forEach((c) => {
      const row = document.createElement("div");
      row.className = "metadata-item" + (c.active ? " active" : "");
      row.innerHTML = `<span class="dot"></span><span>${c.label}</span>${c.active ? `<span class="pts">+${c.points}</span>` : ""}`;
      metaWrap.appendChild(row);
    });

    el("rawFeatures").textContent = JSON.stringify(data.raw_features, null, 2);
  }

  syncThresholds();
})();
