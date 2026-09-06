document.querySelectorAll("form[data-busy]").forEach((form) => {
  form.addEventListener("submit", () => {
    const message = form.getAttribute("data-busy") || "Working…";
    form.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = message;
    form.appendChild(note);
  });
});

function speakText(text) {
  if (!text || !window.speechSynthesis) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

const spoken = document.getElementById("speak-text");
if (spoken && spoken.textContent.trim()) {
  speakText(spoken.textContent.trim());
}

const voiceBtn = document.getElementById("voice-btn");
const voiceStatus = document.getElementById("voice-status");
const voiceForm = document.getElementById("voice-form");
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

if (voiceBtn && !SpeechRec) {
  voiceBtn.disabled = true;
  if (voiceStatus) {
    voiceStatus.textContent =
      "Voice add needs Chrome or Edge on this computer. You can still type the number.";
  }
}

if (voiceBtn && voiceForm && SpeechRec) {
  let recognition = null;
  let listening = false;

  const setStatus = (text) => {
    if (voiceStatus) {
      voiceStatus.textContent = text;
    }
  };

  const stop = () => {
    listening = false;
    voiceBtn.classList.remove("is-listening");
    voiceBtn.setAttribute("aria-pressed", "false");
    voiceBtn.textContent = "Speak a number";
    if (recognition) {
      recognition.stop();
    }
  };

  voiceBtn.addEventListener("click", () => {
    if (listening) {
      stop();
      return;
    }

    recognition = new SpeechRec();
    recognition.lang = "en-PK";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      listening = true;
      voiceBtn.classList.add("is-listening");
      voiceBtn.setAttribute("aria-pressed", "true");
      voiceBtn.textContent = "Listening… click to stop";
      setStatus("Listening. Say the six digits, then pause.");
    };

    recognition.onerror = (event) => {
      stop();
      if (event.error === "not-allowed") {
        setStatus("Microphone permission is blocked. Allow it for this page, then try again.");
        return;
      }
      setStatus("Could not hear that. Try again, or type the number.");
    };

    recognition.onend = () => {
      if (listening) {
        stop();
      }
    };

    recognition.onresult = (event) => {
      const latest = event.results[event.results.length - 1];
      const transcript = latest[0].transcript.trim();
      setStatus("Heard: " + transcript);
      if (!latest.isFinal) {
        return;
      }
      document.getElementById("voice-transcript").value = transcript;
      document.getElementById("voice-denomination").value =
        document.getElementById("bond-denomination").value;
      document.getElementById("voice-owner").value = document.getElementById("bond-owner").value;
      stop();
      voiceForm.submit();
    };

    recognition.start();
  });
}
