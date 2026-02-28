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
        A dictionary containing the set brightness ,the color temperature and a string just for testing.
    """
    print("funzione avviata!")
    return {
        "brightness": brightness,
        "colorTemperature": color_temp,
        "hello" : "Hello, World!"
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

chat_session = gen_model.start_chat(enable_automatic_function_calling=False)
'''
Con enable_automatic_function_calling=False, il modello restituisce un elenco di parti (parts) 
contenenti i dettagli delle funzioni da chiamare, 
anziché eseguirle automaticamente.
'''

# Send initial message
response = chat_session.send_message('light up the light warm,brightness 80')

'''
Dopo aver ricevuto la risposta,
 il tuo codice analizza ciascuna parte (response.parts) e cerca una funzione da eseguire:
'''
responses = {}
for part in response.parts:
    if fn := part.function_call:
        # Extract function arguments and call the respective tool
        args = ", ".join(f"{key}={val}" for key, val in fn.args.items())
        function_result = tools_map[fn.name](**fn.args)
        responses[fn.name] = function_result

# Build the response parts
if responses:
    response_parts = [
        genai.protos.Part(
            function_response=genai.protos.FunctionResponse(
                name=fn, 
                response={"result": val}
            )
        )
        for fn, val in responses.items()
    ]
    # Send the updated response back to the chat session
    response = chat_session.send_message(response_parts)

# Print the final response text
print(response.text)#la risposta del chatbot
print(responses) #conterrà un json con lista dei  nomi della funzione avviati e i valori di return


'''
Perché è necessario inviare due messaggi?

Questo approccio è parte del ciclo di function calling manuale. Il primo invio serve a:

    Determinare se è necessario eseguire una funzione.
    Ottenere i parametri della funzione dalla risposta.

Il secondo invio è necessario per comunicare al modello:

    Che la funzione richiesta è stata eseguita.
    Quali sono i risultati della funzione, così che il modello possa integrarli nella risposta finale.
'''