from sqlalchemy import select, delete, and_, or_, func, distinct, union
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from thefuzz import process as fuzzy_process, fuzz
from datetime import datetime

from .models import async_session, User, Subscription, Event, Artist, Venue, EventLink, EventType, EventArtist, Country, \
    City

SIMILARITY_THRESHOLD = 85


# --- Функции для работы с пользователями и подписками ---
async def get_or_create_user(session, user_id: int, username: str = None, lang_code: str = 'en'):
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(user_id=user_id, username=username, regions=[], language_code=lang_code)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif not user.language_code or user.language_code != lang_code:
        user.language_code = lang_code
        await session.commit()
    return user


async def get_user_regions(user_id: int):
    async with async_session() as session:
        result = await session.execute(select(User.regions).where(User.user_id == user_id))
        return result.scalar_one()


async def update_user_regions(user_id: int, regions: list):
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.regions = regions
            await session.commit()


async def get_user_subscriptions(user_id: int) -> list:
    async with async_session() as session:
        result = await session.execute(
            select(Subscription.item_name).where(Subscription.user_id == user_id).order_by(Subscription.item_name))
        return result.scalars().all()


async def add_subscription(user_id: int, item_name: str, category: str):
    async with async_session() as session:
        # Сначала убедимся, что пользователь существует
        user_result = await session.execute(select(User).where(User.user_id == user_id))
        if not user_result.scalar_one_or_none():
            # В реальном приложении это не должно происходить, но для надежности
            await get_or_create_user(session, user_id)

        result = await session.execute(
            select(Subscription).where(and_(Subscription.user_id == user_id, Subscription.item_name == item_name)))
        if not result.scalar_one_or_none():
            session.add(Subscription(user_id=user_id, item_name=item_name, category=category))
            await session.commit()


async def remove_subscription(user_id: int, item_name: str):
    async with async_session() as session:
        await session.execute(
            delete(Subscription).where(and_(Subscription.user_id == user_id, Subscription.item_name == item_name)))
        await session.commit()


async def find_artists_fuzzy(query: str):
    async with async_session() as session:
        result = await session.execute(select(Artist.name))
        all_artists = result.scalars().all()
        found = fuzzy_process.extract(query, all_artists, limit=5)
        matches = [artist[0] for artist in found if artist[1] >= SIMILARITY_THRESHOLD]
        return matches


# --- НОВЫЕ И ОБНОВЛЕННЫЕ ФУНКЦИИ ---

async def get_countries():
    """Возвращает список всех стран из БД."""
    async with async_session() as session:
        result = await session.execute(select(Country.name).order_by(Country.name))
        return result.scalars().all()


async def get_top_cities_for_country(country_name: str, limit: int = 6):
    """Возвращает топ-N городов для страны из БД."""
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
    """Ищет города по нечеткому совпадению в указанной стране."""
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


# --- ПОЛНОСТЬЮ ПЕРЕПИСАННАЯ ФУНКЦИЯ ПОИСКА ---
async def find_events_fuzzy(query: str, user_regions: list = None):
    async with async_session() as session:
        # Сначала пробуем прямой поиск по части строки (быстрее)
        search_query_like = f'%{query}%'

        # Запрос для поиска по названию события
        stmt_title = select(Event.event_id).where(Event.title.ilike(search_query_like))

        # Запрос для поиска по имени артиста
        stmt_artist = select(Event.event_id).join(Event.artists).join(EventArtist.artist).where(
            Artist.name.ilike(search_query_like))

        # Объединяем ID событий, найденных обоими способами
        event_ids_query = union(stmt_title, stmt_artist).subquery()

        # Основной запрос для получения полных данных о событиях
        stmt = select(Event).options(
            selectinload(Event.venue).selectinload(Venue.city).selectinload(City.country),
            selectinload(Event.links)
        ).join(event_ids_query, Event.event_id == event_ids_query.c.event_id)

        # Фильтруем по регионам пользователя, если они есть
        if user_regions:
            stmt = stmt.join(Event.venue).join(Venue.city).join(City.country).where(
                or_(
                    City.name.in_(user_regions),
                    Country.name.in_(user_regions)
                )
            )

        result = await session.execute(stmt)
        events = result.scalars().unique().all()

        # Если прямой поиск ничего не дал, используем нечеткий
        if not events:
            print("Прямой поиск не дал результатов, используется нечеткий поиск...")
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
                # Проверяем и название события, и имена артистов
                title_score = fuzz.partial_ratio(search_query_lower, event.title.lower())
                artist_scores = [fuzz.partial_ratio(search_query_lower, ea.artist.name.lower()) for ea in event.artists]
                max_score = max([title_score] + artist_scores) if artist_scores else title_score

                if max_score >= SIMILARITY_THRESHOLD:
                    matches.append((event, max_score))

            matches.sort(key=lambda x: x[1], reverse=True)
            return [match[0] for match in matches]

        return events


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
            selectinload(Event.links)
        )
        result = await session.execute(stmt)
        return result.scalars().all()


async def get_subscribers_for_event(event: Event):
    async with async_session() as session:
        artist_result = await session.execute(
            select(Artist.name)
            .join(EventArtist, EventArtist.artist_id == Artist.artist_id)
            .where(EventArtist.event_id == event.event_id)
        )
        artist_name = artist_result.scalar_one_or_none()

        if not artist_name:
            return []

        subscribers_result = await session.execute(
            select(User)
            .join(Subscription, User.user_id == Subscription.user_id)
            .where(
                Subscription.item_name == artist_name,
                or_(
                    event.venue.city.name.in_(User.regions),
                    event.venue.city.country.name.in_(User.regions)
                )
            )
        )
        return subscribers_result.scalars().all()