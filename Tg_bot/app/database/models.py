import asyncio
import os
from dotenv import load_dotenv

from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey,
    TIMESTAMP, DECIMAL, BigInteger, JSON, text
)
import json    # Для работы с JSON-данными, которые приходят из БД
from sqlalchemy.pool import NullPool # Очень важный импорт для слушателя!

load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS]):
    raise KeyError("Не все переменные окружения для базы данных определены в .env файле")

SQL_ALCHEMY = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(url=SQL_ALCHEMY)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Country(Base):
    __tablename__ = "countries"
    country_id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    venues = relationship("Venue", back_populates="country")

class EventType(Base):
    __tablename__ = "event_types"
    type_id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    events = relationship("Event", back_populates="event_type")

class Artist(Base):
    __tablename__ = "artists"
    artist_id = Column(Integer, primary_key=True)
    name = Column(String(500), unique=True, nullable=False)
    events = relationship("EventArtist", back_populates="artist")

class Venue(Base):
    __tablename__ = "venues"
    venue_id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.country_id"), nullable=False)
    city = Column(String(255), nullable=False)
    country = relationship("Country", back_populates="venues")
    events = relationship("Event", back_populates="venue")

class Event(Base):
    __tablename__ = "events"
    event_id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    type_id = Column(Integer, ForeignKey("event_types.type_id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"), nullable=False)
    date_start = Column(TIMESTAMP, nullable=True)
    date_end = Column(TIMESTAMP)
    price_min = Column(DECIMAL(10, 2))
    price_max = Column(DECIMAL(10, 2))
    event_type = relationship("EventType", back_populates="events")
    venue = relationship("Venue", back_populates="events")
    artists = relationship("EventArtist", back_populates="event")
    links = relationship("EventLink", back_populates="event", cascade="all, delete")

class EventArtist(Base):
    __tablename__ = "event_artists"
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), primary_key=True)
    artist_id = Column(Integer, ForeignKey("artists.artist_id", ondelete="CASCADE"), primary_key=True)
    event = relationship("Event", back_populates="artists")
    artist = relationship("Artist", back_populates="events")

class EventLink(Base):
    __tablename__ = "event_links"
    link_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    url = Column(String(1024), nullable=False)
    type = Column(String(50))
    event = relationship("Event", back_populates="links")

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    regions = Column(JSON, nullable=True)

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'))
    item_name = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)



SQL_CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_new_event()
RETURNS TRIGGER AS $$
DECLARE
    payload JSONB;
BEGIN
    -- Собираем вложенные данные об ивенте, типе, площадке и стране
    SELECT jsonb_build_object(
        'event_id', e.event_id,
        'title', e.title,
        'description', e.description,
        'date_start', e.date_start,
        'date_end', e.date_end,
        'price_min', e.price_min,
        'price_max', e.price_max,
        'event_type', jsonb_build_object(
            'name', et.name
        ),
        'venue', jsonb_build_object(
            'name', v.name,
            'city', v.city
        ),
        'country', jsonb_build_object(
            'name', c.name
        )
    )
    INTO payload
    FROM events e
    JOIN event_types et ON e.type_id = et.type_id
    JOIN venues v ON e.venue_id = v.venue_id
    JOIN countries c ON v.country_id = c.country_id
    WHERE e.event_id = NEW.event_id;

    -- Добавляем данные об артисте
    payload := jsonb_set(
        payload,
        '{artist}',
        (
            SELECT to_jsonb(a)
            FROM artists a
            WHERE a.artist_id = NEW.artist_id
        )
    );

    -- Отправляем JSON через канал
    PERFORM pg_notify('new_event_channel', payload::text);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

SQL_CREATE_TRIGGER = """
CREATE TRIGGER new_event_trigger
AFTER INSERT ON event_artists
FOR EACH ROW
EXECUTE FUNCTION notify_new_event();
"""



listener_engine = create_async_engine(url=SQL_ALCHEMY, poolclass=NullPool)

async def listen_for_db_notifications():
    print("📡 Функция listen_for_db_notifications() была вызвана.")

    try:
        async with listener_engine.connect() as conn:  # это AsyncConnection
            # Получаем "сырое" соединение из SQLAlchemy
            raw_connection = await conn.get_raw_connection()

            # Получаем настоящее asyncpg соединение
            asyncpg_conn = raw_connection.driver_connection

            # Подписываемся на канал
            await asyncpg_conn.add_listener("new_event_channel", notification_handler)

            print("✅ Подписка на канал 'new_event_channel' выполнена. Слушаю уведомления...")

            while True:
                await asyncio.sleep(1)  # Нужно, чтобы задача не завершалась
    except Exception as e:
        print(f"[ОШИБКА] В слушателе БД: {e}")


def notification_handler(connection, pid, channel, payload):
    print("\n--- Новые данные поступили в БД! ---")
    print(f"Канал: {channel}")
    print(f"PID отправителя: {pid}")
    print(f"Сообщение: {payload}")
    print("---------------------------")




async def async_main():
    print("Инициализация базы данных: проверка и создание таблиц...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы успешно созданы или уже существуют.")

    print("Проверка и создание функции-триггера и триггера для 'events'...")
    async with engine.connect() as conn:
        # Выполняем SQL-код для создания функции-триггера
        await conn.execute(text("DROP TRIGGER IF EXISTS new_event_trigger ON event_artists;"))
        await conn.execute(text(SQL_CREATE_TRIGGER_FUNCTION))
        # Выполняем SQL-код для создания самого триггера
        await conn.execute(text(SQL_CREATE_TRIGGER))
        await conn.commit() # Важно зафиксировать изменения

    print("Функция-триггер и триггер успешно созданы или обновлены.")