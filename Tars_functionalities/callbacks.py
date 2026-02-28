import os
from typing import Optional

from python.AI_part.robot_Perceptions import RobotPerception
from AI_part.gemini import GeminiBot


def hotword_callback_factory(
    perception: RobotPerception,
    gemini: GeminiBot,
    *,     
      #dopo l'asterisco, i parametri devono essere passati tipo nome="gabriele",(func(nome="gabriele"))
      # i parametri prima invece basta che metti il valore (es: func("gabriele"))
    camera_module,
) -> callable:
    """Create the hotword callback with injected dependencies."""

    def hotword_callback(hotword: Optional[str] = None):
        perception.record_audio_sample_windows()
        user_text = perception.speech_to_text_from_file("registrazione.wav")

        prompt: dict[str, str] = {}
        if user_text:
            prompt["text"] = user_text

        frame = perception.get_latest_frame(copy=True)
        if frame is not None:
            image_path = os.path.join(os.path.dirname(__file__), "last_frame.jpg")
            if camera_module.imwrite(image_path, frame):
                prompt["image"] = image_path
            else:
                print("impossibile inoltrare l'immagine a gemini")

        response = gemini.send_function_chat_message(prompt)
        text = response.candidates[0].content.parts[0].text
        print(text)
        perception.text_to_speech(text)

    return hotword_callback
