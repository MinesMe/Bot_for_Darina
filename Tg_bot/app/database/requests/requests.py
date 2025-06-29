# app/database/requests.py

import logging
from sqlalchemy import select, delete, and_, or_, func, distinct, union, update
from sqlalchemy.orm import selectinload, joinedload,undefer
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from thefuzz import process as fuzzy_process, fuzz
from datetime import datetime

from ..models import (
    UserFavorite, async_session, User, Subscription, Event, Artist, Venue, EventLink,
    EventType, EventArtist, Country, City
)

SIMILARITY_THRESHOLD = 85


async def get_or_create(session, model, **kwargs):
    instance = await session.execute(select(model).filter_by(**kwargs))
    instance = instance.scalar_one_or_none()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        await session.flush()
        return instance

async def get_or_create_user(session, user_id: int, username: str = None, lang_code: str = 'en'):
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(user_id=user_id, username=username, language_code=lang_code)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif not user.language_code or user.language_code != lang_code:
        user.language_code = lang_code
        await session.commit()
    return user

async def get_user_lang(user_id):
    async with async_session() as session:
        result = await session.execute(
            select(User.language_code)
            .where(User.user_id == user_id)
        )
        prefs = result.first()
        if prefs:
            return prefs.language_code
        return None

async def update_user_preferences(user_id: int, home_country: str, home_city: str, event_types: list, main_geo_completed: bool):
    # ... (код без изменений)
    async with async_session() as session:
        # ИЗМЕНЕНИЕ: Используем update для эффективности
        stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(
                home_country=home_country,
                home_city=home_city,
                preferred_event_types=event_types,
                main_geo_completed=main_geo_completed
            )
        )
        await session.execute(stmt)
        await session.commit()

async def get_user_preferences(user_id: int) -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(User.home_city, User.preferred_event_types, User.home_country)
            .where(User.user_id == user_id)
        )
        prefs = result.first()
        if prefs:
            return {
                "home_country": prefs.home_country,
                "home_city": prefs.home_city,
                "preferred_event_types": prefs.preferred_event_types
            }
        return None

async def get_user_favorites(user_id: int) -> list[Artist]:
    """Получает список всех "Объектов интереса" (Артистов) из избранного пользователя."""
    async with async_session() as session:
        # ИЗМЕНЕНИЕ: Используем явное условие для JOIN
        stmt = (
            select(Artist)
            .join(UserFavorite, Artist.artist_id == UserFavorite.artist_id)
            .where(UserFavorite.user_id == user_id)
            .order_by(Artist.name)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

async def add_artist_to_favorites(session,user_id: int, artist_id: int, regions:list):
    """Добавляет "Объект интереса" (Артиста) в избранное пользователя."""
    
    # Убираем `async with`, так как сессия передается извне
    existing_stmt = select(UserFavorite).where(
    and_(UserFavorite.user_id == user_id, UserFavorite.artist_id == artist_id)
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    
    if not existing:
        # Если нет - создаем новую запись с регионами
        new_favorite = UserFavorite(user_id=user_id, artist_id=artist_id, regions=regions)
        session.add(new_favorite)
    else:
        # Если уже есть - просто обновляем регионы
        existing.regions = regions  

async def remove_artist_from_favorites(user_id: int, artist_id: int):
    """
    Удаляет "Объект интереса" (Артиста) из избранного.
    ВАЖНО: Также удаляет все подписки пользователя на события этого артиста.
    """
    async with async_session() as session:
        # Шаг 1: Найти все event_id для данного artist_id
        events_to_unsub_stmt = select(Event.event_id).join(EventArtist).where(EventArtist.artist_id == artist_id)
        events_to_unsub_result = await session.execute(events_to_unsub_stmt)
        event_ids_to_unsub = events_to_unsub_result.scalars().all()

        if event_ids_to_unsub:
            # Шаг 2: Удалить все подписки пользователя на эти события
            delete_subs_stmt = delete(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.event_id.in_(event_ids_to_unsub)
                )
            )
            await session.execute(delete_subs_stmt)

        # Шаг 3: Удалить самого артиста из избранного
        delete_fav_stmt = delete(UserFavorite).where(
            and_(UserFavorite.user_id == user_id, UserFavorite.artist_id == artist_id)
        )
        await session.execute(delete_fav_stmt)
        await session.commit()

async def check_main_geo_status(user_id: int) -> bool:
    """Проверяет, проходил ли пользователь ОСНОВНОЙ онбординг (для Афиши)."""
    async with async_session() as session:
        result = await session.execute(select(User.main_geo_completed).where(User.user_id == user_id))
        return result.scalar_one_or_none() or False

async def check_general_geo_onboarding_status(user_id: int) -> bool:
    """Проверяет, проходил ли пользователь онбординг ОБЩЕЙ мобильности (для Подписок)."""
    async with async_session() as session:
        result = await session.execute(select(User.general_geo_completed).where(User.user_id == user_id))
        return result.scalar_one_or_none() or False

async def set_general_geo_onboarding_completed(user_id: int):
    """Отмечает, что пользователь прошел онбординг ОБЩЕЙ мобильности."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.general_geo_completed = True
            await session.commit()

async def get_general_mobility(user_id: int) -> list | None:
    """Получает список регионов из общей мобильности пользователя (из поля User.general_mobility_regions)."""
    async with async_session() as session:
        stmt = select(User.general_mobility_regions).where(User.user_id == user_id)
        result = await session.execute(stmt)
        regions_data = result.scalar_one_or_none()
        return regions_data if regions_data else None

async def set_general_mobility(user_id: int, regions: list):
    """Устанавливает или обновляет список регионов общей мобильности для пользователя."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.general_mobility_regions = regions
            await session.commit()

async def get_user_subscriptions(user_id: int) -> list[Event]:
    """ИЗМЕНЕНИЕ: Получает список всех СОБЫТИЙ, на которые подписан пользователь."""
    async with async_session() as session:
        stmt = (
            select(Event)
            .join(Subscription)
            .where(Subscription.user_id == user_id) 
            .options(
                selectinload(Event.venue).selectinload(Venue.city),
                selectinload(Event.subscriptions).load_only(Subscription.status)
            )
            .order_by(Event.date_start)
        )
        result = await session.execute(stmt)
        return result.scalars().unique().all()

async def add_events_to_subscriptions_bulk(user_id: int, event_ids: list[int]):
    """ИЗМЕНЕНИЕ: Массово добавляет подписки на СОБЫТИЯ по их ID."""
    if not event_ids:
        return

    async with async_session() as session:
        # Получаем текущие подписки, чтобы не создавать дубликаты
        current_subs_stmt = select(Subscription.event_id).where(Subscription.user_id == user_id)
        current_subs_result = await session.execute(current_subs_stmt)
        current_subs_set = set(current_subs_result.scalars().all())

        new_subs_to_add = [
            Subscription(user_id=user_id, event_id=eid)
            for eid in event_ids if eid not in current_subs_set
        ]

        if new_subs_to_add:
            session.add_all(new_subs_to_add)
            await session.commit()

async def remove_subscription(user_id: int, event_id: int, reason: str = None):
    """ИЗМЕНЕНИЕ: Удаляет подписку на конкретное СОБЫТИЕ по event_id."""
    async with async_session() as session:
        # Вместо удаления можно обновлять статус, но пока удаляем
        stmt = delete(Subscription).where(
            and_(Subscription.user_id == user_id, Subscription.event_id == event_id)
        )
        await session.execute(stmt)
        await session.commit()

async def set_subscription_status(user_id: int, event_id: int, status: str):
    """НОВАЯ ФУНКЦИЯ: Устанавливает статус подписки (active/paused)."""
    async with async_session() as session:
        stmt = (
            update(Subscription)
            .where(and_(Subscription.user_id == user_id, Subscription.event_id == event_id))
            .values(status=status)
        )
        await session.execute(stmt)
        await session.commit()

async def find_artists_fuzzy(query: str, limit: int = 5) -> list[Artist]:
    """ИЗМЕНЕНИЕ: Возвращает полные объекты Artist, а не просто имена."""
    async with async_session() as session:
        result = await session.execute(select(Artist))
        all_artists = result.scalars().all()
        # Создаем словарь "имя -> объект" для быстрого доступа
        artist_map = {artist.name: artist for artist in all_artists}
        
        found = fuzzy_process.extract(query, artist_map.keys(), limit=limit)
        
        # Возвращаем объекты Artist для совпадений выше порога
        matches = [artist_map[artist_name] for artist_name, score in found if score >= SIMILARITY_THRESHOLD]
        return matches

async def get_countries(home_country_selection: bool = False):
    if home_country_selection:
        return ["Беларусь", "Россия"]

    async with async_session() as session:
        result = await session.execute(select(Country.name).order_by(Country.name))
        return result.scalars().all()

async def get_top_cities_for_country(country_name: str, limit: int = 6):
    if country_name == "Беларусь":
        # Если запросили Беларусь, возвращаем заранее определенный список
        return ["Минск", "Брест", "Витебск", "Гомель", "Гродно", "Могилев"]

    # --- СТАРАЯ ЛОГИКА ДЛЯ ВСЕХ ОСТАЛЬНЫХ СТРАН ---
    async with async_session() as session:
        result = await session.execute(
            select(City.name)
            .join(Country)
            .where(Country.name == country_name)
            .order_by(City.city_id)
            .limit(limit)
        )
        return result.scalars().all()

async def find_cities_fuzzy(country_name: str, query: str, limit: int = 3):
    async with async_session() as session:
        result = await session.execute(
            select(City.name).join(Country).where(Country.name == country_name)
        )
        all_cities = result.scalars().all()
        if not all_cities:
            return []
        found = fuzzy_process.extract(query, all_cities, limit=limit)
        best_matches = [city[0] for city in found if city[1] >= 85]
        return best_matches

async def find_events_fuzzy(
    query: str, 
    user_regions: list = None,
    date_from: datetime = None,
    date_to: datetime = None
):
    """
    Нечеткий поиск событий с фильтрацией по региону и дате.
    """
    async with async_session() as session:
        # --- Собираем условия для фильтрации ---
        date_conditions = []
        if date_from:
            date_conditions.append(Event.date_start >= date_from)
        if date_to:
            end_of_day = date_to.replace(hour=23, minute=59, second=59)
            date_conditions.append(Event.date_start <= end_of_day)

        region_conditions = []
        if user_regions:
            region_conditions.append(
                or_(
                    City.name.in_(user_regions),
                    Country.name.in_(user_regions)
                )
            )

        # --- Этап 1: Быстрый поиск по точному совпадению (ilike) ---
        search_query_like = f'%{query}%'
        stmt_title = select(Event.event_id).where(Event.title.ilike(search_query_like))
        stmt_artist = select(Event.event_id).join(Event.artists).join(EventArtist.artist).where(
            Artist.name.ilike(search_query_like))
        
        event_ids_query = union(stmt_title, stmt_artist).subquery()
        
        stmt = (
            select(Event)
            .options(
                selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
                selectinload(Event.links)
            )
            .join(event_ids_query, Event.event_id == event_ids_query.c.event_id)
        )

        # Применяем фильтры к быстрому поиску
        if region_conditions:
            stmt = stmt.join(Event.venue).join(Venue.city).join(City.country).where(*region_conditions)
        if date_conditions:
            stmt = stmt.where(*date_conditions)
        
        result = await session.execute(stmt)
        events = result.scalars().unique().all()

        # Если быстрый поиск что-то нашел, возвращаем результат
        if events:
            return events

        # --- Этап 2: Медленный, но полный нечеткий поиск (если быстрый не сработал) ---
        all_events_stmt = (
            select(Event)
            .options(
                selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
                selectinload(Event.links),
                selectinload(Event.artists).selectinload(EventArtist.artist)
            )
        )
        
        # Применяем фильтры к полному списку событий
        if region_conditions:
            all_events_stmt = all_events_stmt.join(Event.venue).join(Venue.city).join(City.country).where(*region_conditions)
        if date_conditions:
            all_events_stmt = all_events_stmt.where(*date_conditions)
            
        all_events_result = await session.execute(all_events_stmt)
        all_events = all_events_result.scalars().unique().all()

        matches = []
        search_query_lower = query.lower()
        for event in all_events:
            title_score = fuzz.partial_ratio(search_query_lower, event.title.lower())
            artist_scores = [fuzz.partial_ratio(search_query_lower, ea.artist.name.lower()) for ea in event.artists]
            max_score = max([title_score] + artist_scores) if artist_scores else title_score
            if max_score >= SIMILARITY_THRESHOLD:
                matches.append((event, max_score))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches]

async def get_events_for_artists(artist_names: list[str], regions: list[str]) -> list[Event]:
    """
    Находит предстоящие события для заданного списка артистов в указанных регионах (странах или городах).
    """
    if not artist_names or not regions:
        return []

    async with async_session() as session:
        today = datetime.now()
        stmt = (
            select(Event)
            .join(Event.artists)
            .join(EventArtist.artist)
            .join(Event.venue)
            .join(Venue.city)
            .join(City.country)
            .where(
                and_(
                    Artist.name.in_(artist_names),
                    or_(
                        City.name.in_(regions),
                        Country.name.in_(regions)
                    ),
                    or_(
                        Event.date_start >= today,
                        Event.date_start.is_(None)
                    )
                )
            )
            .options(
                selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
                selectinload(Event.links)
            )
            .distinct()
        )
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_cities_for_category(category_name: str, user_regions: list):
    async with async_session() as session:
        stmt = (
            select(distinct(City.name))
            .join(Venue, City.city_id == Venue.city_id)
            .join(Event, Venue.venue_id == Event.venue_id)
            .join(EventType, Event.type_id == EventType.type_id)
            .where(EventType.name == category_name)
            .order_by(City.name)
        )
        if user_regions:
            stmt = stmt.join(Country, City.country_id == Country.country_id).where(or_(
                City.name.in_(user_regions),
                Country.name.in_(user_regions)
            ))
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_grouped_events_by_city_and_category(
    city_name: str, 
    category: str,
    date_from: datetime = None,
    date_to: datetime = None
):
    """
    Получает сгруппированные события с фильтрацией по дате.
    Возвращает event_id и category_name.
    """
    async with async_session() as session:
        # Основа запроса
        stmt = (
            select(
                (func.array_agg(aggregate_order_by(Event.event_id, Event.date_start.asc())))[1].label("event_id"),
                Event.title,
                EventType.name.label("category_name"),
                Venue.name.label("venue_name"),
                array_agg(aggregate_order_by(Event.date_start, Event.date_start.asc())).label("dates"),
                array_agg(aggregate_order_by(EventLink.url, Event.date_start.asc())).label("links"),
                func.min(Event.price_min).label("min_price"),
                func.max(Event.price_max).label("max_price")
            )
            .join(Venue, Event.venue_id == Venue.venue_id)
            .join(City, Venue.city_id == City.city_id)
            .join(EventType, Event.type_id == EventType.type_id)
            .outerjoin(EventLink, Event.event_id == EventLink.event_id)
        )

        # Формируем условия фильтрации (WHERE)
        today = datetime.now()

        # Формируем условия фильтрации (WHERE)
        conditions = [
            City.name == city_name,
            EventType.name == category,
            # НОВОЕ УСЛОВИЕ: дата начала должна быть больше или равна СЕГОДНЯШНЕМУ ДНЮ
            # или не указана вовсе (для анонсов).
            or_(Event.date_start >= today, Event.date_start.is_(None))
        ]
        
        if date_from:
            # Условие "больше или равно" для даты начала
            conditions.append(Event.date_start >= date_from)
        if date_to:
            # Чтобы включить весь конечный день, ищем до начала следующего дня
            end_of_day = date_to.replace(hour=23, minute=59, second=59)
            conditions.append(Event.date_start <= end_of_day)

        # Применяем все условия
        stmt = stmt.where(and_(*conditions))

        # Группировка и сортировка
        stmt = (
            stmt.group_by(Event.title, Venue.name, EventType.name)
            .order_by(func.min(Event.date_start).asc().nulls_last())
            .limit(20)
        )
        
        result = await session.execute(stmt)
        return result.all()


# --- ФУНКЦИИ ДЛЯ УВЕДОМЛЕНИЙ ---
# async def find_upcoming_events():
#     async with async_session() as session:
#         today = datetime.now()
#         stmt = select(Event).where(
#             or_(
#                 Event.date_start >= today,
#                 Event.date_start.is_(None)
#             )
#         ).options(
#             selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
#             selectinload(Event.links),
#             selectinload(Event.artists).selectinload(EventArtist.artist)
#         )
#         result = await session.execute(stmt)
#         return result.scalars().unique().all()


# async def get_subscribers_for_event(event: Event):
#     async with async_session() as session:
#         if not event.artists:
#             return []

#         artist_name = event.artists[0].artist.name

#         subs_on_artist_result = await session.execute(
#             select(Subscription)
#             .options(selectinload(Subscription.user))
#             .where(Subscription.item_name == artist_name)
#         )
#         subs_on_artist = subs_on_artist_result.scalars().all()

#         subscribers_to_notify = []
#         for sub in subs_on_artist:
#             regions_to_check = sub.regions or []

#             event_country = event.venue.city.country.name
#             event_city = event.venue.city.name
#             if event_country in regions_to_check or event_city in regions_to_check:
#                 subscribers_to_notify.append(sub.user)

#         return subscribers_to_notify


# --- ПРОЧИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
# async def get_all_master_artists() -> set:
#     async with async_session() as session:
#         result = await session.execute(select(Artist.name))
#         return {name.lower() for name in result.scalars().all()}


# async def get_artists_by_lowercase_names(names: list[str]) -> list[str]:
#     async with async_session() as session:
#         if not names:
#             return []
#         stmt = select(Artist.name).where(func.lower(Artist.name).in_(names))
#         result = await session.execute(stmt)
#         return result.scalars().all()



async def get_or_create_city_and_country(session, city_name: str, country_name: str) -> tuple[City, Country]:
    """
    Находит или создает страну по имени, затем находит или создает город в этой стране.
    Возвращает объекты City и Country.
    """
    # Сначала находим или создаем страну
    country_obj = await get_or_create(session, Country, name=country_name)

    # Теперь, когда у нас есть ID страны, ищем город в этой конкретной стране
    city_stmt = select(City).where(
        and_(
            City.name == city_name,
            City.country_id == country_obj.country_id
        )
    )
    city_obj = (await session.execute(city_stmt)).scalar_one_or_none()

    if city_obj:
        # Город в нужной стране найден
        return city_obj, country_obj
    else:
        # Город не найден, создаем его с правильным country_id
        new_city = City(name=city_name, country_id=country_obj.country_id)
        session.add(new_city)
        await session.flush() # Получаем city_id
        logging.info(f"  - Добавлен новый город: '{city_name}' в страну '{country_name}'")
        return new_city, country_obj

async def get_subscribers_for_event_title(event_title: str) -> list[int]:
    async with async_session() as session:
        stmt = select(Subscription.user_id).where(
            Subscription.item_name == event_title
        ).distinct()
        result = await session.execute(stmt)
        user_ids = result.scalars().all()
        return list(user_ids)
    
async def get_subscription_details(user_id: int, event_id: int) -> Subscription | None:
    """
    Получает полную информацию о конкретной подписке пользователя
    по user_id и event_id.
    """
    async with async_session() as session:
        stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                # ИЗМЕНЕНИЕ: Фильтруем по event_id, а не по item_name
                Subscription.event_id == event_id 
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def find_event_by_signature(session, title: str, date_start: datetime) -> Event | None:
    """
    Находит событие по его уникальной сигнатуре: названию и точной дате начала.
    Возвращает объект Event или None.
    """
    # Если нет даты или названия, невозможно найти уникальное событие
    if not title or not date_start:
        return None
        
    stmt = (
        select(Event)
        .where(
            and_(
                Event.title == title,
                Event.date_start == date_start
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def update_event_details(session, event_id: int, event_data: dict):
    """
    Обновляет ключевую информацию для СУЩЕСТВУЮЩЕГО события (цены, билеты).
    """
    await session.execute(
        update(Event)
        .where(Event.event_id == event_id)
        .values(
            price_min=event_data.get('price_min'),
            price_max=event_data.get('price_max'),
            tickets_info=event_data.get('tickets_info')
        )
    )
    
    # Также обновим или добавим ссылку на покупку, если она новая
    link_url = event_data.get('link')
    if link_url:
        link_stmt = select(EventLink).where(and_(EventLink.event_id == event_id, EventLink.url == link_url))
        existing_link = (await session.execute(link_stmt)).scalar_one_or_none()
        if not existing_link:
            new_link = EventLink(event_id=event_id, url=link_url, type="bilety")
            session.add(new_link)
            print(f"  - Добавлена новая ссылка для события ID {event_id}")

async def create_event_with_artists(session, event_data: dict, artist_names: list[str]) -> Event | None:
    """
    Создает новое событие и все его связи (место, артисты, ссылка).
    Теперь корректно работает со страной и городом.
    """
    try:
        # 1. Получаем/создаем связанные сущности
        event_type_obj = await get_or_create(session, EventType, name=event_data["event_type"])
        
        # Вызываем нашу новую, улучшенную функцию
        city_obj, country_obj = await get_or_create_city_and_country(
            session, 
            city_name=event_data['city'], 
            country_name=event_data['country_name'] # Передаем имя страны
        )
        
        # Создаем Venue с правильными ID города и страны
        venue_obj = await get_or_create(session, Venue, 
                                    name=event_data['venue'], 
                                    city_id=city_obj.city_id,
                                    country_id=country_obj.country_id) # <--- ВОТ ОНО!

        # 2. Создаем само событие
        new_event = Event(
            title=event_data['event_title'],
            description=event_data.get('time'), 
            venue_id=venue_obj.venue_id,
            type_id=event_type_obj.type_id,
            date_start=event_data.get('timestamp'),
            price_min=event_data.get('price_min'),
            price_max=event_data.get('price_max'),
            tickets_info=event_data.get('tickets_info')
        )
        session.add(new_event)
        await session.flush()

        # 3. Создаем ссылку на покупку
        if event_data.get('link'):
            event_url_link = EventLink(event_id=new_event.event_id, url=event_data['link'], type="bilety")
            session.add(event_url_link)

        # 4. Работа с артистами
        if artist_names:
            for artist_name in artist_names:
                # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
                # Приводим имя к нижнему регистру, как и в populate_artists_if_needed
                formatted_name = artist_name.strip().lower() 
                if not formatted_name: continue
                # get_or_create будет искать/создавать артиста с именем в нижнем регистре
                artist_obj = await get_or_create(session, Artist, name=formatted_name)
                event_artist_link = EventArtist(event_id=new_event.event_id, artist_id=artist_obj.artist_id)
                session.add(event_artist_link)

        await session.flush()
        return new_event

    except Exception as e:
        logging.error(f"Критическая ошибка при создании события '{event_data.get('event_title')}': {e}", exc_info=True)
        return None

# async def get_event_by_id(event_id: int) -> Event | None: #???????----------------------------------------------------------
    """Находит событие по его ID."""
    async with async_session() as session:
        # Используем session.get для простого поиска по первичному ключу
        result = await session.get(Event, event_id)
        return result
    
async def get_favorite_details(user_id: int, artist_id: int) -> UserFavorite | None:
    """Получает детали одной записи из избранного (включая регионы)."""
    async with async_session() as session:
        stmt = select(UserFavorite).where(
            and_(UserFavorite.user_id == user_id, UserFavorite.artist_id == artist_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
async def update_favorite_regions(user_id: int, artist_id: int, new_regions: list):

    """Обновляет регионы для конкретного избранного."""
    async with async_session() as session:
        stmt = (
            update(UserFavorite)
            .where(and_(UserFavorite.user_id == user_id, UserFavorite.artist_id == artist_id))
            .values(regions=new_regions)
        )
        await session.execute(stmt)
        await session.commit()

async def get_future_events_for_artists(artist_ids: list[int]) -> list[Event]:
    """
    Находит все предстоящие события для заданного списка ID артистов.
    События, у которых дата не указана (date_start is None), также считаются будущими.
    Загружает связанные данные для минимизации последующих запросов.

    Args:
        artist_ids: Список ID артистов.

    Returns:
        Список объектов Event.
    """
    if not artist_ids:
        return []

    async with async_session() as session:
        today = datetime.now()
        
        stmt = (
            select(Event)
            .join(Event.artists) # Соединяем с EventArtist
            .where(
                EventArtist.artist_id.in_(artist_ids),
                or_(
                    Event.date_start >= today,
                    Event.date_start.is_(None) # Включаем события без даты
                )
            )
            .options(
                # Загружаем артистов, чтобы знать, к кому относится событие
                selectinload(Event.artists).selectinload(EventArtist.artist), 
                # Загружаем полную информацию о месте проведения
                joinedload(Event.venue).joinedload(Venue.city).joinedload(City.country),
                # Загружаем ссылки на билеты
                selectinload(Event.links)
            )
            .order_by(Event.date_start.asc().nulls_last()) # Сортируем по дате
            .distinct()
        )
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
async def get_or_create_artists_by_name(names: list[str]) -> list[dict]:
    """
    Находит артистов по списку имен. Если артист не найден, создает его.
    Возвращает список СЛОВАРЕЙ с данными артистов, а не объектов SQLAlchemy.

    Args:
        names: Список имен артистов в нижнем регистре.

    Returns:
        Список словарей, каждый вида {'artist_id': int, 'name': str}.
    """
    if not names:
        return []

    async with async_session() as session:
        # 1. Найти всех уже существующих артистов
        existing_artists_stmt = select(Artist).where(func.lower(Artist.name).in_(names))
        existing_artists_result = await session.execute(existing_artists_stmt)
        existing_artists_list = existing_artists_result.scalars().all()
        
        existing_artists_map = {artist.name.lower(): artist for artist in existing_artists_list}

        # 2. Определить, каких артистов нужно создать
        names_to_create = [name for name in names if name not in existing_artists_map]

        # 3. Создать всех недостающих
        new_artists = []
        if names_to_create:
            new_artists = [Artist(name=name_to_create) for name_to_create in names_to_create]
            session.add_all(new_artists)
            # flush нужен, чтобы получить ID для новых артистов
            await session.flush() 
            print(f"Добавлено в БД {len(new_artists)} новых артистов: {', '.join(names_to_create)}")

        # 4. Собираем итоговый список из существующих и новых
        final_artist_list = existing_artists_list + new_artists
        
        # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ ---
        # Сразу же преобразуем объекты в словари, пока сессия еще жива
        result_dicts = [artist.to_dict() for artist in final_artist_list]
        
        await session.commit()
        
        return result_dicts