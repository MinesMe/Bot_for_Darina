# app/listener.py

import asyncio
import json
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramForbiddenError

from app.database.models import listener_engine
# ИЗМЕНЕНИЕ: Импортируем запросы из нового файла
from app.database import requests_favorite_notifier as db_notifier
# ИЗМЕНЕНИЕ: Импортируем клавиатуры из нового файла
from app.database.keyboards_notifier import get_add_to_subscriptions_keyboard
from app.lexicon import Lexicon

async def listen_for_db_notifications(bot: Bot):
    """Слушает канал в БД и запускает обработчик уведомлений."""
    print("📡 Слушатель уведомлений для 'Избранного' запущен.")
    try:
        async with listener_engine.connect() as conn:
            raw_connection = await conn.get_raw_connection()
            asyncpg_conn = raw_connection.driver_connection
            
            # Мы передаем объект bot в обработчик через partial
            handler_with_bot = lambda c, p, ch, pl: asyncio.create_task(notification_handler(bot, c, p, ch, pl))
            
            await asyncpg_conn.add_listener("new_event_channel", handler_with_bot)
            
            print("✅ Подписка на 'new_event_channel' выполнена.")
            while True:
                await asyncio.sleep(3600) # Просто держим соединение живым
    except Exception as e:
        print(f"[ОШИБКА] В слушателе БД: {e}")


async def notification_handler(bot: Bot, connection, pid, channel, payload):
    """Обрабатывает уведомление о новом событии из БД."""
    print(f"\n--- Получено новое событие от PID {pid} по каналу {channel} ---")
    data = json.loads(payload)
    
    # 1. Извлекаем ключевые данные из payload
    artist_info = data.get('artist', {})
    artist_id = artist_info.get('artist_id')
    artist_name = artist_info.get('name', 'Неизвестный артист')
    
    event_id = data.get('event_id')
    event_title = data.get('title', 'Новое событие')
    
    venue_info = data.get('venue', {})
    event_city_name = venue_info.get('city_name', '') # Предполагаем, что триггер вернет и это
    event_country_name = data.get('country', {}).get('name', '')
    
    if not artist_id or not event_id:
        print("Ошибка в payload: отсутствует artist_id или event_id.")
        return

    # 2. Находим всех, кто добавил этого артиста в "Избранное"
    subscribers = await db_notifier.get_favorite_subscribers_by_artist(artist_id)
    print(f"Найдено подписчиков на '{artist_name}' (ID: {artist_id}): {len(subscribers)} чел.")

    # 3. Проходимся по каждому подписчику и отправляем уведомление
    for fav_entry in subscribers:
        user = fav_entry.user
        user_regions = fav_entry.regions # Персональные регионы для этого избранного
        
        # 4. Проверяем регионы
        is_priority_region = False
        if user_regions and (event_country_name in user_regions or event_city_name in user_regions):
            is_priority_region = True
            
        # 5. Формируем сообщение
        lexicon = Lexicon(user.language_code)
        emoji = "🔥" if is_priority_region else "🔔"
        
        text = (
            f"{emoji} У вашего избранного артиста {hbold(artist_name)} появилось новое событие!\n\n"
            f"🎵 {hbold(event_title)}\n"
            f"📍 {event_city_name}, {event_country_name}"
        )
        
        # 6. Отправляем
        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=text,
                reply_markup=get_add_to_subscriptions_keyboard(event_id),
                parse_mode=ParseMode.HTML
            )
            print(f"--> Отправлено уведомление пользователю {user.user_id}")
        except TelegramForbiddenError:
            print(f"Пользователь {user.user_id} заблокировал бота.")
            # Здесь можно будет добавить логику деактивации
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
        
        await asyncio.sleep(0.1) # Пауза между отправками