import os
import cv2
from flask import Flask, Response, request, jsonify
from flask_socketio import SocketIO, emit 
from flask_cors import CORS

#Su portatile,usa python piu vecchio per vedere le librerie
#to do:cosa sono CORS
#pip install eventlet #pip install flask_socketIO
'''
In informatica, 0.0.0.0 è un indirizzo speciale che significa "ascolta su tutte le reti possibili". 
Va bene per il Server (per dire "accetto connessioni da chiunque"),
'''

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
socketio = SocketIO(app,cors_allowed_origins="*")


# Stato interno di TARS (il "Cervello")
tars_state = {
    "honesty": 70,
    "is_listening": False,
    "last_command": None
}

# --- 1. STREAMING VIDEO (MJPEG) ---
def gen_frames():
    camera = cv2.VideoCapture(0) # 0 = webcam. Cambia se hai una cam specifica.
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Opzionale: qui potresti disegnare overlay su 'frame' usando OpenCV
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
 #Gemini ha detto
#Il funzionamento di video_feed si basa su un protocollo chiamato MJPEG (Motion JPEG).  
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# --- 2. RICEZIONE AUDIO (HTTP POST) ---
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'voice' not in request.files:
        return jsonify({"status": "error", "message": "No file"}), 400
    
    audio_file = request.files['voice']
    path = os.path.join("uploads", "command.wav")
    audio_file.save(path)
    
    # Qui inseriresti la tua logica di Speech-to-Text
    print(f"[AUDIO]: Ricevuto file vocale salvato in {path}")
    return jsonify({"status": "received", "action": "processing_voice"})


# --- 3. LOGICA REAL-TIME (WebSockets) ---

@socketio.on('connect')
def test_connect():
    print("[SYSTEM]: Client connesso alla stazione di controllo.")
    emit('status', {'msg': 'CONNESSIONE STABILITA - TARS ONLINE'})

@socketio.on('move')
def handle_move(data):
    # Dati dal Joycon: angle (0-360) e distance (intensità)
    angle = data.get('angle')
    distance = data.get('distance')
    
    # LOGICA DI MOVIMENTO (Qui entra in gioco il tuo lavoro di progettista)
    # Dovrai convertire questi valori in velocità per i motori
    print(f"[NAV]: Angolo {angle:.2f} | Forza {distance:.2f}")

@socketio.on('update_param')
def handle_params(data):
    if 'honesty' in data:
        tars_state['honesty'] = data['honesty']
        print(f"[SYS]: Livello Onestà impostato al {tars_state['honesty']}%")
        
        # Risposta dinamica basata sull'onestà
        if tars_state['honesty'] < 10:
            emit('status', {'msg': 'WARNING: LIVELLO ONESTÀ CRITICO. POSSIBILI DATI ALTERATI.'})

@socketio.on('chat_message')
def handle_message(msg):
    print(f"[CMD]: Ricevuto ordine testuale: {msg}")
    # Risposta di TARS al log del client
    emit('status', {'msg': f'ESECUZIONE: {msg.upper()}'})

if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    
    print("--- TARS SERVER STARTING ON PORT 8000 (GEVENT) ---")
    # IMPORTANTE: Su Windows, con i socket, il debugger a volte rompe. 
    # Prova prima con debug=False per stabilizzare.
    socketio.run(app, debug=True,port=8000)