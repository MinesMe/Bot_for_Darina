import asyncio
from aiogram import Bot, Dispatcher
from app.database.models import async_main

from app.handlers  import main_router as router
from app.database.listener import listen_for_db_notifications

import os
from dotenv import load_dotenv

load_dotenv()


async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await async_main()
    listener_task = asyncio.create_task(listen_for_db_notifications(bot))
    print("Слушатель уведомлений от базы данных запущен в фоновом режиме.")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
    


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("бот отключён")