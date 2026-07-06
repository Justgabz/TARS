import os
import cv2
import time
from math import sin, cos, radians
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from google.generativeai.protos import Part, FunctionResponse
import atexit
from PIL import Image
from pydub import AudioSegment
import io
import tempfile

# --- LIBRERIE CUSTOM ---
# Assicurati che questi moduli siano effettivamente raggiungibili nel tuo path
from Tars_functionalities.AI_part.gemini import GeminiBot
from Tars_functionalities.AI_part.robot_Perceptions import RobotPerception
from robot_control import Robot_Hardware, Robot_Hardware_Mock

# --- INIZIALIZZAZIONE SISTEMA ---
base_path = os.path.dirname(os.path.abspath(__file__))
keyword_path = os.path.join(base_path, "Tars_functionalities", "Hey_tars.ppn")

Geminibot = GeminiBot()
Robotperception = RobotPerception(keyword_path=keyword_path)

motors_sensors = None
try:
    motors_sensors = Robot_Hardware()
    print("[SYS]: Hardware reale inizializzato con successo.")
except Exception as e:
    print(f"[WARNING]: Impossibile inizializzare l'hardware reale: {e}")
    motors_sensors = Robot_Hardware_Mock()

app = Flask(__name__)
CORS(app)

# --- INIZIALIZZAZIONE TELECAMERA ---
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 20)

def cleanup():
    if camera.isOpened():
        camera.release()
        print("[SYS]: Camera rilasciata correttamente.")
    cv2.destroyAllWindows()

atexit.register(cleanup)


# --- FUNZIONI DI SUPPORTO ---
def convert_joystick_data(power, angle):
    angle_rad = radians(angle)
    motordx = int(power * (sin(angle_rad) - cos(angle_rad)))
    motorsx = int(power * (sin(angle_rad) + cos(angle_rad)))
    return (max(-100, min(100, motordx)), max(-100, min(100, motorsx)))


# --- FUNZIONI PER GEMINI TOOL CALLING ---
def cattura_visione_tars():
    success, frame = camera.read()
    if success:
        cv2.imwrite("captured_frame.jpg", frame)
        return True
    return False

def richiedi_accesso_visivo():
    """Chiama questa funzione per guardare l'ambiente circostante."""
    return "FLAG_IMMAGINE_RICHIESTA"

# Avvio sessione manuale di Gemini
try:
    Geminibot.start_function_chat(
        tools=[motors_sensors.set_motors, richiedi_accesso_visivo],
        enable_automatic_function_calling=False 
    )
    print("[SYS]: Sessione Gemini avviata.")
except Exception as e:
    print(f"[ERROR]: Fallimento sessione Gemini: {e}")


# --- LOGICA CORE DI TARS (Indipendente da Flask) ---
def elabora_messaggio_gemini(msg, honesty):
    """
    Gestisce la comunicazione con l'LLM, esegue le funzioni (Tool Calling) 
    e fa parlare il robot. Ritorna la stringa di testo puro.
    """
    full_message = f"utente: {msg} \nistruzioni: sei TARS; livello onestà: {honesty}% in italiano la risposta grazie"
    print(f"[CORE]: Inviando a Gemini -> '{msg}' (Onestà: {honesty}%)")

    response = Geminibot.session.send_message(full_message)
    function_responses = []
    immagini_da_inviare = [] 

    for part in response.parts:
        if fn := part.function_call:
            print(f"[CORE]: Gemini richiede funzione -> {fn.name}")
            
            if fn.name == "richiedi_accesso_visivo":
                if cattura_visione_tars():
                    # COSTRUZIONE PROTOBUF CORRETTA
                    function_responses.append(Part(
                        function_response=FunctionResponse(
                            name=fn.name, 
                            response={"status": "ok", "dettaglio": "Immagine allegata."}
                        )
                    ))
                    immagini_da_inviare.append(Image.open("captured_frame.jpg"))
                else:
                    function_responses.append(Part(
                        function_response=FunctionResponse(
                            name=fn.name, 
                            response={"status": "errore", "dettaglio": "Camera offline"}
                        )
                    ))
            
            elif fn.name == "set_motors":
                args = type(fn).to_dict(fn).get('args', {})
                dx = args.get('dx', 0)
                sx = args.get('sx', 0)
                
                # CAMBIATO IL NOME DELLA VARIABILE (Da 'int' a 'interval_val')
                interval_val = args.get('interval', 1) 
                
                motors_sensors.set_motors(dx, sx, interval_val)
                
                function_responses.append(Part(
                    function_response=FunctionResponse(
                        name=fn.name, 
                        response={"status": "completato", "dx": dx, "sx": sx, "interval": interval_val}
                    )
                ))

    # Se ci sono state chiamate a funzioni, chiudiamo il loop rimandando i dati a Gemini
    if function_responses:
        prompt = Geminibot._normalize_prompt(function_responses + immagini_da_inviare)
        response = Geminibot.session.send_message(prompt)

    text_resp = response.text 
    
    # Text-To-Speech (eseguito dalla tua classe)
    Robotperception.text_to_speech(text=text_resp)
    
    return text_resp


# --- ENDPOINTS FLASK ---

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/move', methods=['POST'])
def move_robot():
    data = request.json
    dx, sx = convert_joystick_data(data.get('distance', 0), data.get('angle', 0))
    motors_sensors.set_motors(dx, sx)
    return jsonify({"status": "ok", "motors": [dx, sx]})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        msg = data.get('msg', ' ')
        honesty = data.get('honesty', '90')
        
        # Chiama il Core
        text_resp = elabora_messaggio_gemini(msg, honesty)
        
        return jsonify({"status": "ok", "reply": text_resp})

    except Exception as e:
        print(f"[ERROR /chat]: {e}")
        return jsonify({"status": "error", "details": str(e)}), 500

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    if 'voice' not in request.files:
        return jsonify({"status": "error", "detail": "File 'voice' mancante nella richiesta"}), 400
    
    file = request.files['voice']
    
    # 1. Recupera l'onestà dal FormData, con fallback a 90 se fallisce
    try:
        honesty_val = int(request.form.get('honesty', 90))
    except ValueError:
        honesty_val = 90
        
    try:
        # Pydub converte WebM (o altro formato dal browser) in WAV
        audio_segment = AudioSegment.from_file(file)
        
        # Salvataggio in un file temporaneo per passarlo alla tua classe
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            audio_segment.export(tmp_wav.name, format="wav")
            temp_path = tmp_wav.name
        
        # Usa il tuo STT per ottenere il testo
        testo_riconosciuto = Robotperception.speech_to_text_from_file(audio_path=temp_path)
        
        # Pulizia disco
        os.remove(temp_path)
        
        if testo_riconosciuto:
            print(f"[USER AUDIO RECOGNIZED]: {testo_riconosciuto} (Onestà ricevuta: {honesty_val}%)")
            
            # Passa il testo al Core di TARS usando l'onestà dinamica
            text_resp = elabora_messaggio_gemini(msg=testo_riconosciuto, honesty=honesty_val)
            
            return jsonify({
                "status": "success", 
                "text": testo_riconosciuto, 
                "reply": text_resp
            })
        else:
            return jsonify({"status": "error", "detail": "L'audio non conteneva parole riconoscibili."}), 400
            
    except Exception as e:
        print(f"[ERROR /upload_audio]: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500


# --- AVVIO SERVER ---
if __name__ == '__main__':
    print("[SYS]: Avvio Server Flask per TARS...")
    app.run(host='0.0.0.0', port=8000, threaded=True, use_reloader=False)