const els = {
  setupPanel: document.getElementById("setupPanel"),
  interviewPanel: document.getElementById("interviewPanel"),
  reportPanel: document.getElementById("reportPanel"),
  startForm: document.getElementById("startForm"),
  resumeInput: document.getElementById("resumeInput"),
  jobDescriptionInput: document.getElementById("jobDescriptionInput"),
  startButton: document.getElementById("startButton"),
  connectionStatus: document.getElementById("connectionStatus"),
  sessionLabel: document.getElementById("sessionLabel"),
  questionAudio: document.getElementById("questionAudio"),
  questionText: document.getElementById("questionText"),
  listeningCard: document.getElementById("listeningCard"),
  liveStateTitle: document.getElementById("liveStateTitle"),
  recordingTimer: document.getElementById("recordingTimer"),
  interviewMessage: document.getElementById("interviewMessage"),
  errorToast: document.getElementById("errorToast"),
  reportSummary: document.getElementById("reportSummary"),
  overallScore: document.getElementById("overallScore"),
  recommendation: document.getElementById("recommendation"),
  dimensionScores: document.getElementById("dimensionScores"),
  strengths: document.getElementById("strengths"),
  weaknesses: document.getElementById("weaknesses"),
  improvementAreas: document.getElementById("improvementAreas"),
  studyRecommendations: document.getElementById("studyRecommendations"),
  communicationAdvice: document.getElementById("communicationAdvice"),
  missingConcepts: document.getElementById("missingConcepts"),
};

const silenceThreshold = 0.018;
const silenceLimitMs = 1500;
const maxAnswerMs = 90000;
const minSpeechMs = 650;

let socket = null;
let sessionId = null;
let micStream = null;
let audioContext = null;
let mediaSource = null;
let recorderNode = null;
let analyser = null;
let silentMonitor = null;
let recordingChunks = [];
let recordingSampleRate = 44100;
let recordingStartedAt = 0;
let speechStartedAt = 0;
let lastVoiceAt = 0;
let timerId = null;
let vadId = null;
let receivedQuestionCount = 0;
let isCapturing = false;

els.startForm.addEventListener("submit", startInterview);
els.questionAudio.addEventListener("ended", beginLiveAnswerCapture);
els.questionAudio.addEventListener("play", () => {
  if (!isCapturing) {
    setLiveState("Question playing", "Listen to the full question. I will start listening when it ends.", "idle");
  }
});

async function startInterview(event) {
  event.preventDefault();
  hideError();

  const resume = els.resumeInput.files[0];
  const jobDescription = els.jobDescriptionInput.value.trim();
  if (!resume || !jobDescription) {
    showError("Resume PDF and job description are required.");
    return;
  }

  setStartLoading(true);
  setStatus("Requesting microphone");

  try {
    await ensureMicrophone();
    const formData = new FormData();
    formData.append("resume", resume);
    formData.append("job_description", jobDescription);

    setStatus("Planning");
    const response = await fetch("/api/interview/start", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Failed to start interview.");
    }

    sessionId = payload.session_id;
    receivedQuestionCount = 0;
    els.questionText.textContent = payload.first_question || "";
    els.sessionLabel.textContent = `Session ${sessionId}`;
    showPanel("interview");
    connectSocket();
  } catch (error) {
    showError(error.message);
    setStatus("Ready");
    stopMicrophone();
  } finally {
    setStartLoading(false);
  }
}

async function ensureMicrophone() {
  if (micStream) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error("This browser does not support microphone recording.");
  }
  micStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
}

function connectSocket() {
  if (socket) {
    socket.disconnect();
  }

  setLiveState("Connecting", "Connecting to the voice interview...", "idle");
  socket = io();

  socket.on("connect", () => {
    setStatus("Connected");
    socket.emit("join", { session_id: sessionId });
  });

  socket.on("disconnect", () => {
    setStatus("Disconnected");
    stopCapture(false);
  });

  socket.on("question", ({ audio }) => {
    receivedQuestionCount += 1;
    if (receivedQuestionCount > 1) {
      els.questionText.textContent = "";
    }
    stopCapture(false);
    setLiveState("Question playing", "Listen to the question. Live listening starts automatically afterward.", "idle");
    playQuestionAudio(audio);
  });

  socket.on("finished", () => {
    setStatus("Finished");
    stopCapture(false);
    stopMicrophone();
    setLiveState("Complete", "Interview complete. Loading report...", "idle");
    loadReport();
  });

  socket.on("error", ({ message }) => {
    showError(message || "Interview socket error.");
    setLiveState("Error", "An error occurred. Check the message and try again.", "idle");
    stopCapture(false);
  });
}

function playQuestionAudio(audio) {
  const bytes = normalizeBinary(audio);
  const blob = new Blob([bytes], { type: "audio/mpeg" });
  const url = URL.createObjectURL(blob);
  if (els.questionAudio.src) {
    URL.revokeObjectURL(els.questionAudio.src);
  }
  els.questionAudio.src = url;
  els.questionAudio.play().catch(() => {
    setLiveState("Question ready", "Press play on the audio control. I will listen automatically when it ends.", "idle");
  });
}

async function beginLiveAnswerCapture() {
  if (!socket || !sessionId || isCapturing) return;

  try {
    await ensureMicrophone();
    startCapture();
  } catch (error) {
    showError(error.message);
    setLiveState("Microphone blocked", "Allow microphone access, then restart the interview.", "idle");
  }
}

function startCapture() {
  stopCapture(false);
  recordingChunks = [];
  audioContext = new AudioContext();
  recordingSampleRate = audioContext.sampleRate;
  mediaSource = audioContext.createMediaStreamSource(micStream);
  recorderNode = audioContext.createScriptProcessor(4096, 1, 1);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 1024;
  silentMonitor = audioContext.createGain();
  silentMonitor.gain.value = 0;

  recorderNode.onaudioprocess = (event) => {
    recordingChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
  };

  mediaSource.connect(analyser);
  mediaSource.connect(recorderNode);
  recorderNode.connect(silentMonitor);
  silentMonitor.connect(audioContext.destination);

  recordingStartedAt = Date.now();
  speechStartedAt = 0;
  lastVoiceAt = 0;
  isCapturing = true;
  timerId = window.setInterval(updateTimer, 250);
  vadId = window.setInterval(checkVoiceActivity, 120);
  updateTimer();
  setLiveState("Listening", "Start speaking. I will submit automatically after you pause.", "listening");
}

function checkVoiceActivity() {
  if (!analyser || !isCapturing) return;

  const data = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(data);
  let sum = 0;
  for (const sample of data) {
    sum += sample * sample;
  }
  const rms = Math.sqrt(sum / data.length);
  const now = Date.now();

  if (rms > silenceThreshold) {
    if (!speechStartedAt) {
      speechStartedAt = now;
    }
    lastVoiceAt = now;
    setLiveState("Listening", "I can hear you. Keep going until your answer is complete.", "speaking");
    return;
  }

  if (!speechStartedAt) {
    if (now - recordingStartedAt > 10000) {
      setLiveState("Listening", "I am still listening. Start your answer when ready.", "listening");
    }
    return;
  }

  const speechDuration = lastVoiceAt - speechStartedAt;
  const silenceDuration = now - lastVoiceAt;
  const totalDuration = now - recordingStartedAt;
  if ((speechDuration >= minSpeechMs && silenceDuration >= silenceLimitMs) || totalDuration >= maxAnswerMs) {
    finishAndSubmitAnswer();
  } else {
    setLiveState("Listening", "Brief pause detected. Continue speaking or pause to submit.", "listening");
  }
}

function finishAndSubmitAnswer() {
  if (!isCapturing) return;

  const samples = mergeBuffers(recordingChunks);
  stopCapture(false);

  if (samples.length < recordingSampleRate / 2) {
    setLiveState("Listening", "I did not catch enough audio. Please answer again after the next prompt.", "listening");
    beginLiveAnswerCapture();
    return;
  }

  const answerAudio = encodeWav(samples, recordingSampleRate);
  setLiveState("Processing", "Submitting your answer for transcription and evaluation...", "idle");
  socket.emit("answer", {
    session_id: sessionId,
    audio: answerAudio,
  });
}

function stopCapture(closeStream) {
  if (vadId) window.clearInterval(vadId);
  if (timerId) window.clearInterval(timerId);
  vadId = null;
  timerId = null;

  if (recorderNode) {
    recorderNode.disconnect();
    recorderNode.onaudioprocess = null;
  }
  if (mediaSource) mediaSource.disconnect();
  if (silentMonitor) silentMonitor.disconnect();
  if (audioContext) audioContext.close();
  if (closeStream) stopMicrophone();

  recorderNode = null;
  mediaSource = null;
  analyser = null;
  silentMonitor = null;
  audioContext = null;
  isCapturing = false;
  els.recordingTimer.textContent = "00:00";
}

function stopMicrophone() {
  if (!micStream) return;
  micStream.getTracks().forEach((track) => track.stop());
  micStream = null;
}

async function loadReport() {
  showPanel("report");
  try {
    const response = await fetch(`/api/interview/${sessionId}/report`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Failed to load report.");
    }
    renderReport(payload);
  } catch (error) {
    showError(error.message);
    els.reportSummary.textContent = "Report could not be loaded.";
  }
}

function renderReport(payload) {
  const report = payload.final_report || {};
  const notes = payload.coaching_notes || {};

  els.reportSummary.textContent = report.summary || "No summary available.";
  els.overallScore.textContent = formatScore(report.overall_score);
  setOverallScore(report.overall_score);
  els.recommendation.textContent = report.recommendation || "No recommendation available.";

  renderScores(report.scores_by_dimension || {});
  renderList(els.strengths, report.strengths);
  renderList(els.weaknesses, report.weaknesses);
  renderList(els.improvementAreas, notes.improvement_areas);
  renderList(els.studyRecommendations, notes.study_recommendations);
  renderList(els.communicationAdvice, notes.communication_advice);
  renderList(els.missingConcepts, notes.missing_concepts);
}

function renderScores(scores) {
  els.dimensionScores.innerHTML = "";
  const entries = Object.entries(scores);
  if (!entries.length) {
    els.dimensionScores.textContent = "No dimension scores available.";
    return;
  }
  for (const [name, score] of entries) {
    const percent = scorePercent(score);
    const row = document.createElement("div");
    row.className = "score-row";
    row.innerHTML = `
      <div class="score-row-top">
        <span>${escapeHtml(name)}</span>
        <strong>${escapeHtml(formatScore(score))}</strong>
      </div>
      <div class="score-track"><span class="score-fill" style="--score-width: ${percent}%"></span></div>
    `;
    els.dimensionScores.appendChild(row);
  }
}

function renderList(target, values) {
  target.innerHTML = "";
  const items = Array.isArray(values) ? values : [];
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = "No items available.";
    target.appendChild(li);
    return;
  }
  for (const value of items) {
    const li = document.createElement("li");
    li.textContent = value;
    target.appendChild(li);
  }
}

function mergeBuffers(chunks) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const merged = new Float32Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }
  return merged;
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (const sample of samples) {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += 2;
  }

  return buffer;
}

function writeString(view, offset, value) {
  for (let i = 0; i < value.length; i += 1) {
    view.setUint8(offset + i, value.charCodeAt(i));
  }
}

function normalizeBinary(value) {
  if (value instanceof ArrayBuffer) return value;
  if (ArrayBuffer.isView(value)) return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength);
  if (Array.isArray(value)) return new Uint8Array(value).buffer;
  return value;
}

function updateTimer() {
  const elapsed = Math.floor((Date.now() - recordingStartedAt) / 1000);
  const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const seconds = String(elapsed % 60).padStart(2, "0");
  els.recordingTimer.textContent = `${minutes}:${seconds}`;
}

function setStartLoading(isLoading) {
  els.startButton.disabled = isLoading;
  els.startButton.textContent = isLoading ? "Starting live interview..." : "Start live interview";
}

function setStatus(value) {
  els.connectionStatus.textContent = value;
}

function setLiveState(title, message, state) {
  els.liveStateTitle.textContent = title;
  els.interviewMessage.textContent = message;
  els.listeningCard.classList.toggle("is-listening", state === "listening");
  els.listeningCard.classList.toggle("is-speaking", state === "speaking");
}

function showPanel(name) {
  els.setupPanel.classList.toggle("hidden", name !== "setup");
  els.interviewPanel.classList.toggle("hidden", name !== "interview");
  els.reportPanel.classList.toggle("hidden", name !== "report");
}

function showError(message) {
  els.errorToast.textContent = message;
  els.errorToast.classList.remove("hidden");
}

function hideError() {
  els.errorToast.classList.add("hidden");
  els.errorToast.textContent = "";
}

function formatScore(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "--";
  return numeric.toFixed(1);
}

function scorePercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(100, numeric * 10));
}

function setOverallScore(value) {
  const ring = document.getElementById("scoreRing");
  if (!ring) return;
  ring.style.setProperty("--score-angle", `${scorePercent(value) * 3.6}deg`);
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = String(value);
  return span.innerHTML;
}
