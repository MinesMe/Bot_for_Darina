from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey,
    TIMESTAMP, DECIMAL, Table, func, select, distinct
)

DATABASE_URL = "postgresql+asyncpg://postgres:23923@localhost:5432/postgres"

# Создание движка
engine = create_async_engine(DATABASE_URL, echo=True)

# Сессия
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Базовая модель
Base = declarative_base()

# ---------------- Таблицы ----------------

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=False)
    username = Column(String(50), nullable=True)

    subscription = relationship("UserSubscription", back_populates="user")

class UserSubscription(Base):
    __tablename__ = "users_subscription"

    sub_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String(100))

    user = relationship("User", back_populates="subscription")

class Country(Base):
    __tablename__ = "countries"

    country_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    venues = relationship("Venue", back_populates="country")


class EventType(Base):
    __tablename__ = "event_types"

    type_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    events = relationship("Event", back_populates="event_type")


class Artist(Base):
    __tablename__ = "artists"

    artist_id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    events = relationship("EventArtist", back_populates="artist")


class Venue(Base):
    __tablename__ = "venues"

    venue_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.country_id"), nullable=False)
    city = Column(String(50), nullable=False)

    country = relationship("Country", back_populates="venues")
    events = relationship("Event", back_populates="venue")


class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    type_id = Column(Integer, ForeignKey("event_types.type_id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"), nullable=False)
    date_start = Column(TIMESTAMP, nullable=False)
    date_end = Column(TIMESTAMP)
    price_min = Column(DECIMAL(10, 2))
    price_max = Column(DECIMAL(10, 2))
    # is_online удалено по твоему запросу

    event_type = relationship("EventType", back_populates="events")
    venue = relationship("Venue", back_populates="events")
    artists = relationship("EventArtist", back_populates="event")
    links = relationship("EventLink", back_populates="event", cascade="all, delete")


class EventArtist(Base):
    __tablename__ = "event_artists"

    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), primary_key=True)
    artist_id = Column(Integer, ForeignKey("artists.artist_id"), primary_key=True)

    event = relationship("Event", back_populates="artists")
    artist = relationship("Artist", back_populates="events")


class EventLink(Base):
    __tablename__ = "event_links"

    link_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    url = Column(String(512), nullable=False)
    type = Column(String(50))  # произвольная строка

    event = relationship("Event", back_populates="links")



class EventLinkIn(BaseModel):
    url: HttpUrl
    type: Optional[str]

class EventIn(BaseModel):
    title: str
    description: Optional[str]
    event_type: str                # Название типа мероприятия, например "Концерт"
    venue_name: str
    city: str
    country_name: str
    date_start: datetime
    date_end: Optional[datetime]
    price_min: Optional[float]
    price_max: Optional[float]
    artists: List[str]             # Список имён артистов, например ["The Weeknd", "Баста"]
    links: Optional[List[EventLinkIn]] = []

class usertest(BaseModel):
    idd: int
    username: str

class sub(BaseModel):
    user_id: int
    name: str

# Создаём приложение
app = FastAPI()

def get_all_events_query():
    stmt = (
        select(
            Event.event_id,
            Event.title,
            Event.description,
            EventType.name.label("event_type"),
            Venue.name.label("venue"),
            Venue.city,
            Country.name.label("country"),
            Event.date_start,
            Event.price_min,
            Event.price_max,
            func.json_agg(
                func.json_build_object("url", EventLink.url, "type", EventLink.type)
            ).filter(EventLink.url != None).label("links"),  # фильтр убирает null-ссылки
            func.array_agg(distinct(Artist.name)).label("artists")  # DISTINCT работает на массиве строк
        )
        .select_from(Event)
        .join(EventType, Event.type_id == EventType.type_id)
        .join(Venue, Event.venue_id == Venue.venue_id)
        .join(Country, Venue.country_id == Country.country_id)
        .join(EventArtist, Event.event_id == EventArtist.event_id)
        .join(Artist, EventArtist.artist_id == Artist.artist_id)
        .outerjoin(EventLink, Event.event_id == EventLink.event_id)
        .group_by(
            Event.event_id,
            Event.title,
            Event.description,
            EventType.name,
            Venue.name,
            Venue.city,
            Country.name,
            Event.date_start,
            Event.price_min,
            Event.price_max
        )
       
    )

    return stmt



# ТУТ СМОТРЕТЬ ПРИМЕРЫ ЗАПРОСОВ


# Функция для создания таблиц
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Зависимость для сессии
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@app.post("/Addusers")
async def create_user(user: usertest, session: AsyncSession = Depends(get_session)):
    async with session.begin():
        
        userbd = await session.scalar(
            select(User).where(User.user_id == user.idd)
        )
        if not userbd:
            session.add(User(user_id=user.idd, username=user.username))

@app.post("/addSubscription")
async def add_sub(sub: sub, session: AsyncSession = Depends(get_session)):
    async with session.begin():
        session.add(UserSubscription(user_id=sub.user_id, name=sub.name))

@app.get('/subs')
async def get_subs(session: AsyncSession = Depends(get_session)):
    async with session.begin():
        query = (
            select(
                User.username,
                func.array_agg(distinct(UserSubscription.name)).label("Subs")
            )
            .join(UserSubscription, UserSubscription.user_id == User.user_id)
            .group_by(
                User.username
            )
            .where(User.user_id == 23923)
        )
        result = await session.execute(query)

        rows = result.all()
        print(rows)
        events = []
        for r in rows:
            events.append({
                "username": r.username,
                "subs": r.Subs
            })

        return events

@app.post("/events")
async def create_event(event_in: EventIn, session: AsyncSession = Depends(get_session)):
    async with session.begin():  # транзакция, всё или ничего
        # --- Найти или создать тип мероприятия ---
        event_type = await session.scalar(
            select(EventType).where(EventType.name == event_in.event_type)
        )
        if not event_type:
            event_type = EventType(name=event_in.event_type)
            session.add(event_type)
            await session.flush()  # чтобы получить id

        # --- Найти или создать страну ---
        country = await session.scalar(
            select(Country).where(Country.name == event_in.country_name)
        )
        if not country:
            country = Country(name=event_in.country_name)
            session.add(country)
            await session.flush()

        # --- Найти или создать площадку (venue) ---
        venue = await session.scalar(
            select(Venue).where(
                (Venue.name == event_in.venue_name) &
                (Venue.city == event_in.city) &
                (Venue.country_id == country.country_id)
            )
        )
        if not venue:
            venue = Venue(name=event_in.venue_name, city=event_in.city, country_id=country.country_id)
            session.add(venue)
            await session.flush()

        # --- Создать событие ---
        event = Event(
            title=event_in.title,
            description=event_in.description,
            type_id=event_type.type_id,
            venue_id=venue.venue_id,
            date_start=event_in.date_start,
            date_end=event_in.date_end,
            price_min=event_in.price_min,
            price_max=event_in.price_max,
        )
        session.add(event)
        await session.flush()  # чтобы получить event_id

        # --- Найти или создать артистов и связать с событием ---
        for artist_name in event_in.artists:
            artist = await session.scalar(
                select(Artist).where(Artist.name == artist_name)
            )
            if not artist:
                artist = Artist(name=artist_name)
                session.add(artist)
                await session.flush()

            # Связь
            event_artist = EventArtist(event_id=event.event_id, artist_id=artist.artist_id)
            session.add(event_artist)

        # --- Добавить ссылки ---
        for link_in in event_in.links or []:
            link = EventLink(event_id=event.event_id, url=str(link_in.url)  , type=link_in.type)
            session.add(link)

    return {"message": "Event created", "event_id": event.event_id}


@app.post('/Events')
async def get_all_events( session: AsyncSession = Depends(get_session)):
    stmt = get_all_events_query()

    # stmt = stmt.where(
    #     Event.event_id.in_(
    #         select(EventArtist.event_id)
    #         .join(Artist, Artist.artist_id == EventArtist.artist_id)
    #         .where(Artist.name == "Oxxxymiron")
    #     )
    # )

    result = await session.execute(stmt)

    rows = result.all()
    print(rows[0])

    events = []
    for r in rows:
        events.append({
            "event_id": r.event_id,
            "title": r.title,
            "description": r.description,
            "event_type": r.event_type,
            "venue": r.venue,
            "city": r.city,
            "country": r.country,
            "date_start": r.date_start.isoformat() if r.date_start else None,
            "price_min": float(r.price_min) if r.price_min else None,
            "price_max": float(r.price_max) if r.price_max else None,
            "links": r.links,
            "artists": r.artists,
        })

    return events



# Эндпоинт: Добавить страну
@app.post("/countries/")
async def create_country(name: str, session: AsyncSession = Depends(get_session)):
    new_country = Country(name=name)
    session.add(new_country)
    try:
        await session.commit()
        await session.refresh(new_country)
        return {"id": new_country.country_id, "name": new_country.name}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Страна уже существует")


# Эндпоинт: Получить все страны
@app.get("/countries/")
async def get_countries(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Country))
    countries = result.scalars().all()
    return [{"id": c.country_id, "name": c.name} for c in countries]
