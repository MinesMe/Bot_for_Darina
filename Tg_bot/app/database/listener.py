import asyncio
from functools import partial
import json

from aiogram import Bot
from app.database.models import listener_engine
import app.database.requests as rq

async def listen_for_db_notifications(bot:Bot):
    print("📡 Функция listen_for_db_notifications() была вызвана.")
    try:
        async with listener_engine.connect() as conn:  # это AsyncConnection
            # Получаем "сырое" соединение из SQLAlchemy
            raw_connection = await conn.get_raw_connection()

            # Получаем настоящее asyncpg соединение
            asyncpg_conn = raw_connection.driver_connection

            # Подписываемся на канал
            partial_notification_handler = partial(notification_handler, bot)
            await asyncpg_conn.add_listener("new_event_channel", partial_notification_handler)

            

            print("✅ Подписка на канал 'new_event_channel' выполнена. Слушаю уведомления...")

            while True:
                await asyncio.sleep(1)  # Нужно, чтобы задача не завершалась
    except Exception as e:
        print(f"[ОШИБКА] В слушателе БД: {e}")


async def notification_handler(bot: Bot, connection, pid, channel, payload):
    print("\n--- Новые данные поступили в БД! ---")
    event_data = json.loads(payload)
    event_title = event_data.get('title') 
    event_description = event_data.get('description', 'Нет описания')
    # Так как event_type - это вложенный JSON, получаем его название безопасно
    event_type_name = event_data.get('event_type', {}).get('name', 'Не указан') 

    users_id = await rq.get_subscribers_for_event_title(event_title)
    for user_id in users_id:
        await bot.send_message(chat_id=user_id, text=f"""Появилось новое мероприятие:
-Название: {event_title}
-время: {event_description}
-тип: {event_type_name}""")

    
    return payload
   
    # print(f"Канал: {channel}")
    # print(f"PID отправителя: {pid}")
    # print(f"Сообщение: {payload}")
    # print("---------------------------")
