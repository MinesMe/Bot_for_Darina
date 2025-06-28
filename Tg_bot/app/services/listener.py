import asyncio
import json
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold, hitalic
from aiogram.exceptions import TelegramForbiddenError

from app.database.models import listener_engine
from app.database.requests import requests_favorite_notifier as db_notifier
from app.database.requests.requests import get_user_lang
from app.keyboards.keyboards_notifier import get_add_to_subscriptions_keyboard
from app.lexicon import Lexicon
# Правильный импорт вашей функции
from app.services.recommendation import get_recommended_artists
from app.handlers.subscriptions import RecommendationFlow # Импортируем наш новый FSM
from aiogram.fsm.storage.redis import RedisStorage # Или ваш FSM Storage
from app.keyboards import keyboards as kb

async def favorite_notification_handler(bot: Bot, storage: RedisStorage, connection, pid, channel, payload):
    """
    Обрабатывает уведомление, получает ВАШ список рекомендованных артистов
    и отправляет его пользователю в виде интерактивной клавиатуры.
    """
    print(f"\n⭐️ Получено уведомление о НОВОМ ИЗБРАННОМ из канала '{channel}' (PID: {pid})")
    
    try:
        data = json.loads(payload)
        user_id = data.get('user_id')
        artist_name = data.get('artist_name')

        if not user_id or not artist_name:
            print("[ОШИБКА] В payload отсутствуют user_id или artist_name.")
            return

        # 1. Получаем список ОБЪЕКТОВ Artist, которые есть в нашей БД (или только что созданы)
        recommended_artists = await get_recommended_artists(artist_name)

        # Если Gemini ничего не вернул или ни один из артистов не прошел валидацию/создание
        if not recommended_artists:
            print(f"--> Рекомендации для '{artist_name}' не найдены или не прошли валидацию. Уведомление не отправлено.")
            return

        user_lang = await get_user_lang(user_id)
        lexicon = Lexicon(user_lang)
        
        # 2. Формируем текст сообщения
        text_header = lexicon.get('recommendations_after_add_favorite').format(artist_name=hbold(artist_name.title()))
        
        # 3. Создаем нашу новую интерактивную клавиатуру
        # Изначально ничего не выбрано, поэтому selected_artist_ids - пустой set
        keyboard = kb.get_recommended_artists_keyboard(recommended_artists, lexicon, set())

        # 4. ОТПРАВЛЯЕМ СООБЩЕНИЕ с клавиатурой
        try:
            sent_message = await bot.send_message(
                chat_id=user_id,
                text=text_header,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
            print(f"--> Отправлено уведомление с рекомендациями пользователю {user_id}")

            # 5. ЗАПИСЫВАЕМ ДАННЫЕ В FSM для этого пользователя
            # Это ключевой шаг для связи уведомителя с хэндлерами
            state_data = {
                'recommended_artists': [artist.to_dict() for artist in recommended_artists], # Сериализуем объекты для хранения
                'selected_artist_ids': set(), # Изначально выбор пуст
                'message_id_to_edit': sent_message.message_id # Сохраняем ID сообщения для редактирования
            }
            # Устанавливаем состояние и сохраняем данные
            await storage.set_state(key=f"fsm:{user_id}:{user_id}", state=RecommendationFlow.selecting_artists)
            await storage.set_data(key=f"fsm:{user_id}:{user_id}", data=state_data)
            print(f"--> Установлено состояние 'selecting_artists' для пользователя {user_id}")


        except TelegramForbiddenError:
            print(f"Пользователь {user_id} заблокировал бота.")
        except Exception as e:
            print(f"Не удалось отправить рекомендации пользователю {user_id}: {e}")

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] в favorite_notification_handler: {e}", exc_info=True)

async def notification_handler(bot: Bot, connection, pid, channel, payload):
    """Обрабатывает уведомление о новом событии из БД."""
    print(f"\n--- Получено новое событие от PID {pid} по каналу {channel} ---")
    data = json.loads(payload)
    
    artist_info = data.get('artist', {})
    artist_id = artist_info.get('artist_id')
    # --- ИЗМЕНЕНИЕ --- Получаем имя без значения по умолчанию
    artist_name_payload = artist_info.get('name') 
    
    event_id = data.get('event_id')
    # --- ИЗМЕНЕНИЕ --- Получаем заголовок без значения по умолчанию
    event_title_payload = data.get('title')
    
    venue_info = data.get('venue', {})
    event_city_name = venue_info.get('city_name', '')
    event_country_name = data.get('country', {}).get('name', '')
    
    if not artist_id or not event_id:
        print("Ошибка в payload: отсутствует artist_id или event_id.")
        return

    subscribers = await db_notifier.get_favorite_subscribers_by_artist(artist_id)
    print(f"Найдено подписчиков на '{artist_name_payload or 'ID:'+str(artist_id)}': {len(subscribers)} чел.")

    for fav_entry in subscribers:
        user = fav_entry.user
        user_regions = fav_entry.regions
        
        is_priority_region = False
        if user_regions and (event_country_name in user_regions or event_city_name in user_regions):
            is_priority_region = True
        
        # --- ИЗМЕНЕНИЕ --- Создаем лексикон для КОНКРЕТНОГО пользователя
        lexicon = Lexicon(user.language_code)
        emoji = "🔥" if is_priority_region else "🔔"
        
        # --- ИЗМЕНЕНИЕ --- Используем лексикон для значений по умолчанию
        final_artist_name = artist_name_payload or lexicon.get('unknown_artist')
        final_event_title = event_title_payload or lexicon.get('new_event_title')

        # --- ИЗМЕНЕНИЕ --- Текст сообщения полностью формируется из лексикона
        text = lexicon.get('new_event_for_favorite_notification').format(
            emoji=emoji,
            artist_name=hbold(final_artist_name),
            event_title=hbold(final_event_title),
            event_city=event_city_name,
            event_country=event_country_name
        )

        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=text,
                reply_markup=get_add_to_subscriptions_keyboard(event_id, lexicon),
                parse_mode=ParseMode.HTML
            )
            print(f"--> Отправлено уведомление пользователю {user.user_id}")
        except TelegramForbiddenError:
            print(f"Пользователь {user.user_id} заблокировал бота.")
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")
        
        await asyncio.sleep(0.1)


# --- ИСПРАВЛЕННАЯ ВЕРСИЯ ---
async def listen_for_db_notifications(bot: Bot, storage: RedisStorage):
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
            favorite_handler_with_bot = lambda c, p, ch, pl: asyncio.create_task(favorite_notification_handler(bot, storage, c, p, ch, pl))
            await asyncpg_conn.add_listener("user_favorite_added_channel", favorite_handler_with_bot)
            print("✅ Подписка на канал 'user_favorite_added_channel' выполнена.")
            
            print("\nСлушатель готов к работе. Ожидание уведомлений...")
            while True:
                await asyncio.sleep(3600)

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА] В слушателе БД: {e}. Перезапуск может быть необходим.")