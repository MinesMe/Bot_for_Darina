# app/database/requests.py

from sqlalchemy import select, delete, and_, or_, func, distinct, union
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from thefuzz import process as fuzzy_process, fuzz
from datetime import datetime

from .models import async_session, User, Subscription, Event, Artist, Venue, EventLink, EventType, EventArtist, Country, \
    City, MobilityTemplate

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
                "home_country": prefs.home_country ,
                "home_city": prefs.home_city,
                "preferred_event_types": prefs.preferred_event_types
            }
        return None


# --- ФУНКЦИИ ДЛЯ МОБИЛЬНОСТИ ---
async def check_main_geo_status(user_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(select(User.main_geo_completed).where(User.user_id == user_id))
        return result.scalar_one_or_none() or False


async def set_main_geo_completed(user_id: int):
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.main_geo_completed = True
            await session.commit()


async def get_user_mobility_templates(user_id: int) -> list[MobilityTemplate]:
    async with async_session() as session:
        result = await session.execute(
            select(MobilityTemplate).where(MobilityTemplate.user_id == user_id).order_by(MobilityTemplate.template_name)
        )
        return result.scalars().all()


async def create_mobility_template(user_id: int, template_name: str, regions: list):
    async with async_session() as session:
        new_template = MobilityTemplate(user_id=user_id, template_name=template_name, regions=regions)
        session.add(new_template)
        await session.commit()


async def delete_mobility_template(template_id: int):
    """Удаляет шаблон мобильности и отвязывает его от всех подписок."""
    async with async_session() as session:
        # Сначала отвязываем шаблон от всех подписок, которые его используют
        # Это необязательно, если в модели стоит ondelete="SET NULL", но так надежнее
        await session.execute(
            select(Subscription)
            .where(Subscription.template_id == template_id)
        ).update({"template_id": None})

        # Затем удаляем сам шаблон
        await session.execute(
            delete(MobilityTemplate).where(MobilityTemplate.template_id == template_id)
        )
        await session.commit()


# --- ФУНКЦИИ ДЛЯ ПОДПИСОК ---
async def get_user_subscriptions(user_id: int) -> list:
    async with async_session() as session:
        result = await session.execute(
            select(Subscription.item_name).where(Subscription.user_id == user_id).order_by(Subscription.item_name))
        return result.scalars().all()


async def add_subscription(user_id: int, item_name: str, category: str, template_id: int = None,
                           custom_regions: list = None):
    async with async_session() as session:
        user_result = await session.execute(select(User).where(User.user_id == user_id))
        if not user_result.scalar_one_or_none():
            await get_or_create_user(session, user_id)

        existing_sub = await session.execute(
            select(Subscription).where(and_(Subscription.user_id == user_id, Subscription.item_name == item_name)))
        if not existing_sub.scalar_one_or_none():
            new_sub = Subscription(
                user_id=user_id,
                item_name=item_name,
                category=category,
                template_id=template_id,
                custom_regions=custom_regions
            )
            session.add(new_sub)
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
            regions_to_check = []
            if sub.template_id:
                template = await session.get(MobilityTemplate, sub.template_id)
                if template:
                    regions_to_check = template.regions
            else:
                regions_to_check = sub.custom_regions or []

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

            # 1. Работа с типом события
            event_type_obj = await get_or_create(session, EventType, name=event["event_type"])
            
            # 2. Извлечение города и работа с местом проведения
            city = extract_city_from_place(event['place'])
            venue = await get_or_create(session, Venue, name=event['place'], city_id=2,
                                        country_id=1)

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
            print("Ошибка при добавление ивента в бд: ")
            print(e)


async def get_subscribers_for_event_title(event_title: str) -> list[int]:
    async with async_session() as session: # Открываем асинхронную сессию
        
        stmt = select(Subscription.user_id).where(
            Subscription.item_name == event_title
        ).distinct() # Добавляем distinct() для уникальных ID

        # Выполняем запрос
        result = await session.execute(stmt)
        
        # Получаем все результаты. scalar_all() извлекает значения из первого столбца (user_id).
        user_ids = result.scalars().all()
        
        return list(user_ids) # Возвращаем список user_id