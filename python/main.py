from AI_part.gemini import GeminiBot
from AI_part.robot_control import robot

def example_usage() -> None:
    bot = GeminiBot()
    my_robot = robot()

    # tools: metodi/funzioni che il modello puo chiamare
    tools = [my_robot.set_motors]

    # inizializza una chat riusabile con function calling automatico
    chat = bot.start_function_chat(
        tools=tools,
        enable_automatic_function_calling=False,
    )

    # prompt: il modello sceglie e chiama set_motors in base a docstring/parametri
    #preferisco il func call manuale perchè posso ottenere anche i valori di ritorno della funzione
    prompt = "go forward."
    response, returns = bot.function_call_manual(
        prompt=prompt,
        chat_session=chat,
        tools=[my_robot.set_motors]
    )

    print("valori di ritorno:",returns) #dict con i return delle funzioni
    #print(response) #tutto il json della risposta
    

if __name__ == "__main__":
    example_usage()
