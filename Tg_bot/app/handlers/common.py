# app/handlers/common.py

from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.utils.markdown import hbold

from ..database import requests as db
from ..database.models import async_session
from .. import keyboards as kb
from ..lexicon import Lexicon, LEXICON_COMMANDS_RU, LEXICON_COMMANDS_EN
from .onboarding import start_onboarding_process

router = Router()


async def set_main_menu(bot: Bot, lang: str):
    commands = LEXICON_COMMANDS_RU if lang in ('ru', 'be') else LEXICON_COMMANDS_EN
    main_menu_commands = [BotCommand(command=cmd, description=desc) for cmd, desc in commands.items()]
    await bot.set_my_commands(main_menu_commands)


async def format_grouped_events_for_response(events: list) -> str:
    if not events: return "По вашему запросу ничего не найдено."
    response_parts = []
    for event in events:
        title_text = hbold(event.title)
        url = event.links[0] if event.links and event.links[0] else None
        title_link = f'<a href="{url}">{title_text}</a>' if url else title_text
        place_info = event.venue_name or "—"
        dates_str = sorted(list(set(d.strftime("%d.%m.%Y в %H:%M") for d in event.dates if d)))
        dates_info = "\n".join(f"▫️ {d}" for d in dates_str) if dates_str else "—"
        price_info = "—"
        if event.min_price and event.max_price and event.min_price != event.max_price:
            price_info = f"от {event.min_price} до {event.max_price} BYN"
        elif event.min_price:
            price_info = f"от {event.min_price} BYN"
        event_card = (f"{title_link}\n\n"
                      f"📍 <b>Место:</b> <i>{place_info}</i>\n"
                      f"💰 <b>Цена:</b> <i>{price_info}</i>\n\n"
                      f"📅 <b>Доступные даты:</b>\n<i>{dates_info}</i>")
        response_parts.append(event_card)
    separator = "\n\n" + "—" * 15 + "\n\n"
    return separator.join(response_parts)


async def format_events_for_response(events: list) -> str:
    if not events: return "По вашему запросу ничего не найдено."
    response_parts = []
    for event in events:
        url = event.links[0].url if event.links else None
        title = hbold(event.title)
        title_link = f'<a href="{url}">{title}</a>' if url else title
        place_info = f"{event.venue.name}, {event.venue.city.name}" if event.venue and event.venue.city else (
            event.venue.name if event.venue else "—")
        date_start_info = event.date_start.strftime("%d.%m.%Y в %H:%M") if event.date_start else "—"
        price_info = "—"
        if event.price_min and event.price_max:
            price_info = f"от {event.price_min} до {event.price_max} BYN"
        elif event.price_min:
            price_info = f"от {event.price_min} BYN"
        when_info = event.description or "—"
        event_card = (f"{title_link}\n\n"
                      f"📍 <b>Место:</b> <i>{place_info}</i>\n"
                      f"🕒 <b>Время:</b> <i>{when_info}</i>\n"
                      f"📅 <b>Начало:</b> <i>{date_start_info}</i>\n"
                      f"💰 <b>Цена:</b> <i>{price_info}</i>")
        response_parts.append(event_card)
    separator = "\n\n" + "—" * 15 + "\n\n"
    return separator.join(response_parts)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_lang = message.from_user.language_code
    lexicon = Lexicon(user_lang)
    await set_main_menu(bot, user_lang)
    async with async_session() as session:
        user = await db.get_or_create_user(session, message.from_user.id, message.from_user.username, user_lang)

    if user.home_country:
        await message.answer(
            lexicon.get('main_menu_greeting').format(first_name=hbold(message.from_user.first_name)),
            reply_markup=kb.get_main_geo_settings(lexicon), parse_mode=ParseMode.HTML
        )
        return
    await start_onboarding_process(message, state, lexicon)

@router.callback_query(F.data == "change_location")
async def cq_change_location(callback: CallbackQuery, state: FSMContext):
    lexicon = Lexicon(callback.from_user.language_code)
    await start_onboarding_process(callback, state, lexicon)

@router.message(F.text.startswith('/'))
async def any_unregistered_command_handler(message: Message):
    await message.reply("Я не знаю такой команды. Воспользуйтесь кнопками меню.")