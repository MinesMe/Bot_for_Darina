# app/database/requests.py

from sqlalchemy import select, delete, and_, or_, func, distinct, union
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from thefuzz import process as fuzzy_process, fuzz
from datetime import datetime

from .models import (
    async_session, User, Subscription, Event, Artist, Venue, EventLink,
    EventType, EventArtist, Country, City
)

SIMILARITY_THRESHOLD = 85

# --- Функции для работы с пользователями и предпочтениями ---
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


async def update_user_preferences(user_id: int, home_country: str, home_city: str, event_types: list, main_geo_completed):
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.home_country = home_country
            user.home_city = home_city
            user.preferred_event_types = event_types
            user.main_geo_completed = main_geo_completed
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


# --- ФУНКЦИИ ДЛЯ МОБИЛЬНОСТИ ---

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


# --- ФУНКЦИИ ДЛЯ ПОДПИСОК ---
async def get_user_subscriptions(user_id: int) -> list:
    """Получает список всех подписок пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(Subscription.item_name)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.item_name)
        )
        return result.scalars().all()


async def add_subscriptions_bulk(user_id: int, subscriptions_data: list[dict]):
    """
    Массово добавляет подписки из списка словарей в одной транзакции.
    Каждый словарь: {'item_name': '...', 'category': '...', 'regions': [...]}
    """
    if not subscriptions_data:
        return

    async with async_session() as session:
        # Получаем текущие подписки пользователя, чтобы не создавать дубликаты
        current_subs_stmt = select(Subscription.item_name).where(Subscription.user_id == user_id)
        current_subs_result = await session.execute(current_subs_stmt)
        current_subs_set = set(current_subs_result.scalars().all())

        new_subs_to_add = []
        for sub_data in subscriptions_data:
            if sub_data['item_name'] not in current_subs_set:
                new_subs_to_add.append(Subscription(user_id=user_id, **sub_data))

        if new_subs_to_add:
            session.add_all(new_subs_to_add)
            await session.commit()


async def remove_subscription(user_id: int, item_name: str):
    async with async_session() as session:
        await session.execute(
            delete(Subscription).where(and_(Subscription.user_id == user_id, Subscription.item_name == item_name)))
        await session.commit()


# --- ФУНКЦИИ ПОИСКА И АФИШИ ---
async def find_artists_fuzzy(query: str):
    async with async_session() as session:
        result = await session.execute(select(Artist.name))
        all_artists = result.scalars().all()
        found = fuzzy_process.extract(query, all_artists, limit=5)
        matches = [artist[0] for artist in found if artist[1] >= SIMILARITY_THRESHOLD]
        return matches


async def get_countries(home_country_selection: bool = False):
    if home_country_selection:
        return ["Беларусь", "Россия"]

    async with async_session() as session:
        result = await session.execute(select(Country.name).order_by(Country.name))
        return result.scalars().all()


async def get_top_cities_for_country(country_name: str, limit: int = 6):
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


async def find_events_fuzzy(query: str, user_regions: list = None):
    async with async_session() as session:
        search_query_like = f'%{query}%'
        stmt_title = select(Event.event_id).where(Event.title.ilike(search_query_like))
        stmt_artist = select(Event.event_id).join(Event.artists).join(EventArtist.artist).where(
            Artist.name.ilike(search_query_like))
        event_ids_query = union(stmt_title, stmt_artist).subquery()
        stmt = select(Event).options(
            selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
            selectinload(Event.links)
        ).join(event_ids_query, Event.event_id == event_ids_query.c.event_id)
        if user_regions:
            stmt = stmt.join(Event.venue).join(Venue.city).join(City.country).where(
                or_(
                    City.name.in_(user_regions),
                    Country.name.in_(user_regions)
                )
            )
        result = await session.execute(stmt)
        events = result.scalars().unique().all()
        if not events:
            all_events_stmt = select(Event).options(
                selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
                selectinload(Event.links),
                selectinload(Event.artists).selectinload(EventArtist.artist)
            )
            if user_regions:
                all_events_stmt = all_events_stmt.join(Event.venue).join(Venue.city).join(City.country).where(
                    or_(
                        City.name.in_(user_regions),
                        Country.name.in_(user_regions)
                    )
                )
            all_events_result = await session.execute(all_events_stmt)
            all_events = all_events_result.scalars().unique().all()
            matches = []
            search_query_lower = query.lower()
            for event in all_events:
                title_score = fuzz.partial_ratio(search_query_lower, event.title.lower())
                artist_scores = [fuzz.partial_ratio(search_query_lower, ea.artist.name.lower()) for ea in
                                 event.artists]
                max_score = max([title_score] + artist_scores) if artist_scores else title_score
                if max_score >= SIMILARITY_THRESHOLD:
                    matches.append((event, max_score))
            matches.sort(key=lambda x: x[1], reverse=True)
            return [match[0] for match in matches]
        return events


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


async def get_grouped_events_by_city_and_category(city_name: str, category: str):
    async with async_session() as session:
        stmt = (
            select(
                Event.title,
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
            .where(City.name == city_name, EventType.name == category)
            .group_by(Event.title, Venue.name)
            .order_by(func.min(Event.date_start).asc().nulls_last())
            .limit(20)
        )
        result = await session.execute(stmt)
        return result.all()


# --- ФУНКЦИИ ДЛЯ УВЕДОМЛЕНИЙ ---
async def find_upcoming_events():
    async with async_session() as session:
        today = datetime.now()
        stmt = select(Event).where(
            or_(
                Event.date_start >= today,
                Event.date_start.is_(None)
            )
        ).options(
            selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
            selectinload(Event.links),
            selectinload(Event.artists).selectinload(EventArtist.artist)
        )
        result = await session.execute(stmt)
        return result.scalars().unique().all()


async def get_subscribers_for_event(event: Event):
    async with async_session() as session:
        if not event.artists:
            return []

        artist_name = event.artists[0].artist.name

        subs_on_artist_result = await session.execute(
            select(Subscription)
            .options(selectinload(Subscription.user))
            .where(Subscription.item_name == artist_name)
        )
        subs_on_artist = subs_on_artist_result.scalars().all()

        subscribers_to_notify = []
        for sub in subs_on_artist:
            regions_to_check = sub.regions or []

            event_country = event.venue.city.country.name
            event_city = event.venue.city.name
            if event_country in regions_to_check or event_city in regions_to_check:
                subscribers_to_notify.append(sub.user)

        return subscribers_to_notify


# --- ПРОЧИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def get_all_master_artists() -> set:
    async with async_session() as session:
        result = await session.execute(select(Artist.name))
        return {name.lower() for name in result.scalars().all()}


async def get_artists_by_lowercase_names(names: list[str]) -> list[str]:
    async with async_session() as session:
        if not names:
            return []
        stmt = select(Artist.name).where(func.lower(Artist.name).in_(names))
        result = await session.execute(stmt)
        return result.scalars().all()


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


def extract_city_from_place(place_string: str) -> str:
    if not place_string:
        return "Минск"
    parts = place_string.split(',')
    if len(parts) > 1:
        city = parts[-1].strip()
        if not any(char.isdigit() for char in city):
            return city
    known_cities = ["Минск", "Брест", "Витебск", "Гомель", "Гродно", "Могилев", "Лида", "Молодечно", "Сморгонь",
                    "Несвиж"]
    for city in known_cities:
        if city.lower() in place_string.lower():
            return city
    return "Минск"

async def add_unique_event(event):
    async with async_session() as session:
        try:
            event_type_obj = await get_or_create(session, EventType, name=event["event_type"])
            city = extract_city_from_place(event['place'])
            venue = await get_or_create(session, Venue, name=event['place'], city_id=2,
                                        country_id=1)

            artist = await get_or_create(session, Artist, name=event['event_title'])

            start_datetime = None
            if event.get('timestamp'):
                try:
                    start_datetime = datetime.fromtimestamp(event['timestamp'])
                except (ValueError, TypeError):
                    start_datetime = None

            new_event_data = {
                "title": event['event_title'],
                "description": event['time'],
                "type_id": event_type_obj.type_id,
                "venue_id": venue.venue_id,
                "date_start": start_datetime,
                "price_min": event.get('price_min'),
                "price_max": event.get('price_max')
            }

            new_event = await get_or_create(session, Event, **new_event_data)
            
            event_artist_link = {"event_id": new_event.event_id, "artist_id": artist.artist_id}
            await get_or_create(session, EventArtist, **event_artist_link)
            
            event_url_link = {"event_id": new_event.event_id, "url": event['link'], "type": "bilety"}
            await get_or_create(session, EventLink, **event_url_link)

            await session.commit()
        except Exception as e:
            print("Ошибка при добавление ивента в бд: ")
            print(e)


async def get_subscribers_for_event_title(event_title: str) -> list[int]:
    async with async_session() as session:
        stmt = select(Subscription.user_id).where(
            Subscription.item_name == event_title
        ).distinct()
        result = await session.execute(stmt)
        user_ids = result.scalars().all()
        return list(user_ids)