from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.database.models import Artist, Event, Venue, Country, City, EventArtist

def get_concert_recommendations_query(db: Session, country_name: str, target_date: datetime):
    """
    Выполняет запрос для получения рекомендаций по концертам.
    """
    start_date = target_date - timedelta(days=4)
    end_date = target_date + timedelta(days=4)

    results = db.query(
        Artist.name.label('artist_name'),
        Country.name.label('country_name'),
        City.name.label('city_name'),
        Event.date_start.label('event_date')
    ).join(EventArtist, Artist.artist_id == EventArtist.artist_id) \
     .join(Event, EventArtist.event_id == Event.event_id) \
     .join(Venue, Event.venue_id == Venue.venue_id) \
     .join(Country, Venue.country_id == Country.country_id) \
     .join(City, Venue.city_id == City.city_id) \
     .filter(Country.name == country_name) \
     .filter(Event.date_start.between(start_date, end_date)) \
     .distinct() \
     .all()

    # Преобразуем результаты в список словарей
    output = []
    for row in results:
        row_dict = row._asdict() # Преобразуем Row в dict
        # SQLAlchemy уже возвращает даты как объекты datetime, можно просто .date()
        if 'event_date' in row_dict and isinstance(row_dict['event_date'], datetime):
            row_dict['event_date'] = row_dict['event_date'].date()
        output.append(row_dict)
    return output

def get_local_event_recommendations_query(db: Session, home_country_name: str):
    """
    Выполняет запрос для получения предстоящих мероприятий в стране проживания.
    """
    today = datetime.now().date()
    ten_days_from_now = today + timedelta(days=10)

    results = db.query(
        Artist.name.label('artist_name'),
        Country.name.label('country_name'),
        City.name.label('city_name'),
        Event.date_start.label('event_date')
    ).join(EventArtist, Artist.artist_id == EventArtist.artist_id) \
     .join(Event, EventArtist.event_id == Event.event_id) \
     .join(Venue, Event.venue_id == Venue.venue_id) \
     .join(Country, Venue.country_id == Country.country_id) \
     .join(City, Venue.city_id == City.city_id) \
     .filter(Country.name == home_country_name) \
     .filter(Event.date_start.between(today, ten_days_from_now)) \
     .distinct() \
     .all()

    output = []
    for row in results:
        row_dict = row._asdict()
        if 'event_date' in row_dict and isinstance(row_dict['event_date'], datetime):
            row_dict['event_date'] = row_dict['event_date'].date()
        output.append(row_dict)
    return output