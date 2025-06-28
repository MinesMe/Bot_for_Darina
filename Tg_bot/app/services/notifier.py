import asyncio
from collections import defaultdict
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold
from aiogram.exceptions import TelegramForbiddenError

from app.database.requests import requests_notifier as db_notifier
from app.lexicon import Lexicon

async def send_reminders(bot: Bot):
    """
    Основная функция уведомителя. Собирает подписки и рассылает напоминания.
    """
    # 1. Получаем все активные подписки одним запросом
    active_subscriptions = await db_notifier.get_active_subscriptions_for_notify()

    if not active_subscriptions:
        return

    # 2. Группируем подписки по пользователям
    reminders_by_user = defaultdict(list)
    for sub in active_subscriptions:
        if sub.user and sub.event:
            reminders_by_user[sub.user].append(sub.event)

    # 3. Проходимся по каждому пользователю и отправляем ему сводку
    for user, events in reminders_by_user.items():
        lexicon = Lexicon(user.language_code)
        
        header = lexicon.get('subs_reminder_header')
        
        events_parts = []
        for i, event in enumerate(events, 1):
            # --- ИЗМЕНЕНИЕ --- Используется существующий ключ lexicon вместо "TBA"
            date_str = event.date_start.strftime('%d.%m.%Y %H:%M') if event.date_start else lexicon.get('date_not_specified')
            # --- ИЗМЕНЕНИЕ --- Используется lexicon вместо "В наличии"
            tickets_str = event.tickets_info or lexicon.get('tickets_available')
            
            # --- ИЗМЕНЕНИЕ --- Весь блок текста для события берется из лексикона
            event_text = lexicon.get('reminder_event_item').format(
                index=i,
                title=event.title,
                date=date_str,
                tickets=tickets_str
            )
            events_parts.append(event_text)
        
        full_text = header + "\n\n" + "\n\n".join(events_parts)
        
        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=full_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.1) 
        except TelegramForbiddenError:
            # Текст для логов остается без изменений, согласно вашим требованиям
            print(f"Пользователь {user.user_id} заблокировал бота. Деактивируем его подписки.")
            await db_notifier.deactivate_user_subscriptions(user.user_id)
        except Exception as e:
            # Текст для логов остается без изменений
            print(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")