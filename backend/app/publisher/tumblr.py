from __future__ import annotations
import pytumblr

from app.publisher.config import Settings


class TumblrError(RuntimeError):
    pass


class TumblrPublisher:
    def __init__(self, settings: Settings):
        self.blog = settings.blog
        self._client = pytumblr.TumblrRestClient(
            settings.consumer_key,
            settings.consumer_secret,
            settings.oauth_token,
            settings.oauth_token_secret,
        )

    def verify(self) -> dict:
        """Confirm the credentials work. Returns the authed user info."""
        info = self._client.info()
        if "user" not in info:
            raise TumblrError(f"tumblr auth failed: {info}")
        return info["user"]

    def post_photo(
        self,
        image_path: str,
        caption: str,
        tags: list[str],
        state: str = "draft",
    ) -> dict:
        resp = self._client.create_photo(
            self.blog,
            state=state,
            tags=tags,
            caption=caption,
            data=image_path,  # local file path; pytumblr uploads it
            format="text",
        )
        return _check(resp)

    def post_photoset(
        self,
        image_paths: list[str],
        caption: str,
        tags: list[str],
        state: str = "draft",
    ) -> dict:
        # A photoset is just create_photo with several local files.
        resp = self._client.create_photo(
            self.blog,
            state=state,
            tags=tags,
            caption=caption,
            data=list(image_paths),
            format="text",
        )
        return _check(resp)


def _check(resp: dict) -> dict:
    # Success returns {"id": <post id>, ...}; errors return meta/errors.
    if not isinstance(resp, dict) or "id" not in resp:
        raise TumblrError(f"tumblr post rejected: {resp}")
    return resp
