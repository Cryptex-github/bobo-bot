from __future__ import annotations

import os
from io import BufferedIOBase, BytesIO
from typing import Any, Final, NamedTuple, TYPE_CHECKING
from urllib.parse import quote

from aiohttp import ClientResponseError, ClientSession, FormData

from config import cdn_authorization

if TYPE_CHECKING:
    from discord import File
    from core.bot import BoboBot

__all__ = (
    'CDNClient',
    'CDNEntry',
)

BASE_URL: Final[str] = 'https://cdn.bobobot.cf'
HEADERS: Final[dict[str, str]] = {
    'Authorization': f'Bearer {cdn_authorization}',
    'User-Agent': 'BoboBot/0.1',
}


class CDNEntry(NamedTuple):
    filename: str
    directory: str
    path: str
    session: ClientSession | None = None

    @property
    def url(self) -> str:
        return BASE_URL + '/uploads' + self.path

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        return f'<CDNEntry filename={self.filename!r} path={self.path!r}>'

    def with_session(self, session: ClientSession, /) -> CDNEntry:
        return CDNEntry(self.filename, self.directory, self.path, session)

    async def read(self) -> bytes:
        if self.session is None:
            raise RuntimeError('no session attached to this entry')

        async with self.session.get(self.url) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def stream(self) -> BytesIO:
        return BytesIO(await self.read())

    async def delete(self) -> None:
        if self.session is None:
            raise RuntimeError('no session attached to this entry')

        async with self.session.delete(self.url, headers=HEADERS) as resp:
            resp.raise_for_status()


class CDNClient:
    """An interface for requests to Lambda's CDN, cdn.lambdabot.cf."""

    def __init__(self, bot: BoboBot) -> None:
        self._session: ClientSession = (
            bot.session
        )  # set this to an instance of aiohttp.ClientSession

    def partial_entry(self, filename: str, *, directory: str = '/') -> CDNEntry:
        """Create a CDNEntry object from a filename."""
        if directory != '/':
            directory = f'/{directory.strip("/")}/'

        return CDNEntry(filename, directory, directory + filename, self._session)

    async def upload(
        self,
        fp: BufferedIOBase,
        filename: str | None = None,
        *,
        directory: str | None = None,
        raise_on_conflict: bool = False,
    ) -> CDNEntry:
        """Upload a file to the CDN."""
        filename = filename or 'unknown.png'

        form = FormData()
        form.add_field('file', fp, filename=filename)

        params = {}
        if directory is not None:
            params['directory'] = quote(directory)

        if raise_on_conflict:
            params['safe'] = 'true'

        async with self._session.post(
            'https://cdn.lambdabot.cf/upload', data=form, headers=HEADERS, params=params
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

            return CDNEntry(
                filename=data['filename'],
                directory=data['directory'],
                path=data['path'],
                session=self._session,
            )

    async def upload_file(self, file: File, **kwargs: Any) -> CDNEntry:
        """Upload a file to the CDN from a discord.File object."""
        return await self.upload(file.fp, file.filename, **kwargs)

    async def safe_upload(
        self,
        fp: BufferedIOBase,
        extension: str | None = None,
        *,
        directory: str | None = None,
        max_tries: int = 3,
    ) -> CDNEntry | None:
        """Uploads a file to the CDN guaranteeing that the filename is unique."""
        for _ in range(max_tries):
            filename = os.urandom(8).hex() + (f'.{extension}' * (extension is not None))

            try:
                return await self.upload(
                    fp, filename, directory=directory, raise_on_conflict=True
                )
            except ClientResponseError as exc:
                if exc.status != 409:
                    raise

    async def paste(
        self, text: str, *, extension: str = 'txt', directory: str | None = None
    ) -> CDNEntry | None:
        """Upload text to the CDN."""
        return await self.safe_upload(
            BytesIO(text.encode('utf-8')), extension=extension, directory=directory
        )

    async def delete(self, entry: CDNEntry | str) -> None:
        """Deletes a file from the CDN. Entry can be a :class:`CDNEntry` object or a filename."""
        if isinstance(entry, CDNEntry):
            entry = entry.filename

        entry = entry.removeprefix(BASE_URL + '/uploads/')

        async with self._session.delete(
            f'{BASE_URL}/uploads/{entry}', headers=HEADERS
        ) as resp:
            resp.raise_for_status()
