import asyncio
from aiogram import Bot, Dispatcher
from app.database.models import async_main
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.handlers  import main_router as router
from app.services.listener import listen_for_db_notifications
from app.services.notifier import send_reminders

import os
from dotenv import load_dotenv

load_dotenv()


async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await async_main()
    listener_task = asyncio.create_task(listen_for_db_notifications(bot))
    scheduler = AsyncIOScheduler(timezone="Europe/Minsk") # Укажите ваш часовой пояс
    scheduler.add_job(send_reminders, 'interval', seconds=30, args=(bot,))
    scheduler.start()
    print("Планировщик уведомлений запущен.")
    print("Слушатель уведомлений от базы данных запущен в фоновом режиме.")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
    


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("бот отключён")