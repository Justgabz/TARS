import time

from python.AI_part.robot_Perceptions import RobotPerception
from AI_part.gemini import GeminiBot
from AI_part.robot_control import robot as robot_controller
from callbacks import hotword_callback_factory


#! implementazioni da fare:
'''


'''

def main() -> None:
    try:
        import cv2
    except ImportError:
        print("cv2 is not installed; unable to show camera feed.")
        return

    perception = RobotPerception(keyword_path="Hey_tars.ppn", camera_index=0, fps=30.0)
    perception.start_capture() #avvia un nuovo thread per cattura continua di frame in background
    gemini = GeminiBot()
    robot_control = robot_controller()
    gemini.start_function_chat(tools=[robot_control.set_motors])
    #di default func calling automatico... se hai necessit� cambia

    hotword_callback = hotword_callback_factory(
        perception,
        gemini,
        camera_module=cv2, #gli stiamo passando la libreria da usare per la telecamera
    ) 
      #ho salvato una funzione con parametri impostati in una variabile;
      #chiamare hotword_callbakc equivale a chiamare l'altra funzione con i parametri impostati 

    perception.start_hotword_listener( #avvia nuovo thread per chiamare hotword
        sensitivities=[0.5],
        callback=hotword_callback,
    ) #Qui quando la hotword viene rilevata nell'altro thread, viene chiamata la funzione di callback
    try:
        while True:
            frame = perception.get_latest_frame(copy=True)
            if frame is not None:
                cv2.imshow("Robot Camera", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            if frame is None:
                time.sleep(0.01)
    finally:
        perception.stop_capture()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
