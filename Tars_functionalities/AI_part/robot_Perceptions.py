import os
import struct
import threading
import time
import uuid
from typing import Optional, Any, Callable, List
import speech_recognition as sr



class RobotPerception:
    def __init__(
        self,
        keyword_path: Optional[str],
        camera_index: int = 0,
        fps: float = 30.0,
        *,
        access_key: Optional[str] = None,
        keyword_paths: Optional[List[str]] = None,
    ) -> None:
        self._camera_index = camera_index
        self._fps = fps

        self._frame_lock = threading.Lock()
        self._capture_thread: Optional[threading.Thread] = None
        self._capture_stop = threading.Event()
        self.latest_frame: Optional[Any] = None

        self._hotword_lock = threading.Lock()
        self._hotword_event = threading.Event() #* come funziona hotword_event?
        self._hotword_callback: Optional[Callable[[str], None]] = None #* come funziona questo attributo??
        self.last_hotword: Optional[str] = None
        self._hotword_thread: Optional[threading.Thread] = None
        self._hotword_stop = threading.Event()
        self._audio_lock = threading.Lock()

        self.access_key = access_key or os.getenv("HOTWORD_KEY")
        if keyword_paths is not None:
            self.keyword_paths = keyword_paths
        elif keyword_path is not None:
            self.keyword_paths = [keyword_path]
        else:
            self.keyword_paths = []
        self.keyword_path = self.keyword_paths
        self._activation_mp3_path = os.path.join(os.path.dirname(__file__), "activate.mp3")

    def _capture_loop(self) -> None: #il loop di cattura che verrà avviato con il multithreading
        try:
            import cv2
        except ImportError:
            print("cv2 is not installed; frame capture thread exiting.")
            return

        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            print(f"Unable to open camera index {self._camera_index}; frame capture thread exiting.")
            cap.release()
            return

        frame_interval = 1.0 / self._fps if self._fps > 0 else 0.0
        try:
            while not self._capture_stop.is_set():
                ok, frame = cap.read()
                if ok:
                    with self._frame_lock:
                        self.latest_frame = frame
                if frame_interval > 0:
                    time.sleep(frame_interval)
        finally:
            cap.release()

    def start_capture(self) -> None: #la funzione che avvia il metodo in un altro thread
        if self._capture_thread is not None and self._capture_thread.is_alive():
            return

        self._capture_stop.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="frame-capture-thread",
        )
        self._capture_thread.start()

    def stop_capture(self) -> None:
        self._capture_stop.set()

    def get_latest_frame(self, copy: bool = True) -> Optional[Any]:
        with self._frame_lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy() if copy and hasattr(self.latest_frame, "copy") else self.latest_frame
        
    ''''
    NUOVO CODICE --------------------------------
    '''

    def set_hotword_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        with self._hotword_lock:
            self._hotword_callback = callback 
        #prende come parametro una funzione,e imposta come funzione di callback quelal funzione, cioè verrà chiamata
        #alla rilevazione della hotword

    def _keyword_name_from_paths(self, keyword_paths: List[str], index: int) -> str:
        if index < 0 or index >= len(keyword_paths):
            return f"keyword_{index}"
        base = os.path.basename(keyword_paths[index])
        name, _ = os.path.splitext(base)
        return name or f"keyword_{index}" #semplicemente prende il path e torna il nome della keyword

    def _hotword_loop( #verra avviata da un altra funzione in un altro thread
        self,
        access_key: str,
        keyword_paths: List[str],
        audio_device_index: Optional[int],
        sensitivities: Optional[List[float]],
    ) -> None:
        try:
            import pvporcupine
        except ImportError:
            print("pvporcupine is not installed; hotword thread exiting.")
            return

        try:
            import pyaudio
        except ImportError:
            print("pyaudio is not installed; hotword thread exiting.")
            return

        porcupine = None
        pa = None
        stream = None

        #inizializzo porcupine e l'audio stream contiuno
        try:
            porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=keyword_paths,
                sensitivities=sensitivities,
            )
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=audio_device_index,
                frames_per_buffer=porcupine.frame_length,
            )
            stream.start_stream() #fornisce un flusso continuo di campioni di audio

            while not self._hotword_stop.is_set():
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                #leggo l'ultimo blocco di audio di dimensione x(praticamente scorre nella stream piu in avanti ad ogni ciclo)
                pcm_frame = struct.unpack_from("h" * porcupine.frame_length, pcm)#blocco di campioni audio grezzi
                keyword_index = porcupine.process(pcm_frame)

                #avente l'indice della hotword,controlliamo effettivamente quale è nell'array
                #(sarà sempre hey tars visto che è solo una per adesso)
                if keyword_index >= 0:
                    hotword = self._keyword_name_from_paths(keyword_paths, keyword_index)
                    with self._hotword_lock:
                        self.last_hotword = hotword 
                        callback = self._hotword_callback ##? 
                    self._hotword_event.set() ##? 
                    if callback is not None:
                        try:
                            callback(hotword) #chiama la funzione assegnata
                        except Exception as exc:
                            print(f"Hotword callback raised error: {exc}")
        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()
            if pa is not None:
                pa.terminate()
            if porcupine is not None:
                porcupine.delete()

    #*studiare codice da qua in poi
    def start_hotword_listener(
        self,
        access_key: Optional[str] = None,
        keyword_paths: Optional[List[str]] = None,
        audio_device_index: Optional[int] = None,
        sensitivities: Optional[List[float]] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if self._hotword_thread is not None and self._hotword_thread.is_alive():
            return

        if callback is not None:
            self.set_hotword_callback(callback) #imposta la funzione da avviare al rilevamento

        self._hotword_event.clear()
        with self._hotword_lock: #appunto perchè lo stiamo riavviando,resettiamo le variabili
            self.last_hotword = None

        self._hotword_stop.clear()
        effective_access_key = access_key if access_key is not None else self.access_key
        effective_keyword_paths = keyword_paths if keyword_paths is not None else self.keyword_paths
        if not effective_access_key:
            print("Set HOTWORD_KEY environment variable or pass access_key.")
            return
        if not effective_keyword_paths:
            print("Set keyword_paths in RobotPerception or pass keyword_paths.")
            return

        self._hotword_thread = threading.Thread(
            target=self._hotword_loop,
            daemon=True,
            name="hotword-detection-thread",
            args=(effective_access_key, effective_keyword_paths, audio_device_index, sensitivities),
        ) #mi memorizzo il thread in una variabile dell'oggetto
        self._hotword_thread.start()

    def stop_hotword_listener(self, timeout: float = 2.0) -> None:
        self._hotword_stop.set()
        if self._hotword_thread is not None:
            self._hotword_thread.join(timeout=timeout)

    def wait_for_hotword(self, timeout: Optional[float] = None) -> Optional[str]: 
        #semplicemente una funzione che aspetta l'hotword, e appena la rileva toglie lo stato di wait
        if not self._hotword_event.wait(timeout=timeout):
            return None
        self._hotword_event.clear()
        with self._hotword_lock:
            return self.last_hotword

    def _play_mp3(self, path: str) -> None:
        path = self._normalize_audio_path(path)
        if not os.path.isfile(path):
            print(f"File mp3 non trovato: {path}")
            return

        try:
            with self._audio_lock:
                if os.name == "nt":
                    self._play_mp3_mci(path)
                else:
                    try:
                        from playsound import playsound
                    except ImportError:
                        print("playsound non installato; impossibile riprodurre l'mp3.")
                        return
                    playsound(path, block=True)
        except Exception as exc:
            print(f"Errore durante la riproduzione mp3: {exc}")
    
    
    #* da studiare questo codice
    def _normalize_audio_path(self, path: str) -> str:
        normalized = os.path.abspath(path)
        if os.name == "nt":
            normalized = self._windows_short_path(normalized)
        return normalized

    #* da studiare questo codice
    def _windows_short_path(self, path: str) -> str:
        try:
            import ctypes
            from ctypes import wintypes
        except Exception:
            return path

        buffer = ctypes.create_unicode_buffer(260)
        get_short_path = ctypes.windll.kernel32.GetShortPathNameW
        get_short_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_short_path.restype = wintypes.DWORD
        result = get_short_path(path, buffer, len(buffer))
        if result == 0:
            return path
        return buffer.value
    
    #* da studiare questo codice
    def _play_mp3_mci(self, path: str) -> None:
        import ctypes

        def mci_send(command: str) -> None:
            buffer = ctypes.create_unicode_buffer(512)
            error = ctypes.windll.winmm.mciSendStringW(command, buffer, len(buffer), 0)
            if error != 0:
                err_buf = ctypes.create_unicode_buffer(512)
                ctypes.windll.winmm.mciGetErrorStringW(error, err_buf, len(err_buf))
                raise RuntimeError(err_buf.value or f"MCI error {error}")

        alias = f"mp3_{uuid.uuid4().hex}"
        mci_send(f'open "{path}" type mpegvideo alias {alias}')
        try:
            mci_send(f"play {alias} wait")
        finally:
            try:
                mci_send(f"close {alias}")
            except Exception:
                pass

    #! ATTENZIONE! SU LINUX CAMBIA QUESTO CODICE!!!IMPLEMENTARE
    def record_audio_sample_windows(self, hotword: Optional[str] = None) -> None:
        r = sr.Recognizer()
        r.dynamic_energy_threshold = True
        
        #! il problema è questa funzione
        self._play_mp3(self._activation_mp3_path)
        with sr.Microphone() as source:
            print("In attesa di audio... (inizia a parlare)")
            audio = r.listen(source)
            print("Silenzio rilevato, registrazione interrotta.")

        with open("registrazione.wav", "wb") as f:
            f.write(audio.get_wav_data())
        self._play_mp3(self._activation_mp3_path)

        return audio.get_wav_data()

    def speech_to_text_from_file(
        self,
        audio_path: str = "registrazione.wav",
        language: str = "it-IT",
    ) -> Optional[str]:
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
        except FileNotFoundError:
            print(f"File audio non trovato: {audio_path}")
            return None
        except Exception as exc:
            print(f"Errore apertura audio: {exc}")
            return None

        try:
            return recognizer.recognize_google(audio, language=language)
        except sr.UnknownValueError:
            print("STT: audio non riconosciuto.")
            return None
        except sr.RequestError as exc:
            print(f"STT: errore servizio di riconoscimento ({exc}).")
            return None


    def text_to_speech(
        self,
        text: str,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
        voice_id: Optional[str] = None,
    ) -> None:
        try:
            import pyttsx3
        except ImportError:
            print("pyttsx3 non installato; impossibile fare TTS.")
            return

        engine = pyttsx3.init()
        if voice_id is None: #se è None, di default metti la voce maschile
            voice_id = self._select_male_voice(engine)
        if voice_id is not None:
            engine.setProperty("voice", voice_id)
        engine.setProperty("rate", rate if rate is not None else 130)
        if volume is not None:
            engine.setProperty("volume", volume)
        engine.say(text)
        engine.runAndWait()

    def _select_male_voice(self, engine: Any) -> Optional[str]:
        try:
            voices = engine.getProperty("voices")
        except Exception:
            return None

        def looks_male(v: Any) -> bool:
            hay = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
            return any(k in hay for k in ("male", "masch", "man", "uomo", "deep", "baritone"))

        for v in voices:
            if looks_male(v):
                return getattr(v, "id", None)

        for v in voices:
            langs = getattr(v, "languages", None) or []
            lang_str = " ".join([str(l).lower() for l in langs])
            if "it" in lang_str or "ital" in lang_str:
                return getattr(v, "id", None)

        return getattr(voices[0], "id", None) if voices else None
        
    #---------------------------Audio listener ( dentro la classe)---------------------------------#
    ''''
    NUOVO CODICE --------------------------------
    '''

#main
def example_hotword_capture_usage() -> None:
    import cv2
    # Example: hotword listener in background thread with callback (without robot.wait_for_hotword).
    robot = RobotPerception(keyword_path="..//Hey_tars.ppn")

    def on_hotword(hotword: str) -> None:
        print(f"Hotword detected: {hotword}")

    robot.start_hotword_listener(
        sensitivities=[0.5],
        callback=robot.record_audio_sample,
    ) #Qui quando la hotword viene rilevata nell'altro thread, viene chiamata la funzione di callback

    robot.start_capture()

    try:
        print("Listening for hotword in background... Press Ctrl+C to stop.")
        while True:
            # Do other work here without blocking on wait_for_hotword.
            if robot.latest_frame is not None:
                cv2.imshow("foto-->",robot.latest_frame)
                cv2.waitKey(1)
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        robot.stop_hotword_listener() #appena sei uscito dal try(o except),vai sul finally e
        robot.stop_capture()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    pass
    #example_hotword_capture_usage()
