# app/database/models.py

import os
from dotenv import load_dotenv

from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy import (
    Column, Integer, NullPool, String, Text, ForeignKey, TIMESTAMP, DECIMAL, BigInteger,
    JSON, Boolean, text, Enum, inspect
)

# --- Настройка подключения (без изменений) ---
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

# --- Существующие таблицы (остаются без изменений) ---
class Country(Base):
    __tablename__ = "countries"
    country_id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    cities = relationship("City", back_populates="country")
    venues = relationship("Venue", back_populates="country")

class City(Base):
    __tablename__ = "cities"
    city_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.country_id"), nullable=False)
    country = relationship("Country", back_populates="cities")
    venues = relationship("Venue", back_populates="city")

class EventType(Base):
    __tablename__ = "event_types"
    type_id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    events = relationship("Event", back_populates="event_type")

# --- ИЗМЕНЕНИЕ 1: Artist становится нашей сущностью "Объект интереса" ---
# Мы не будем создавать новую таблицу, а будем считать, что "Artist" может быть
# не только музыкантом, но и фестивалем, чемпионатом и т.д.
class Artist(Base):
    __tablename__ = "artists"
    artist_id = Column(Integer, primary_key=True)
    name = Column(String(500), unique=True, nullable=False)
    # Эта связь показывает, в каких событиях участвует "артист"
    events = relationship("EventArtist", back_populates="artist")
    # НОВАЯ СВЯЗЬ: Пользователи, добавившие этого "артиста" в "Избранное"
    user_associations = relationship("UserFavorite", back_populates="artist", cascade="all, delete-orphan")
    # --- ДОБАВЬТЕ ЭТОТ МЕТОД ---
    def to_dict(self):
        return {
            'artist_id': self.artist_id,
            'name': self.name
        }

class Venue(Base):
    __tablename__ = "venues"
    # ... (без изменений)
    venue_id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    country_id = Column(Integer, ForeignKey("countries.country_id"), nullable=False)
    city_id = Column(Integer, ForeignKey("cities.city_id"), nullable=False)
    country = relationship("Country", back_populates="venues")
    city = relationship("City", back_populates="venues")
    events = relationship("Event", back_populates="venue")

class Event(Base):
    __tablename__ = "events"
    # ... (добавляем поле для обновлений от парсера)
    event_id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    type_id = Column(Integer, ForeignKey("event_types.type_id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.venue_id"), nullable=False)
    date_start = Column(TIMESTAMP, nullable=True)
    date_end = Column(TIMESTAMP)
    price_min = Column(DECIMAL(10, 2))
    price_max = Column(DECIMAL(10, 2))
    # НОВОЕ ПОЛЕ: для хранения информации о билетах (например, "Осталось мало", "Sold Out")
    tickets_info = Column(String(255), nullable=True)
    # Связи
    event_type = relationship("EventType", back_populates="events")
    venue = relationship("Venue", back_populates="events")
    artists = relationship("EventArtist", back_populates="event")
    links = relationship("EventLink", back_populates="event", cascade="all, delete-orphan")

    subscriptions = relationship("Subscription", back_populates="event", cascade="all, delete-orphan")

class EventArtist(Base):
    __tablename__ = "event_artists"
    # ... (без изменений)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), primary_key=True)
    artist_id = Column(Integer, ForeignKey("artists.artist_id", ondelete="CASCADE"), primary_key=True)
    event = relationship("Event", back_populates="artists")
    artist = relationship("Artist", back_populates="events")

class EventLink(Base):
    __tablename__ = "event_links"
    # ... (без изменений)
    link_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    url = Column(String(1024), nullable=False)
    type = Column(String(50))
    event = relationship("Event", back_populates="links")

class User(Base):
    __tablename__ = 'users'
    # ... (добавляем связь с "Избранным")
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    language_code = Column(String(10), nullable=True)
    home_country = Column(String(255), nullable=True)
    home_city = Column(String(255), nullable=True)
    preferred_event_types = Column(JSON, nullable=True)
    main_geo_completed = Column(Boolean, default=False, nullable=False)
    general_geo_completed = Column(Boolean, default=False, nullable=False)
    general_mobility_regions = Column(JSON, nullable=True)
    # НОВАЯ СВЯЗЬ: "Избранные" артисты/объекты интереса
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")

# --- ИЗМЕНЕНИЕ 2: Таблица Subscription теперь для КОНКРЕТНЫХ СОБЫТИЙ ---
# Мы полностью меняем назначение этой таблицы.
class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    # Связь с конкретным событием, а не с именем
    event_id = Column(Integer, ForeignKey('events.event_id', ondelete='CASCADE'), nullable=False)
    # Статус для реализации паузы
    status = Column(Enum('active', 'paused', name='subscription_status_enum'), default='active', nullable=False)
    # Поле для "Турбо-режима" на будущее
    is_turbo = Column(Boolean, default=False, nullable=False)
    # Причина удаления (опционально, для аналитики)
    deletion_reason = Column(Text, nullable=True)

    event = relationship("Event", back_populates="subscriptions")
    user = relationship("User")

# --- ИЗМЕНЕНИЕ 3: НОВАЯ таблица для "Избранного" (многие-ко-многим) ---
# Эта таблица связывает Пользователей и их "Объекты интереса" (Артистов)
class UserFavorite(Base):
    __tablename__ = 'user_favorites'
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    artist_id = Column(Integer, ForeignKey('artists.artist_id', ondelete='CASCADE'), primary_key=True)
    regions = Column(JSON, nullable=False)
    
    # Добавляем связи для удобства (опционально, но полезно)
    user = relationship("User", back_populates="favorites")
    artist = relationship("Artist", back_populates="user_associations")


SQL_CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_new_event()
RETURNS TRIGGER AS $$
DECLARE
    payload JSONB;
BEGIN
    -- Собираем вложенные данные
    SELECT jsonb_build_object(
        'event_id', e.event_id,
        'title', e.title,
        'description', e.description,
        'date_start', e.date_start,
        'venue', jsonb_build_object(
            'name', v.name,
            -- ИЗМЕНЕНИЕ: Добавляем имя города
            'city_name', cities.name 
        ),
        'country', jsonb_build_object(
            'name', c.name
        )
    )
    INTO payload
    FROM events e
    JOIN venues v ON e.venue_id = v.venue_id
    JOIN cities cities ON v.city_id = cities.city_id
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





# --- НОВЫЙ КОД: Триггер для добавления в "Избранное" ---
SQL_CREATE_FAVORITE_NOTIFY_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_new_user_favorite()
RETURNS TRIGGER AS $$
DECLARE
    payload JSONB;
    artist_name_var TEXT;
BEGIN
    -- Получаем имя артиста по его ID из вставленной строки (NEW.artist_id)
    SELECT name INTO artist_name_var
    FROM artists
    WHERE artist_id = NEW.artist_id;

    -- Собираем JSON-объект с необходимой информацией
    payload := jsonb_build_object(
        'user_id', NEW.user_id,
        'artist_id', NEW.artist_id,
        'artist_name', artist_name_var
    );

    -- Отправляем уведомление в наш новый, выделенный канал
    PERFORM pg_notify('user_favorite_added_channel', payload::text);

    -- Возвращаем NEW, что является стандартной практикой для AFTER-триггеров
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

SQL_CREATE_FAVORITE_TRIGGER = """
CREATE TRIGGER user_favorite_insert_trigger
AFTER INSERT ON user_favorites
FOR EACH ROW
EXECUTE FUNCTION notify_new_user_favorite();
"""
# --- КОНЕЦ НОВОГО КОДА ---



listener_engine = create_async_engine(url=SQL_ALCHEMY, poolclass=NullPool)





# Вставьте этот код вместо вашей текущей функции async_main

async def async_main():
    print("Инициализация базы данных: проверка и создание таблиц...")
    # Шаг 1: Создание/проверка таблиц. Этот блок у вас был правильным.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы успешно созданы или уже существуют.")

    # Шаг 2: Создание/обновление функций и триггеров в одной атомарной транзакции.
    print("\nПроверка и создание функций и триггеров...")
    try:
        # ## Правильный способ: используем engine.begin() для управления транзакцией ##
        async with engine.connect() as conn:
            print(" -> Транзакция для создания триггеров начата.")
            await conn.execute(text("DROP TRIGGER IF EXISTS new_event_trigger ON event_artists;"))
            # --- Триггер для событий ---
            print("-> Обновление триггера для 'events'...")
            await conn.execute(text(SQL_CREATE_TRIGGER_FUNCTION))
            await conn.execute(text(SQL_CREATE_TRIGGER))
            print("-> Триггер для 'events' успешно обновлен.")

            # --- Триггер для избранного ---
            print("      -> Обновление триггера для 'user_favorites'...")
            await conn.execute(text("DROP TRIGGER IF EXISTS user_favorite_insert_trigger ON user_favorites;"))
            await conn.execute(text("DROP FUNCTION IF EXISTS notify_new_user_favorite();"))
            await conn.execute(text(SQL_CREATE_FAVORITE_NOTIFY_FUNCTION))
            await conn.execute(text(SQL_CREATE_FAVORITE_TRIGGER))
            print("      -> Триггер для 'user_favorites' успешно обновлен.")
        
        # COMMIT будет вызван здесь автоматически при выходе из блока "with"
        print("✅ Транзакция успешно завершена. Все объекты в БД обновлены.")

    except Exception as e:
        # ROLLBACK будет вызван здесь автоматически, если в блоке "with" произойдет ошибка
        print(f"❌ Произошла ошибка во время транзакции, все изменения отменены: {e}")