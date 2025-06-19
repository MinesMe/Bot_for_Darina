from sqlalchemy import select, delete, and_, or_, func, distinct
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from thefuzz import fuzz
from datetime import datetime, timedelta


from .models import async_session, User, Subscription, Event, Artist, Venue, EventLink, EventType, EventArtist

SIMILARITY_THRESHOLD = 85


async def get_or_create_user(session, user_id: int, username: str = None):
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(user_id=user_id, username=username, regions=[])
        session.add(user)
        await session.commit()
        await session.refresh(user)
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

        matches = []
        search_query = query.lower().strip()
        for artist_name in all_artists:
            score = fuzz.partial_ratio(search_query, artist_name.lower())
            if score >= SIMILARITY_THRESHOLD:
                matches.append((artist_name, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches[:5]]


async def find_events_fuzzy(query: str, user_regions: list = None):
    async with async_session() as session:
        stmt = select(Event).options(selectinload(Event.venue), selectinload(Event.links))
        if user_regions:
            stmt = stmt.join(Event.venue).where(Venue.city.in_(user_regions))

        all_events_result = await session.execute(stmt)
        all_events = all_events_result.scalars().all()

        if not all_events: return []
        matches = []
        search_query = query.lower().strip()
        for event in all_events:
            score = fuzz.partial_ratio(search_query, event.title.lower())
            if score >= SIMILARITY_THRESHOLD:
                matches.append((event, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches]


async def get_all_cities():
    async with async_session() as session:
        result = await session.execute(
            select(distinct(Venue.city)).order_by(Venue.city)
        )
        return result.scalars().all()


async def get_cities_for_category(category_name: str, user_regions: list):
    async with async_session() as session:
        result = await session.execute(
            select(distinct(Venue.city))
            .join(Event, Event.venue_id == Venue.venue_id)
            .join(EventType, Event.type_id == EventType.type_id)
            .where(EventType.name == category_name, Venue.city.in_(user_regions))
            .order_by(Venue.city)
        )
        return result.scalars().all()


async def get_grouped_events_by_city_and_category(city: str, category: str):
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
            .join(EventType, Event.type_id == EventType.type_id)
            .outerjoin(EventLink, Event.event_id == EventLink.event_id)
            .where(Venue.city == city, EventType.name == category)
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
                Event.date_start == None
            )
        ).options(selectinload(Event.venue), selectinload(Event.links))

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
            .where(Subscription.item_name == artist_name)
        )
        return subscribers_result.scalars().all()
    

async def get_or_create(session, model, **kwargs):
    instance = await session.execute(select(model).filter_by(**kwargs))
    instance = instance.scalar_one_or_none()
    if instance:
        print(f"DEBUG: {model.__name__} с параметрами {kwargs} НАЙДЕН. INSERT не будет.") # Добавил для отладки
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        await session.flush()
        print(f"DEBUG: {model.__name__} с параметрами {kwargs} СОЗДАН. Ожидаем INSERT после commit.")
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

            # 1. Работа с типом события
            event_type_obj = await get_or_create(session, EventType, name=event["event_type"])
            
            # 2. Извлечение города и работа с местом проведения
            city = extract_city_from_place(event['place'])
            venue = await get_or_create(session, Venue, name=event['place'], city=city,
                                        country_id=event["country"])

            # 3. Работа с артистом
            artist = await get_or_create(session, Artist, name=event['event_title'])

            # 4. Обработка времени начала события
            start_datetime = None
            if event.get('timestamp'):
                try:
                    start_datetime = datetime.fromtimestamp(event['timestamp'])
                except (ValueError, TypeError):
                    start_datetime = None

            # 5. Подготовка данных для нового события
            new_event_data = {
                "title": event['event_title'],
                "description": event['time'], # Здесь используется "time" для описания, возможно, это опечатка?
                "type_id": event_type_obj.type_id,
                "venue_id": venue.venue_id,
                "date_start": start_datetime,
                "price_min": event.get('price_min'),
                "price_max": event.get('price_max')
            }
            
            # 6. Создание (или получение) самого события
            new_event = await get_or_create(session, Event, **new_event_data)
            
            # 7. Связывание события с артистом
            event_artist_link = {"event_id": new_event.event_id, "artist_id": artist.artist_id} # Используем event_id и artist_id
            await get_or_create(session, EventArtist, **event_artist_link)
            
            # 8. Добавление ссылки на событие
            event_url_link = {"event_id": new_event.event_id, "url": event['link'], "type": "bilety"} # Используем event_id
            await get_or_create(session, EventLink, **event_url_link)

            # 9. Сохранение всех изменений
            await session.commit()
        except Exception as e:
            print("Ошибка при добавление ивента в бд")