from __future__ import annotations

from typing import TYPE_CHECKING

import dectate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .main import App


def match_origin(
    allowed_origin: str | Sequence[str] | None, requested_origin: str | None
) -> str | None:
    """The value of ``Access-Control-Allow-Origin`` for the origin requested.

    A string or ``None`` is used as it is. For a sequence of origins it is
    the requested origin if that is one of them, otherwise ``None``.
    """
    if allowed_origin is None or isinstance(allowed_origin, str):
        return allowed_origin
    if requested_origin in allowed_origin:
        return requested_origin
    return None


class CORSAction(dectate.Action):
    filter_convert = {"model": dectate.convert_dotted_name}
    app_class_arg = True

    def __init__(
        self,
        model: type[object],
        view_name: str = "",
        allowed_origin: str | Sequence[str] | None = None,
        allowed_headers: list[str] | None = None,
        expose_headers: list[str] | None = None,
        allow_credentials: bool | None = None,
        max_age: int | None = None,
    ) -> None:
        self.model = model
        self.view_name = view_name
        self.allowed_origin = allowed_origin
        self.allowed_headers = allowed_headers
        self.expose_headers = expose_headers
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def identifier(self, app_class: type[App]) -> str:
        return str((app_class, self.model, self.view_name))

    def perform(self, obj: object, app_class: type[App]) -> None:
        allowed_origin = self.allowed_origin
        if allowed_origin is not None:
            app_class.get_cors_allowed_origin.register(
                lambda self, model, request, requested_origin: match_origin(
                    allowed_origin, requested_origin
                ),
                model=self.model,
                view_name=self.view_name,
            )

        allowed_headers = self.allowed_headers
        if allowed_headers is not None:
            app_class.get_cors_allowed_headers.register(
                (lambda self, model, request, requested_headers: allowed_headers),
                model=self.model,
                view_name=self.view_name,
            )

        expose_headers = self.expose_headers
        if expose_headers is not None:
            app_class.get_cors_expose_headers.register(
                lambda self, model, request: expose_headers,
                model=self.model,
                view_name=self.view_name,
            )

        allow_credentials = self.allow_credentials

        if allow_credentials is not None:
            app_class.get_cors_allow_credentials.register(
                lambda self, model, request: allow_credentials,
                model=self.model,
                view_name=self.view_name,
            )

        max_age = self.max_age

        if max_age is not None:
            app_class.get_cors_max_age.register(
                lambda self, model, request: max_age,
                model=self.model,
                view_name=self.view_name,
            )
