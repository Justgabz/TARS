// Configurazione Base
const SERVER_URL = "http://127.0.0.1:8000";

// Funzione di utilità per aggiornare il log (centralizzata)
function updateLog(msg, color = "white") {
    const log = document.getElementById('output-log');
    log.innerHTML += `<div style="color: ${color}">${msg}</div>`;
    log.scrollTop = log.scrollHeight;
}

// --- 1. VIDEO STREAMING (MJPEG) ---
// Con MJPEG non serve JS per i frame. Basta puntare l'src dell'immagine all'URL.
const vFeed = document.getElementById('robot-view'); 
vFeed.src = `${SERVER_URL}/video_feed`;

vFeed.onload = () => updateLog("[SYSTEM]: VIDEO STREAM CONNECTED", "white");
vFeed.onerror = () => updateLog("[WARN]: VIDEO SIGNAL LOST", "var(--tars-red)");


// --- 2. JOYCON (MOVIMENTO) ---
const joyManager = nipplejs.create({
    zone: document.getElementById('joycon-zone'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: 'white'
});

// Nota: Il joystick spara eventi DECINE di volte al secondo. 
// Con HTTP questo può intasare il server. Usiamo un piccolo controllo temporale.
let lastMoveTime = 0;

joyManager.on('move', (evt, data) => {
    const now = Date.now();
    if (now - lastMoveTime < 50) return; // Invia max 20 comandi al secondo
    lastMoveTime = now;

    const movement = {
        angle: data.angle.degree,
        distance: data.distance
    };

    fetch(`${SERVER_URL}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(movement)
    }).catch(err => console.error("Errore invio movimento:", err));
});


// --- 3. MESSAGGI DI TESTO (CHAT) ---
document.getElementById('btn-send').onclick = () => {
    const input = document.getElementById('command-input');
    const message = input.value.trim();

    if (message !== "") {
        updateLog(`[YOU]: ${message}`, "#00ff00");
        sendMessage(message);
        input.value = "";
    }
};

// --- GESTIONE SLIDER HONESTY ---
const honestySlider = document.getElementById('honesty-slider');
const honestyDisplay = document.getElementById('honesty-display');

// Aggiorna il testo accanto allo slider quando lo muovi
honestySlider.oninput = function() {
    honestyDisplay.innerText = this.value;
};

// Inizializza il display al caricamento
honestyDisplay.innerText = honestySlider.value;


// --- MODIFICA INVIO MESSAGGIO ---
async function sendMessage(msg_user) {
    const honestyValue = parseInt(honestySlider.value); // Recupera il valore attuale

    try {
        const response = await fetch(`${SERVER_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                msg: msg_user, 
                honesty: honestyValue // Inviato insieme al messaggio
            })
        });
        
        const data = await response.json();
        updateLog(`[TARS]: ${data.reply}`, "cyan");
        
    } catch (err) {
        updateLog("[ERROR]: Impossibile raggiungere TARS", "var(--tars-red)");
    }
}


// --- 4. AUDIO ---
async function sendAudio(blob) {
    const formData = new FormData();
    formData.append('voice', blob);

    try {
        updateLog("[SYS]: Invio audio in corso...");
        const response = await fetch(`${SERVER_URL}/upload_audio`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        updateLog(`[SYS]: Audio ricevuto (${data.status})`);
    } catch (err) {
        updateLog("[ERROR]: Errore caricamento audio", "red");
    }
}

// (Il resto della logica MediaRecorder rimane uguale)
let mediaRecorder;
let audioChunks = [];

document.getElementById('btn-mic').onclick = async () => {
    const btn = document.getElementById('btn-mic');
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        btn.classList.add('recording');
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    } else {
        mediaRecorder.stop();
        btn.classList.remove('recording');
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            sendAudio(audioBlob);
            audioChunks = [];
        };
    }
};

// --- PULIZIA ---
document.getElementById('btn-clear').onclick = () => {
    document.getElementById('output-log').innerHTML = "<div>[SYSTEM]: LOG PURGED.</div>";
};

document.getElementById('command-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('btn-send').click();
});