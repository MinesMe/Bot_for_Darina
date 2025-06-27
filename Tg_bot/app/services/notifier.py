# app/services/notifier.py

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
    # defaultdict(list) создает словарь, где значение по умолчанию - пустой список
    reminders_by_user = defaultdict(list)
    for sub in active_subscriptions:
        # sub.user и sub.event уже загружены благодаря selectinload
        if sub.user and sub.event:
            reminders_by_user[sub.user].append(sub.event)

    # 3. Проходимся по каждому пользователю и отправляем ему сводку
    for user, events in reminders_by_user.items():
        lexicon = Lexicon(user.language_code)
        
        header = lexicon.get('subs_reminder_header')
        
        events_parts = []
        for i, event in enumerate(events, 1):
            date_str = event.date_start.strftime('%d.%m.%Y %H:%M') if event.date_start else "TBA"
            tickets_str = event.tickets_info or "В наличии"
            
            event_text = (
                f"{hbold(f'{i}. {event.title}')}\n"
                f"📅 {date_str}\n"
                f"🎟️ Билеты: {tickets_str}"
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
            # Небольшая пауза между отправками, чтобы не попасть под лимиты Telegram
            await asyncio.sleep(0.1) 
        except TelegramForbiddenError:
            print(f"Пользователь {user.user_id} заблокировал бота. Деактивируем его подписки.")
            await db_notifier.deactivate_user_subscriptions(user.user_id)
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {user.user_id}: {e}")