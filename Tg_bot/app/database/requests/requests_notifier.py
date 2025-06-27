# app/database/requests_notifier.py

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import async_session, Subscription, Event, User

async def get_active_subscriptions_for_notify() -> list[Subscription]:
    """
    Получает все активные подписки и сразу подгружает связанные с ними
    данные о событии и пользователе, чтобы избежать лишних запросов к БД.
    """
    async with async_session() as session:
        stmt = (
            select(Subscription)
            .where(Subscription.status == 'active')
            .options(
                # Подгружаем связанный объект Event
                selectinload(Subscription.event)
                .options(
                    # А для этого Event сразу подгружаем Venue
                    selectinload(Event.venue)
                ),
                # Подгружаем связанный объект User, но только его ID и язык
                selectinload(Subscription.user)
                .load_only(User.user_id, User.language_code)
            )
        )
        result = await session.execute(stmt)
        # unique() нужен, чтобы SQLAlchemy правильно обработал дубликаты из-за join'ов
        return result.scalars().unique().all()

async def deactivate_user_subscriptions(user_id: int):
    """
    Ставит на паузу все подписки пользователя.
    Используется, если пользователь заблокировал бота.
    """
    # Эту функцию можно будет реализовать позже, пока оставим заглушку
    print(f"Пользователь {user_id} заблокировал бота. В будущем здесь будет деактивация подписок.")
    pass