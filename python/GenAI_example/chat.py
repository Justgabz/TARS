from PIL import Image
from rich.console import Console
from rich.markdown import Markdown
from prep import genai, MODEL 

#PER INCLUDERE I MEDIA FUNZIONA ALLO STESSO MODO COME VISTO SU GenAI_Images_and_Audios
console = Console()

generation_config = {
    'temperature' : 1,
    'max_output_tokens' : 8192,
    'response_mime_type' : 'text/plain',
}

gen_model = genai.GenerativeModel(
    model_name=MODEL,
    generation_config=generation_config,
    system_instruction='Reply in one sentence'
)

#chat_session = gen_model.start_chat(history=[])
chat_session = gen_model.start_chat()

response = chat_session.send_message('What is the capital of US')
console.print(Markdown(response.text))

response = chat_session.send_message('What is the capital of Italy?')
console.print(Markdown(response.text))

print('Chat history : ')
console.print(chat_session.history)

chat_session.rewind() #cancella la history