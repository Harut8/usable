import functools
from contextlib import asynccontextmanager
from typing import Type, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.postgres import AsyncSQLAlchemyAdapter
from adapters.repository import BaseRepository

REPO = TypeVar("REPO", bound=BaseRepository)


class SQLAlchemyUnitOfWork:
    def __init__(self,
                 sqlalchemy_adapter: AsyncSQLAlchemyAdapter,
                 repositories: set[REPO],
                 log: bool = False) -> None:
        self._sqlalchemy_adapter = sqlalchemy_adapter
        self._repositories = repositories
        self._session = None
        self._log = log

    @property
    def session(self) -> AsyncSession:
        return self._session

    @session.setter
    def session(self, session: AsyncSession):
        self._session = session

    @property
    def sqlalchemy_adapter(self) -> AsyncSQLAlchemyAdapter:
        return self._sqlalchemy_adapter

    @asynccontextmanager
    async def atomic(self, read_only: bool = False) -> AsyncSession:
        async with self.sqlalchemy_adapter.async_scoped_session() as _session:
            try:
                self.session = _session
                if self._log:
                    print(_session.bind.pool.status(), "AT START")
                yield _session
                if not read_only:
                    await _session.commit()
            except Exception as e:
                await _session.rollback()
                raise e
            finally:
                await _session.close()
            if self._log:
                print(_session.bind.pool.status(), "AT END")

    def transactional(self):

        def wrapper(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper_func(*args, **kwargs):
                async with self.atomic():
                    return await func(*args, **kwargs)

            return wrapper_func

        return wrapper

    async def dispose_uow(self):
        await self._session.close()
        await self._sqlalchemy_adapter.dispose()

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()

    def get_repository(self, repository: Type[REPO]) -> REPO:
        _founded_repo = None
        for _repo in self._repositories:
            if _repo.name == repository.__name__:
                _founded_repo = _repo
                break
        _founded_repo.session = self._session
        return _founded_repo
