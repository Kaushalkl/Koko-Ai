/**
 * =====================================================
 * KOKO AI v6.4 – AUTO LANGUAGE TEXT + VOICE (FIXED)
 * =====================================================
 */

let synth = window.speechSynthesis;
let recognition = null;
let isMicActive = false;
let hasBooted = false;

let lastUserLang = "en-US";   // en-US | hi-IN | hinglish
let lastEmotion = "neutral";

const statusText = document.getElementById("status");
const msgText = document.getElementById("msg");
const waveBox = document.getElementById("waveBox");
const logContent = document.getElementById("logContent"); // Terminal Card target

/* ---------------- TERMINAL UPDATE FUNCTION ---------------- */
function updateTerminal(text, sender) {
    if (!logContent) return;

    const entry = document.createElement("div");
    entry.className = "log-entry " + (sender === "YOU" ? "user-text" : "jarvis-text");
    
    const color = (sender === "YOU") ? "#00ffff" : "#ff4fd8";
    entry.innerHTML = `<span style="color:${color}">[${sender}]:</span> ${text}`;
    
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
}

/* ---------------- WAVE ---------------- */
function toggleWave(active) {
    waveBox?.classList.toggle("active", active);
}

/* ---------------- LANGUAGE DETECTION ---------------- */
function detectLanguage(text) {
    const hasHindi = /[\u0900-\u097F]/.test(text);
    const hasEnglish = /[a-zA-Z]/.test(text);

    if (hasHindi && hasEnglish) return "hinglish";
    if (hasHindi) return "hi-IN";
    return "en-US";
}

/* ---------------- EMOTION ---------------- */
function detectEmotion(text) {
    text = text.toLowerCase();
    if (/gussa|angry|idiot|stupid/.test(text)) return "angry";
    if (/sad|dukhi|depressed/.test(text)) return "sad";
    if (/happy|khush|awesome|great/.test(text)) return "happy";
    if (/love|jaan|miss you/.test(text)) return "loving";
    return "neutral";
}

/* ---------------- FEMALE SIRI-LIKE VOICE ---------------- */
function pickSiriLikeFemaleVoice(lang) {
    const voices = synth.getVoices();
    const siri = voices.find(v => /siri/i.test(v.name) && v.lang.startsWith(lang.split("-")[0]));
    if (siri) return siri;

    if (lang === "hi-IN") {
        return (
            voices.find(v => /kalpana/i.test(v.name)) ||
            voices.find(v => v.lang === "hi-IN") ||
            voices.find(v => /female/i.test(v.name))
        );
    }

    return (
        voices.find(v => /zira/i.test(v.name)) ||
        voices.find(v => /female/i.test(v.name) && v.lang.startsWith("en")) ||
        voices.find(v => v.lang === "en-US")
    );
}

/* ---------------- EMOTION TONE ---------------- */
function applyEmotionTone(text) {
    if (lastEmotion === "angry")
        return lastUserLang === "en-US" ? "Please calm down. " + text : "Shaant ho jaiye. " + text;
    if (lastEmotion === "sad")
        return lastUserLang === "en-US" ? "I understand. " + text : "Main samajh rahi hoon. " + text;
    if (lastEmotion === "happy") return "😄 " + text;
    return text;
}

/* ---------------- SPEAK ---------------- */
function speak(text) {
    if (!text) return;
    synth.cancel();

    text = applyEmotionTone(text);
    const utter = new SpeechSynthesisUtterance(text);

    utter.lang = lastUserLang === "hinglish" ? "hi-IN" : lastUserLang;
    utter.voice = pickSiriLikeFemaleVoice(utter.lang);
    utter.pitch = 1.3;
    utter.rate = 1.1;

    utter.onstart = () => {
        statusText.innerText = "🎙️ KOKO RESPONDING...";
        toggleWave(true);
    };

    utter.onend = () => {
        statusText.innerText = "KOKO READY";
        toggleWave(false);
        if (isMicActive) setTimeout(startListening, 600);
    };

    synth.speak(utter);
}

/* ---------------- OFFLINE BRAIN ---------------- */
function offlineBrain(cmd) {
    if (lastUserLang === "en-US") {
        if (/time/.test(cmd)) return new Date().toLocaleTimeString();
        if (/date/.test(cmd)) return new Date().toDateString();
        return "I'm offline right now, but I'm still listening.";
    }
    if (/samay|time/.test(cmd)) return new Date().toLocaleTimeString("hi-IN");
    if (/date|aaj|tarikh/.test(cmd)) return new Date().toDateString("hi-IN");
    return "Abhi main offline hoon, par sun rahi hoon.";
}

/* ---------------- SPEECH RECOGNITION ---------------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SR) {
    recognition = new SR();
    recognition.lang = "hi-IN"; 
    recognition.interimResults = false;

    recognition.onresult = async (e) => {
        const cmd = e.results[0][0].transcript;

        lastUserLang = detectLanguage(cmd);
        lastEmotion = detectEmotion(cmd);

        msgText.innerText = cmd; 
        updateTerminal(cmd, "YOU");
        statusText.innerText = "🧠 ANALYZING...";

        try {
            const res = await fetch("/process_command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command: cmd, language: lastUserLang })
            });

            if (!res.ok) throw "offline";
            const data = await res.json();

            updateTerminal(data.reply, "KOKO");
            speak(data.reply);

        } catch {
            const reply = offlineBrain(cmd);
            updateTerminal(reply, "KOKO");
            speak(reply);
        }
    };
}

/* ---------------- BOOT ---------------- */
function bootKoko() {
    if (hasBooted) return;
    hasBooted = true;

    statusText.innerText = "CORE SYNCED";
    const welcomeMsg = "KOKO online क्या हाल है बीरू? क्या मांगता है बीरू";
    
    setTimeout(() => {
        updateTerminal(welcomeMsg, "KOKO");
        speak(welcomeMsg);
    }, 800);
}

function startListening() {
    if (!recognition || synth.speaking) return;
    try {
        recognition.start();
        statusText.innerText = "🎧 LISTENING...";
        toggleWave(true);
    } catch(e) {}
}

/* ---------------- UPDATED START FUNCTION (STOP ON CLICK) ---------------- */
function startKoko() {
    // 1. Agar KOKO bol rahi hai, toh turant stop karo
    if (synth.speaking) {
        synth.cancel();
        updateTerminal("Manual Interruption: KOKO muted.", "SYSTEM");
    }

    isMicActive = true;

    // 2. Initialise ya Start Mic
    if (!hasBooted) {
        bootKoko();
    } else {
        // Recognition session ko reset karke naya start karein
        try {
            recognition.stop();
        } catch(e) {}
        
        // Chhota delay taaki voice stop hone aur mic on hone me conflict na ho
        setTimeout(() => {
            startListening();
        }, 300);
    }
}

window.addEventListener("click", bootKoko, { once: true });