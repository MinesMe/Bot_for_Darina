import asyncio
import os
import sys
from aiogram import Bot
from aiogram.enums import ParseMode
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Tg_bot')))

from app.database import requests as db
from app.handlers import format_events_for_response


async def send_notifications():
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("Ошибка: BOT_TOKEN не найден в .env файле.")
        return

    bot = Bot(token=bot_token)
    print("Запуск рассылки уведомлений...")

    upcoming_events = await db.find_upcoming_events()

    if not upcoming_events:
        print("Нет предстоящих событий для уведомлений.")
        await bot.session.close()
        return

    print(f"Найдено {len(upcoming_events)} предстоящих событий. Проверка подписчиков...")

    notifications_sent = 0
    for event in upcoming_events:
        subscribers = await db.get_subscribers_for_event(event)
        if not subscribers:
            continue

        for user in subscribers:
            if event.venue and user.regions and event.venue.city in user.regions:
                print(f"  -> Отправка уведомления пользователю {user.user_id} о событии '{event.title}'")
                try:
                    event_text = await format_events_for_response([event])
                    intro_text = "🔔 Уведомление о подписке!\n\nСкоро состоится событие, на которое вы подписаны:\n\n"

                    await bot.send_message(
                        chat_id=user.user_id,
                        text=intro_text + event_text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                    notifications_sent += 1
                    await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"  -! Не удалось отправить уведомление пользователю {user.user_id}: {e}")

    print(f"Рассылка завершена. Отправлено уведомлений: {notifications_sent}.")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(send_notifications())