from PIL import Image
from prep import MODEL, genai

gen_model = genai.GenerativeModel(MODEL)

img = Image.open('python\\GenAi\\tarsss.jpg')

response = gen_model.generate_content(
    [
        'What do you see in the photo?',
        img
    ]

)

print(response.text)

audio_file = genai.upload_file('python\\GenAi\\fully_functioning.wav')

response = gen_model.generate_content(
    [
        audio_file,
        'What do you hear?'
        
    ]

)

print(response.text)