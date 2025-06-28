# app/handlers/common.py

from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.utils.markdown import hbold

from ..database.requests import requests as db
from ..database.models import async_session
from app import keyboards as kb
from ..lexicon import Lexicon, LEXICON_COMMANDS_RU, LEXICON_COMMANDS_EN, EVENT_TYPE_EMOJI
from .onboarding import start_onboarding_process

router = Router()

from app.utils import set_main_menu


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_lang = message.from_user.language_code
    lexicon = Lexicon(user_lang)
    
    async with async_session() as session:
        user = await db.get_or_create_user(session, message.from_user.id, message.from_user.username, user_lang)
    await set_main_menu(bot, user_lang)
    if user.home_country:
        await message.answer(
            lexicon.get('main_menu_greeting').format(first_name=hbold(message.from_user.first_name)),
            parse_mode=ParseMode.HTML,
            reply_markup=kb.get_main_menu_keyboard(lexicon),
        )
        return
    
    await start_onboarding_process(message, state, lexicon)

# @router.callback_query(F.data == "change_location")
# async def cq_change_location(callback: CallbackQuery, state: FSMContext):
#     lexicon = Lexicon(callback.from_user.language_code)
#     await start_onboarding_process(callback, state, lexicon)

@router.message(F.text.startswith('/'))
async def any_unregistered_command_handler(message: Message):
    await message.reply("Я не знаю такой команды. Воспользуйтесь кнопками меню.")