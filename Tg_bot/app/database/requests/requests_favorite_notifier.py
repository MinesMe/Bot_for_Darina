from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import async_session, UserFavorite, Artist, User

async def get_favorite_subscribers_by_artist(artist_id: int) -> list[UserFavorite]:
    """
    Находит все записи UserFavorite для данного артиста.
    Сразу подгружает связанные объекты User для отправки сообщений
    и Artist для получения имени.
    """
    async with async_session() as session:
        stmt = (
            select(UserFavorite)
            .where(UserFavorite.artist_id == artist_id)
            .options(
                selectinload(UserFavorite.user).load_only(User.user_id, User.language_code),
                selectinload(UserFavorite.artist).load_only(Artist.name)
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()