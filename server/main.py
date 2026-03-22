import os
import cv2
from flask import Flask, Response, request, jsonify
from flask_socketio import SocketIO, emit 
from flask_cors import CORS
import time 
from math import sin,cos,sqrt,radians
#sssss
#librerie custom che ho fatto io per l'AI
from Tars_functionalities.AI_part.gemini import GeminiBot
from Tars_functionalities.AI_part.robot_Perceptions import RobotPerception
from robot_control import Robot_Hardware

#Su portatile,usa python piu vecchio per vedere le librerie
#to do:cosa sono CORS
#pip install eventlet #pip install flask_socketIO
'''
In informatica, 0.0.0.0 è un indirizzo speciale che significa "ascolta su tutte le reti possibili". 
Va bene per il Server (per dire "accetto connessioni da chiunque"),
'''
def convert_joystick_data(power,angle):
    angle = radians(angle) #converto l'angolo in radianti
    max_power = 100
    power_norm = int(power/(power/100)) 

    motordx = int(  power_norm*( sin(angle) - cos(angle)    ) )
    
    motorsx = int(   power_norm*(  sin(angle) + cos(angle)   ) )

    #limita motordx e motorsx tra -100 e 100
    motordx = max(-100,min(100,motordx))
    motorsx = max(-100,min(100,motordx))

    return (motordx,motorsx)




base_path = os.path.dirname(os.path.abspath(__file__))
keyword_path = os.path.join(base_path, "Tars_functionalities", "Hey_tars.ppn")
#classi custom per l'ai e controllo robot

Geminibot = GeminiBot()
Robotperception = RobotPerception(keyword_path=keyword_path)

try:
    Robot_hardware = Robot_Hardware()
except:
    print("error on initializing motor control library,\n" \
    "please make sure u are on a raspberry")


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

Robotperception.start_capture() #avvia la cattura del frame in un altro thread

#STREAM VIDEO MJPEG(da errore qui non so perchè)(confronta con codice vecchio senza)
#la tua libreria
def gen_frames():
    while True:
        frame = Robotperception.get_latest_frame()
        if frame is None:
            time.sleep(0.01) # Evita di friggere la CPU se il frame non è pronto
            continue 
        
        # Encoding
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

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
    print(f"motori corrispondenti(dx e sx)---> {convert_joystick_data(distance,angle)}")

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
    #manda al client una risposta

if __name__ == '__main__':
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    
    print("--- TARS SERVER STARTING ON PORT 8000 (GEVENT) ---")
    # IMPORTANTE: Su Windows, con i socket, il debugger a volte rompe. 
    # Prova prima con debug=False per stabilizzare.
    socketio.run(app, debug=True,port=8000)



