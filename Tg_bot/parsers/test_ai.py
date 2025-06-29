import os
from dotenv import load_dotenv
import google.generativeai as genai

# ПРЕДУПРЕЖДЕНИЕ: Этот способ небезопасен для публичного кода!
# Ваш API ключ виден всем, кто имеет доступ к этому файлу.
# AIzaSyC95EiaCgY0zwW1JTWz4Ip2xfsO8DVmh5Q" # Я закомментировал ключ для безопасности


load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')

async def getArtist(description: str) -> list: # Добавил type hint для наглядности
    
    artists = []
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash') # Используем flash, он быстрее и дешевле для таких задач
        
        prompt = f"Из этого текста вычлени только имена и фамилии людей, которые являются артистами, композиторами, дирижерами или постановщиками. Ответь списком через запятую. Если никого нет, оставь ответ пустым. Текст: {description}"
        response = await model.generate_content_async(prompt)

        # Обрабатываем ответ
        if response.text:
            for artist in response.text.split(','):
                clean_artist = artist.strip().lower()
                if clean_artist: # Добавляем, только если строка не пустая после очистки
                    artists.append(clean_artist)
        
        return artists # <--- ИЗМЕНЕНИЕ 1: Возвращаем готовый список

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return [] # В случае ошибки возвращаем пустой список

