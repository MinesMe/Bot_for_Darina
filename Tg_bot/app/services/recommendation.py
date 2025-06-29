from datetime import datetime, timedelta
import logging
import google.generativeai as genai
import os
from dotenv import load_dotenv
from app.database.requests import requests as db # Импортируем наш модуль с запросами

from .query import get_concert_recommendations_query, get_local_event_recommendations_query
from app.database.models import async_session # Импортируем async_session из models.py

load_dotenv()

async def get_recommended_artists(artist_name: str):
    """
    Получает имена рекомендованных артистов от Gemini,
    находит их в БД или СОЗДАЕТ, если их нет.

    Возвращает:
        list[Artist]: Список объектов Artist (существующих и/или только что созданных).
    """
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY не установлен.")
    genai.configure(api_key=gemini_api_key)

    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = (
        f"Назови 3 артиста, похожих на {artist_name}. "
        f"Ответь только именами артистов, разделенными запятыми, без дополнительных символов и нумерации. Всего 3 артиста."
    )

    try:
        response = await model.generate_content_async(prompt)
        raw_artists = response.text.strip()
        recommended_names_lower = [artist.strip().lower() for artist in raw_artists.split(',') if artist.strip()]

        if not recommended_names_lower:
            logging.warning(f"Предупреждение: Gemini не вернул рекомендации для '{artist_name}'.")
            return []

        # Вызываем нашу функцию, она возвращает список ОБЪЕКТОВ
        verified_artists_objects = await db.get_or_create_artists_by_name(recommended_names_lower)
        
        logging.info(f"Успешно обработаны рекомендации для '{artist_name}'.")
        # --- ИСПРАВЛЕНИЕ: Возвращаем список объектов, а не словарей ---
        return verified_artists_objects

    except Exception as e:
        logging.error(f"Произошла ошибка при запросе к Gemini API или работе с БД: {e}", exc_info=True)
        return []

def get_concert_recommendations(country_name: str, target_date_str: str):
    """
    Извлекает информацию о мероприятиях (артист, страна, город, дата)
    в указанной стране и в заданном диапазоне дат с использованием SQLAlchemy.

    Args:
        country_name (str): Название страны (например, 'Чехия').
        target_date_str (str): Целевая дата в формате 'YYYY-MM-DD' (например, '2025-08-23').

    Returns:
        list: Список словарей, каждый из которых содержит информацию о мероприятии
              (artist_name, country_name, city_name, event_date).
              Возвращает пустой список, если мероприятий не найдено.
    """
    db = None
    try:
        # Преобразование строки даты в объект datetime
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')

        # Получаем сессию базы данных
        db = async_session()
        results = get_concert_recommendations_query(db, country_name, target_date)
        return results

    except ValueError as e:
        print(f"Ошибка формата даты: {e}. Убедитесь, что дата в формате YYYY-MM-DD.")
        return []
    except Exception as e:
        print(f"Произошла ошибка при получении рекомендаций по концертам: {e}")
        return []
    finally:
        if db:
            db.close() # Важно закрывать сессию

def get_local_event_recommendations(home_country_name: str):
    """
    Извлекает информацию о предстоящих мероприятиях (артист, страна, город, дата)
    в указанной стране проживания пользователя, в течение 10 дней от текущей даты,
    с использованием SQLAlchemy.

    Args:
        home_country_name (str): Название страны проживания пользователя (например, 'Германия').

    Returns:
        list: Список словарей, каждый из которых содержит информацию о мероприятии
              (artist_name, country_name, city_name, event_date).
              Возвращает пустой список, если мероприятий не найдено.
    """
    db = None
    try:
        # Получаем сессию базы данных
        db = async_session()
        results = get_local_event_recommendations_query(db, home_country_name)
        return results

    except Exception as e:
        print(f"Произошла ошибка при получении предстоящих мероприятий: {e}")
        return []
    finally:
        if db:
            db.close() # Важно закрывать сессию

if __name__ == "__main__":

    input_artist = ... # Артист
    
    if input_artist:
        recommended_artists = get_recommended_artists(input_artist)
        if recommended_artists:
            print("\n--- Рекомендованные артисты ---")
            for artist in recommended_artists:
                print(f"Артист: {artist}")
            print("---------------------------------------------------------")
        else:
            print("Не удалось получить рекомендации артистов.")

    country_concert = ... # Страна
    date_concert = ... # Дата концерта (ГГГГ-ММ-ДД)
    
    if date_concert and country_concert:
        concert_recommendations = get_concert_recommendations(country_concert, date_concert)
        if concert_recommendations:
            print("\n--- Рекомендованные выступления в поездке для дальнейшей интеграции ---")
            for event in concert_recommendations:
                print(f"- Артист: {event.get('artist')}, Страна: {event['country_name']}, "
                f"Город: {event['city_name']}, Дата: {event['event_date']}")
            print("-----------------------------------------------------------------------")
        else:   
            print(f"Мероприятия в {country_concert} (дата +- 4 дня от {date_concert}) не найдены.")
        print("\n" + "="*30 + "\n")
    else:
        print("Недостаточно данных для получения рекомендаций по выступлениям.")

    country_residence = ... # Страна проживания

    if country_residence:
        local_event_recommendations = get_local_event_recommendations(country_residence)
        if local_event_recommendations:
            print("\n--- Рекомендованные местные мероприятия ---")
            for event in local_event_recommendations:
                print(f"- Артист: {event.get('artist')}, Страна: {event['country_name']}, "
            f"Город: {event['city_name']}, Дата: {event['event_date']}")
            print("---------------------------------------------------------------------")
        else:
            print("Не удалось получить рекомендации по местным мероприятиям.")
        print("\n" + "="*30 + "\n")
    else:
        print("Недостаточно данных для получения рекомендаций по местным мероприятиям.")