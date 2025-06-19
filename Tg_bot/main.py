import asyncio
from aiogram import Bot, Dispatcher
from app.database.models import async_main, listen_for_db_notifications
from app.handlers import router


import os
from dotenv import load_dotenv

load_dotenv()


async def main():
    await async_main()
    listener_task = asyncio.create_task(listen_for_db_notifications())
    print("Слушатель уведомлений от базы данных запущен в фоновом режиме.")
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
    


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("бот отключён")