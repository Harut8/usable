import functools
import logging
from contextlib import asynccontextmanager
from typing import Callable, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.postgres import PgAsyncSQLAlchemyAdapter
from adapters.repository import BaseRepository

REPO = TypeVar("REPO", bound=BaseRepository)


class PgSQLAlchemyUnitOfWork:
    def __init__(
        self, sqlalchemy_adapter: PgAsyncSQLAlchemyAdapter, repositories: dict[str, REPO], logger: logging.Logger
    ) -> None:
        self._sqlalchemy_adapter = sqlalchemy_adapter
        self._repositories = repositories
        self._session = None
        self._logger = logger

    async def __aenter__(self):
        self.session = self.sqlalchemy_adapter.async_scoped_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
            return
        await self.session.commit()


    @property
    def session(self) -> AsyncSession:
        return self._session

    @session.setter
    def session(self, session: AsyncSession):
        self._session = session

    @property
    def sqlalchemy_adapter(self) -> PgAsyncSQLAlchemyAdapter:
        return self._sqlalchemy_adapter

    @asynccontextmanager
    async def atomic(self, read_only: bool = False) -> AsyncSession:
        async with self.sqlalchemy_adapter.async_scoped_session() as _session:
            try:
                self.session = _session
                if self._logger:
                    self._logger.debug(f"Session status: {_session.bind.pool.status()} at start")
                yield _session
                if not read_only:
                    await _session.commit()
            except Exception as e:
                await self._session.rollback()
                raise e
            if self._logger:
                self._logger.debug(f"Session status: {_session.bind.pool.status()} at end")

    @asynccontextmanager
    async def atomic_concurrent(self) -> AsyncSession:
        async with self.sqlalchemy_adapter.engine.begin() as _conn:
            async with self.sqlalchemy_adapter.session_factory() as _session:
                try:
                    async with _session.begin():
                        self.session = _session
                        if self._logger:
                            self._logger.debug(f"Session status: {_session.bind.pool.status()} at start")
                        yield _session
                except Exception as e:
                    await self._session.rollback()
                    raise e
                if self._logger:
                    self._logger.debug(f"Session status: {_session.bind.pool.status()} at end")

    async def dispose_uow(self):
        await self._session.close()
        await self._sqlalchemy_adapter.dispose()

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()

    def get_repository(self, repository: Type[REPO]) -> REPO:
        _founded_repo_class: Type[REPO] = self._repositories.get(repository.__name__)
        _repo = _founded_repo_class(self._session)
        return _repo
