import asyncio
import json
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold, hitalic
from aiogram.exceptions import TelegramForbiddenError

from app.database.models import listener_engine
from app.database.requests import requests_favorite_notifier as db_notifier
from app.keyboards.keyboards_notifier import get_add_to_subscriptions_keyboard
from app.lexicon import Lexicon
# Правильный импорт вашей функции
from app.services.recommendation import get_recommended_artists

async def favorite_notification_handler(bot: Bot, connection, pid, channel, payload):
    """
    Обрабатывает уведомление, получает ВАШ список рекомендованных артистов
    и отправляет его пользователю.
    """
    print(f"\n⭐️ Получено уведомление о НОВОМ ИЗБРАННОМ из канала '{channel}' (PID: {pid})")
    
    try:
        data = json.loads(payload)
        user_id = data.get('user_id')
        artist_name = data.get('artist_name')

        if not user_id or not artist_name:
            print("[ОШИБКА] В payload отсутствуют user_id или artist_name.")
            return

        # 1. ПОЛУЧАЕМ ВАШ ГОТОВЫЙ СПИСОК АРТИСТОВ
        # Исправлено: используем импортированную функцию напрямую
        artists = await get_recommended_artists(artist_name)
        
        # 2. ФОРМИРУЕМ ТЕКСТ СООБЩЕНИЯ
        text = (
            f"Мы заметили, что вы добавили в избранное {hbold(artist_name)}! ✨\n\n"
            f"Возможно, вам также понравятся эти исполнители:\n"
        )
        
        # 3. ПРЕВРАЩАЕМ ВАШ СПИСОК В КРАСИВЫЙ ВИД
        recommendations_list = "\n".join([f"• {hitalic(rec_artist)}" for rec_artist in artists])
        text += recommendations_list

        # 4. ОТПРАВЛЯЕМ СООБЩЕНИЕ
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            print(f"--> Отправлено уведомление с рекомендациями пользователю {user_id}")
        except TelegramForbiddenError:
            print(f"Пользователь {user_id} заблокировал бота.")
        except Exception as e:
            print(f"Не удалось отправить рекомендации пользователю {user_id}: {e}")

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] в favorite_notification_handler: {e}")

async def notification_handler(bot: Bot, connection, pid, channel, payload):
    """Обрабатывает уведомление о новом событии из БД."""
    print(f"\n--- Получено новое событие от PID {pid} по каналу {channel} ---")
    data = json.loads(payload)
    
    artist_info = data.get('artist', {})
    artist_id = artist_info.get('artist_id')
    artist_name = artist_info.get('name', 'Неизвестный артист')
    
    event_id = data.get('event_id')
    event_title = data.get('title', 'Новое событие')
    
    venue_info = data.get('venue', {})
    event_city_name = venue_info.get('city_name', '')
    event_country_name = data.get('country', {}).get('name', '')
    
    if not artist_id or not event_id:
        print("Ошибка в payload: отсутствует artist_id или event_id.")
        return

    subscribers = await db_notifier.get_favorite_subscribers_by_artist(artist_id)
    print(f"Найдено подписчиков на '{artist_name}' (ID: {artist_id}): {len(subscribers)} чел.")

    for fav_entry in subscribers:
        user = fav_entry.user
        user_regions = fav_entry.regions
        
        is_priority_region = False
        if user_regions and (event_country_name in user_regions or event_city_name in user_regions):
            is_priority_region = True
            
        lexicon = Lexicon(user.language_code)
        emoji = "🔥" if is_priority_region else "🔔"
        
        text = (
            f"{emoji} У вашего избранного артиста {hbold(artist_name)} появилось новое событие!\n\n"
            f"🎵 {hbold(event_title)}\n"
            f"📍 {event_city_name}, {event_country_name}"
        )
        
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
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
        
        await asyncio.sleep(0.1)


# --- ИСПРАВЛЕННАЯ ВЕРСИЯ ---
async def listen_for_db_notifications(bot: Bot):
    """Слушает каналы в БД и запускает правильные обработчики уведомлений."""
    print("📡 Запуск основного слушателя уведомлений из БД...")
    try:
        async with listener_engine.connect() as conn:
            raw_connection = await conn.get_raw_connection()
            asyncpg_conn = raw_connection.driver_connection
            
            # 1. Создаем обработчик для КАНАЛА СОБЫТИЙ (указывает на notification_handler)
            event_handler_with_bot = lambda c, p, ch, pl: asyncio.create_task(notification_handler(bot, c, p, ch, pl))
            await asyncpg_conn.add_listener("new_event_channel", event_handler_with_bot)
            print("✅ Подписка на канал 'new_event_channel' выполнена.")
            
            # 2. Создаем обработчик для КАНАЛА ИЗБРАННОГО (указывает на favorite_notification_handler)
            favorite_handler_with_bot = lambda c, p, ch, pl: asyncio.create_task(favorite_notification_handler(bot, c, p, ch, pl))
            await asyncpg_conn.add_listener("user_favorite_added_channel", favorite_handler_with_bot)
            print("✅ Подписка на канал 'user_favorite_added_channel' выполнена.")
            
            print("\nСлушатель готов к работе. Ожидание уведомлений...")
            while True:
                await asyncio.sleep(3600)

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] В слушателе БД: {e}. Перезапуск может быть необходим.")