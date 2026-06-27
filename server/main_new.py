import os
import cv2
import time
from math import sin, cos, radians
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import subprocess
from gtts import gTTS
# Aggiungi questo import in alto nel file per gestire i tipi dell'SDK
from google.generativeai.types import content_types
from google.generativeai.protos import Part
import atexit # <--- Aggiungi questo import



# Librerie custom (Assicurate che siano nel path)
from Tars_functionalities.AI_part.gemini import GeminiBot
from Tars_functionalities.AI_part.robot_Perceptions import RobotPerception
from robot_control import Robot_Hardware,Robot_Hardware_Mock
from PIL import Image

def cattura_visione_tars():
    """Cattura il frame attuale dalla telecamera e restituisce i byte JPG e l'oggetto PIL."""
    success, frame = camera.read()
    if success:
        # 1. Salviamo l'immagine localmente nel path richiesto
        cv2.imwrite("captured_frame.jpg", frame)
        print("[SYS]: Immagine salvata localmente in 'captured_frame.jpg'")
        
        # 2. Codifichiamo in formato JPG per inviarla come byte a Gemini
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            return buffer.tobytes()
    return None

def richiedi_accesso_visivo():
    """
    Chiama questa funzione SOLO quando l'utente ti chiede implicitamente o 
    esplicitamente  di guardare, vedere o descrivere qualcosa nell'ambiente circostante.
    includi nella risposta la stringa di ritorno
    """

    print("gemini sta catturando l'immagine....")
    return "FLAG_IMMAGINE_RICHIESTA"

def text_to_speech(text):
    # Genera l'audio tramite Google e lo salva
    tts = gTTS(text=text, lang='it')
    audio_file = "tars_voice.mp3"
    tts.save(audio_file)
    
    # Riproduce il file (-q sta per quiet, nasconde l'output sul terminale)
    subprocess.run(["mpg123", "-q", audio_file])
    
    # Elimina il file per non intasare la memoria
    os.remove(audio_file)


# Funzione di pulizia
def cleanup():
    if camera.isOpened():
        camera.release()
        print("[SYS]: Camera rilasciata correttamente.")
    cv2.destroyAllWindows()

# Registra la funzione per essere chiamata alla chiusura
atexit.register(cleanup)


def convert_joystick_data(power, angle):
    angle_rad = radians(angle)
    # Calcolo semplificato per trazione differenziale
    motordx = int(power * (sin(angle_rad) - cos(angle_rad)))
    motorsx = int(power * (sin(angle_rad) + cos(angle_rad)))

    # Limita tra -100 e 100
    motordx = max(-100, min(100, motordx))
    motorsx = max(-100, min(100, motorsx))
    return (motordx, motorsx)

# Inizializzazione Hardware e AI
base_path = os.path.dirname(os.path.abspath(__file__))
keyword_path = os.path.join(base_path, "Tars_functionalities", "Hey_tars.ppn")

Geminibot = GeminiBot()
Robotperception = RobotPerception(keyword_path=keyword_path)



# Variabili globali "di emergenza"

# --- INIZIALIZZAZIONE HARDWARE SICURA ---
motors_sensors = None

# --- INIZIALIZZAZIONE HARDWARE SICURA ---
try:
    motors_sensors = Robot_Hardware()
    print("[SYS]: Hardware reale inizializzato con successo.")
except Exception as e:
    print(f"[WARNING]: Impossibile inizializzare l'hardware reale: {e}")
    # Se fallisce, usiamo l'oggetto Mock invece di None
    motors_sensors = Robot_Hardware_Mock()

app = Flask(__name__)
CORS(app) # Fondamentale per far comunicare il frontend con il backend

# Stato interno
tars_state = {
    "honesty": 70,
    "is_listening": False,
}

#Robotperception.start_capture() da problemi!!!

# --- INIZIALIZZAZIONE CAMERA ---
# Inizializziamo la camera globalmente per evitare di riaprirla a ogni richiesta
camera = cv2.VideoCapture(0) 

# Opzionale: Imposta risoluzione per non saturare la banda (MJPEG è pesante)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 20)

if not camera.isOpened():
    print("[ERROR]: Impossibile accedere alla telecamera.")

# --- 1. VIDEO STREAMING (OpenCV + MJPEG) ---
def gen_frames():
    while True:
        # Cattura frame-by-frame
        success, frame = camera.read()
        if not success:
            print("frame inesistente")
            # Se la camera fallisce, non crashare il thread, aspetta e riprova
            time.sleep(0.1)
            continue
        else:
            # Codifica in JPG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            # Formato MJPEG standard
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            



@app.route('/video_feed')
def video_feed():
    # MJPEG è uno standard HTTP nativo, non servono socket qui.
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- 2. MOVIMENTO (HTTP POST) ---
@app.route('/move', methods=['POST'])
def move_robot():
    data = request.json
    angle = data.get('angle', 0)
    distance = data.get('distance', 0)
    
    dx, sx = convert_joystick_data(distance, angle)
    
    # Qui invieresti i comandi all'hardware
    # Robot_hardware.set_motors(dx, sx)
    
    print(f"[NAV]: Angolo {angle} | Forza {distance} -> MOTORI: DX:{dx} SX:{sx}")
    motors_sensors.set_motors(dx,sx)
    return jsonify({"status": "ok", "motors": [dx, sx]})

#sistemiamo dopo per il func calling
try:
    Geminibot.start_function_chat(
    tools=[motors_sensors.set_motors, richiedi_accesso_visivo],
    enable_automatic_function_calling=False 
)
    print("[SYS]: Sessione Gemini avviata in modalità MANUALE.")
except Exception as e:
    print(f"Fallimento nell'inizializzazione della sessione: {e}")

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "JSON mancante"}), 400
            
        msg = data.get('msg', ' ')
        honesty = data.get('honesty', '90')
        
        full_message = f"utente: {msg} \nistruzioni: sei TARS; livello onestà: {honesty}%"

        # 1. Inviamo il messaggio iniziale
        response = Geminibot.session.send_message(full_message)

        # 2. Setup per la gestione manuale del Function Calling
        function_responses = []
        immagini_da_inviare = [] # Buffer per le immagini richieste

        # Iteriamo sulle parti della risposta per trovare chiamate a funzioni

        print(response)

        for part in response.parts:
            if fn := part.function_call:

                '''
                Serve a fare due cose contemporaneamente, all'interno della stessa istruzione:
                Assegna un valore a una variabile.
                Restituisce immediatamente quel valore, permettendo di valutarlo al volo (ad esempio 
                in una condizione if o while).
                in questa condizione si verifica se fn è not null(cioè se if fn è true)
                '''
                print(f"[SYS]: Gemini ha richiesto l'esecuzione di: {fn.name}")
                
                # --- FUNZIONE: VISIONE ---
                if fn.name == "richiedi_accesso_visivo":
                    immagine = cattura_visione_tars()
                    
                    if immagine:
                        esito = {"text": "Immagine allegata nella richiesta corrente."}
                        immagini_da_inviare.append({"image" : "captured_frame.jpg"})
                    else:
                        esito = {"text":  "Camera offline o non accessibile."}
                    
                    # Creiamo l'oggetto di risposta della funzione
                    function_responses.append(
                        esito
                    )
                
                # --- FUNZIONE: MOTORI ---
                elif fn.name == "set_motors": #DA SISTEMARE!!!
                    # Estraiamo gli argomenti convertendoli in un dizionario Python standard
                    argomenti = type(fn).to_dict(fn).get('args', {})
                    dx = argomenti.get('dx', 0)
                    sx = argomenti.get('sx', 0)
                    
                    # Eseguiamo il comando sull'hardware
                    motors_sensors.set_motors(dx, sx)
                    
                    # Creiamo l'oggetto di risposta
                    function_responses.append(
                        Part.from_function_response(
                            name=fn.name, 
                            response={"status": "movimento completato", "dx_eseguito": dx, "sx_eseguito": sx}
                        )
                    )

        # 3. Se ci sono state chiamate a funzioni, chiudiamo il ciclo rimandando i dati
        if function_responses:
            # Uniamo le risposte delle funzioni e l'eventuale immagine catturata in un'unica lista
            elementi_da_inviare = function_responses + immagini_da_inviare
            prompt = Geminibot._normalize_prompt(elementi_da_inviare)
            print("[SYS]: Invio esiti delle funzioni (e/o dati ottici) a Gemini...")
            # Un SOLO send_message per chiudere il turno e ottenere il testo finale
            response = Geminibot.session.send_message(prompt)

        # 4. Estraiamo il testo della risposta finale
        text_resp = response.text 

        # 5. Generiamo l'audio e rispondiamo al client
        text_to_speech(text=text_resp)
        return jsonify({"status": "ok", "reply": text_resp})

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[ERROR] {error_type}: {error_msg}")
        return jsonify({"status": "error", "type": error_type, "details": error_msg}), 500


# --- 5. UPLOAD AUDIO ---
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'voice' not in request.files:
        return jsonify({"status": "error", "message": "No file"}), 400
    
    audio_file = request.files['voice']
    path = os.path.join("uploads", "command.wav")
    audio_file.save(path)
    return jsonify({"status": "received", "path": path})


if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    # 1. Definiamo cosa deve fare TARS quando sente la hotword
    def reazione_hotword(keyword):
        print(f"[HOTWORD]: Rilevata {keyword}! TARS è in ascolto...")
        # Esempio: registra un campione o cambia uno stato
        # robot_perception.record_audio_sample_windows() 

    # 2. Avviamo il listener PRIMA di Flask
    # Gira in un thread separato (grazie a RobotPerception)
    Robotperception.start_hotword_listener(
        sensitivities=[0.5],
        callback=reazione_hotword
    )

    print("[SYS]: Hotword listener avviato in background.")

    # 3. Avviamo Flask (che blocca il thread principale)
    app.run(host='0.0.0.0', port=8000, debug=True, threaded=True, use_reloader=False)