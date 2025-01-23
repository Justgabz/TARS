from rich.console import Console
from rich.markdown import Markdown
from prep import genai, MODEL 
#ESEMPIO DI FUNCTION CALLING MANUALE!SE METTI AUTOMATICO SI SEMPLIFICA PERCHE' LA AVVIA DA SOLA
def set_light_values(brightness: int, color_temp: str) -> dict:
    """Set the brightness and color temperature of a room light. (mock API).

    Args:
        brightness: Light level from 0 to 100. Zero is off and 100 is full brightness
        color_temp: Color temperature of the light fixture, which can be `daylight`, `cool` or `warm`.

    Returns:
        A dictionary containing the set brightness and color temperature.
    """
    print("funzione avviata!")
    return {
        "brightness": brightness,
        "colorTemperature": color_temp
    }

console = Console()

generation_config = {
    'temperature': 1,
    'max_output_tokens': 8192,
    'response_mime_type': 'text/plain',
}

# Define tools as a list and create a name-to-function mapping
tools = [set_light_values]
tools_map = {tool.__name__: tool for tool in tools}

gen_model = genai.GenerativeModel(
    model_name=MODEL,
    generation_config=generation_config,
    tools=tools  # Use the list of functions here
)

chat_session = gen_model.start_chat(enable_automatic_function_calling=True)

response = chat_session.send_message('Dim the light so the room feels warm and cozy, you choose the brightness.')
# Stampa la risposta completa
print(response.text)  # Testo integrato del modello
# Iterazione sulle parti della risposta
for part in response.parts:
    if part.function_call:
        print(f"Funzione chiamata: {part.function_call.name}")
        print(f"Parametri usati: {part.function_call.args}")
    if part.function_response:
        print(f"Risultato della funzione: {part.function_response.response}")