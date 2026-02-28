from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Tuple

from AI_part.prep import MODEL, genai

try:
    from PIL import Image
except Exception:
    Image = None


class GeminiBot:
    def __init__(self, model_name: Optional[str] = None) -> None:
        if not (model_name or MODEL):
            raise ValueError("MODEL is not set. Check your .env for MODEL_GEMINI_2_FLASH.")
        self.model_name = model_name or MODEL
        self.gen_model = genai.GenerativeModel(model_name=self.model_name)
        self.session = None #sessione di chat per func calling

        #watch normalize prompt for understanding the allowed types of input

    
    #riconfigura il modello per il function calling:
    #generations_config: {temperature : 100,max_token : 30}
    #tools : lista delle funzioni usate nel function calling
    def configure( 
        self,
        generation_config: Optional[Dict[str, Any]] = None,
        tools: Optional[Sequence[Callable[..., Any]]] = None,
    ) -> None:
        #qui avviene la parte della riconfigurazione
        self.gen_model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
            tools=tools,
        )
    

    def start_chat(self, enable_automatic_function_calling: bool = True) -> Any:
        return self.gen_model.start_chat(
            enable_automatic_function_calling=enable_automatic_function_calling
        )#apre una sessione dove appunto si specifica se attivare il function calling automatico

    def _ensure_image(self, img: Any) -> Any:
        if Image is None: #se PILLOW non è installato, ritorna l'immagine cosi come è non cambiata
            return img
        if isinstance(img, str): #se l'immagine è una stringa,allora usa PILLOW per aprire il path e scaricare la foto
            return Image.open(img)
        return img #se l'immagine non è una stringa;si assume che sia gia nel formato giusto

    def _normalize_parts(self, parts: Iterable[Any]) -> Sequence[Any]: 
        #questa funzione prende la lista delle parti del prompt : [text,audio,image] e rimuove quelle che sono None
        return [p for p in parts if p is not None]
    

    def _normalize_prompt(self, prompt: Any) -> Any: 
        #questo metodo e usato per inserire immagine,testo e audio 
        # Supporta prompt come stringa, dict o lista di parti (text, image, audio)
        #
        # Esempi di utilizzo:
        # prompt = 'Descrivi questa immagine'
        #
        # prompt = {
        #     'text': 'Descrivi questa immagine',
        #     'image': 'C:/path/to/img.jpg',
        # }
        #
        # prompt = [
        #     ('text', 'Confronta queste due immagini'),
        #     ('image', 'C:/path/to/img1.jpg'),
        #     ('image', 'C:/path/to/img2.jpg'),
        # ]
        #
        # prompt = [
        #     {'text': 'Trascrivi questo audio'},
        #     {'audio': 'C:/path/to/audio.wav'},
        # ]
        if isinstance(prompt, str):
            return prompt
        parts: list[Any] = []
        if isinstance(prompt, dict):
            if 'text' in prompt:
                parts.append(prompt['text'])
            if 'image' in prompt:
                parts.append(self._ensure_image(prompt['image']))
            if 'audio' in prompt:
                parts.append(genai.upload_file(prompt['audio']))
            return self._normalize_parts(parts)
        for part in prompt:
            if part is None:
                continue
            if isinstance(part, tuple) and len(part) == 2:
                kind, value = part
                if kind == 'text':
                    parts.append(value)
                    continue
                if kind == 'image':
                    parts.append(self._ensure_image(value))
                    continue
                if kind == 'audio':
                    parts.append(genai.upload_file(value))
                    continue
            if isinstance(part, dict):
                if 'text' in part:
                    parts.append(part['text'])
                    continue
                if 'image' in part:
                    parts.append(self._ensure_image(part['image']))
                    continue
                if 'audio' in part:
                    parts.append(genai.upload_file(part['audio']))
                    continue
            parts.append(part)
        return self._normalize_parts(parts)


    #uso semplice senza function calling
    def generate_content(self, prompt: Any) -> Any:
        return self.gen_model.generate_content(self._normalize_prompt(prompt))
    

    
    
    '''. . . FUNC CALL AUTO . . .
       fai un solo send_message(prompt)
       l SDK decide se chiamare la funzione, la esegue e reinvia il risultato al modello in automatico.
       Tu ricevi direttamente la risposta finale.'''
    #inizializza una chat riusabile per function calling (config + start_chat)
    def start_function_chat(
        self,
        tools: Sequence[Callable[..., Any]],
        generation_config: Optional[Dict[str, Any]] = None,
        enable_automatic_function_calling: bool = True,
    ) -> Any: #restituisce un oggetto di sessione chat
        self.configure(generation_config=generation_config, tools=tools)
        self.session = self.start_chat(
            enable_automatic_function_calling=enable_automatic_function_calling)
        return self.session

    #funzione che si occupa di mandare il messaggio in una sessione di func calling 
    def send_function_chat_message(
        self,
        message: Any,
        chat_session: Optional[Any] = None,
    ) -> Any:
        session = chat_session or self.session
        if session is None:
            raise ValueError("Chat session not started. Call start_function_chat() first.")
        return session.send_message(self._normalize_prompt(message))
    
     #esempio session = self.start_chat ; session.send(bla bla bla)
    
    #IN ENTRAMBE LE FUNZIONI, O PUOI PASSARE COME PARAMETRO LA SESSIONE DI CHAT, ALTRIMENTI
    #INVII UN SOLO MESSAGGIO CREANDO UNA NUOVA SESSIONE CHE NON PUOI RIUTILIZZARE
    # (utile se ti serve mandare solo un messaggio senza intrometterti nell'altra sessione)
    def function_call_auto(
        self,
        prompt: Any,
        tools: Optional[Sequence[Callable[..., Any]]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        chat_session: Optional[Any] = None,
    ) -> Any:
        if chat_session is None:
            if tools is None:
                raise ValueError("tools is required when chat_session is not provided.")
            self.configure(generation_config=generation_config, tools=tools)
            chat_session = self.start_chat(enable_automatic_function_calling=True)

        else: #se abbiamo passato la sessione come parametro
            return chat_session.send_message(self._normalize_prompt(prompt))

    
    def function_call_manual(
        self,
        prompt: Any,
        tools: Optional[Sequence[Callable[..., Any]]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        chat_session: Optional[Any] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        if tools is None:
            raise ValueError("tools is required for manual function calling.")
        if chat_session is None:
            self.configure(generation_config=generation_config, tools=tools)
            chat_session = self.start_chat(enable_automatic_function_calling=False)
        tools_map = {tool.__name__: tool for tool in tools}

        response = chat_session.send_message(self._normalize_prompt(prompt))
        responses: Dict[str, Any] = {}
        for part in response.parts:
            if fn := part.function_call:
                function_result = tools_map[fn.name](**fn.args)
                responses[fn.name] = function_result

        if responses:
            response_parts = [
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=fn,
                        response={"result": val},
                    )
                )
                for fn, val in responses.items()
            ]
            response = chat_session.send_message(response_parts)

        return response, responses
    


geminibot = GeminiBot
