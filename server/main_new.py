import os
import cv2
import time
from math import sin, cos, radians
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import subprocess



# Librerie custom (Assicurate che siano nel path)
from Tars_functionalities.AI_part.gemini import GeminiBot
from Tars_functionalities.AI_part.robot_Perceptions import RobotPerception
from robot_control import Robot_Hardware,Robot_Hardware_Mock



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

# --- 1. VIDEO STREAMING (MJPEG su HTTP) ---
def gen_frames():
    while True:
        frame = Robotperception.get_latest_frame()
        if frame is None:
            time.sleep(0.01)
            continue 
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
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


# --- 4. MESSAGGI DI TESTO (HTTP POST) ---
@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get('msg', ' ')
    honesty = request.json.get('honesty',' ')
    print(f"[CMD]: Ricevuto: {msg} onestà : {honesty}")
        # prompt = {
        #     'text': 'Descrivi questa immagine',
        #     'image': 'C:/path/to/img.jpg',
        # }

    full_message = {'text' : f"utente:msg \n per gemini:sei TARS di interstellar;livello di onestà : {honesty}%"}

    if Geminibot.session:
        response = Geminibot.send_function_chat_message(full_message)
        print(response)
    else:
        print("sessione func calling non inizializzata")
    
    # Qui chiameresti Geminibot.ask(msg)
    return jsonify({"status": "ok", "reply": f"ESECUZIONE: {msg.upper()}"})

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

    Geminibot.start_function_chat(tools=[])

    #Robotperception.start_capture()

    # Usiamo il server integrato di Flask. 
    # NOTA: Per performance serie su Raspberry, servirebbe Gunicorn o Waitress.
    app.run(host='0.0.0.0', port=8000, debug=True, threaded=True,use_reloader=False)