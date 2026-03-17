//ASSICURA DI USARE LO STESSO TIPO DI PROTOCOLLO PER I SOCKET TRA SERVER E CLIENT
//IL SERVER USA SOCKETIO
// --- VECCHIO (Standard WebSocket - NON FUNZIONA CON FLASK-SOCKETIO) ---
// const socket = new WebSocket('ws://localhost:8000');

// --- NUOVO (Socket.IO Client) ---
const socket = io('http://127.0.0.1:8000');


//--------------SOCKET-------------------------//


// 1. Gestione JOYCON
const joyManager = nipplejs.create({
    zone: document.getElementById('joycon-zone'),
    mode: 'static',
    position: {left: '50%', top: '50%'},
    color: 'white'
});

// Gestione JOYCON
joyManager.on('move', (evt, data) => {
    const movement = {
        angle: data.angle.degree,
        distance: data.distance 
    };

    // Socket.IO usa 'emit' e gestisce lui la conversione in JSON
    socket.emit('move', movement);
});

// Aggiungi questo per ricevere i messaggi dal server (es. "TARS ONLINE")
socket.on('status', (data) => {
    const log = document.getElementById('output-log');
    log.innerHTML += `<div>[SERVER]: ${data.msg}</div>`;
    log.scrollTop = log.scrollHeight; // Auto-scroll verso il basso
});

// Gestione errori di connessione
socket.on('connect_error', (err) => {
    // 1. Stampa l'errore tecnico nella console del browser (F12)
    console.error("Dettaglio Errore Socket:", err);
});

// 2. Registrazione AUDIO
let mediaRecorder;
let audioChunks = [];

//gestore cattura msg vocale
//quando la registrazione termina,il messaggio viene automaticamente inviato
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
            // Qui invii il blob al server tramite POST o WebSocket
            sendAudio(audioBlob);
            audioChunks = [];
        };
    }
};


// Gestione click sul pulsante INVIO
document.getElementById('btn-send').onclick = () => {
    const input = document.getElementById('command-input');
    const message = input.value.trim(); // .trim() rimuove spazi vuoti inutili

    if (message !== "") {
        // 1. Invia il messaggio al server tramite la funzione che hai già creato
        sendMessage(message);

        // 2. Opzionale: Mostra il messaggio inviato nel log locale (feedback visivo)
        const log = document.getElementById('output-log');
        log.innerHTML += `<div style="color: #00ff00;">[YOU]: ${message}</div>`;
        log.scrollTop = log.scrollHeight;

        // 3. Pulisci l'input per il prossimo comando
        input.value = "";
    }
};

function sendAudio(blob) {
    const formData = new FormData();
    formData.append('voice', blob);
    fetch('http://localhost:8000/upload_audio', { method: 'POST', body: formData });
}

function sendMessage(msg_user)
{
//nel server : @socketio.on('chat_message')
socket.emit('chat_message', msg_user);

}

const vFeed = document.querySelector('#video-feed img');

var video_active = 0;
var video_lost = 0;
// Quando l'immagine riesce a caricare lo stream dal server
vFeed.onload = function() {
    if (video_active == 0){
    vFeed.classList.add('streaming');
    document.getElementById('output-log').innerHTML += "<div>[SYSTEM]: VIDEO STREAM CONNECTED</div>";
    video_active = 1;
    video_lost = 0;}
};

// Se lo stream cade o l'URL non è raggiungibile
vFeed.onerror = function() {
    if (video_lost ==0){
    vFeed.classList.remove('streaming');
    document.getElementById('output-log').innerHTML += "<div style='color:var(--tars-red)'>[WARN]: VIDEO SIGNAL LOST</div>";
    video_lost = 1;
    video_active = 0;}

};

// Gestione pulizia log
document.getElementById('btn-clear').onclick = () => {
    const log = document.getElementById('output-log');
    log.innerHTML = "<div>[SYSTEM]: LOG PURGED.</div>";
};

// Se vuoi che l'input di testo venga inviato anche premendo INVIO sulla tastiera:
document.getElementById('command-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('btn-send').click();
    }
});