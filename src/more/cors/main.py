from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, cast

from webob.exc import HTTPUnauthorized

import dectate
import morepath
import reg
from morepath.publish import get_view_name, resolve_model

from . import action

if TYPE_CHECKING:
    from collections.abc import Sequence

    from webob.response import Response

    from morepath.request import Request
    from morepath.types import Tween


logger = logging.getLogger(__name__)


# the combinations that have been reported, to do that once
_reported: set[tuple[type[object], str | None]] = set()


def _warn_wildcard_credentials(model: type[object], view_name: str | None) -> None:
    """Log that the wildcard origin is combined with credentials, once."""
    if (model, view_name) in _reported:
        return
    _reported.add((model, view_name))
    logger.warning(
        "more.cors: allow_credentials is set but allowed_origin is '*' for "
        "%s (view %r). Browsers reject this for requests with credentials. "
        "Set an explicit allowed_origin, or a list of origins.",
        model.__qualname__,
        view_name,
    )


class _CORSSettings(Protocol):
    """The settings in the ``cors`` section, see ``cors_settings`` below."""

    allowed_verbs: list[str]
    allowed_origin: str | Sequence[str] | None
    expose_headers: list[str]
    allowed_headers: list[str]
    max_age: int
    allow_credentials: bool


def _view_name(*, request: Request[Any], **kwargs: object) -> str | None:
    """Dispatch key of the ``get_cors_*`` methods: the name of the view.

    Reg calls this with the arguments of the dispatch method, as keyword
    arguments.
    """
    return request.view_name


class App(morepath.App):
    _cors = dectate.directive(action.CORSAction)

    @classmethod
    def cors(
        cls,
        model: type[object],
        view_name: str = "",
        allowed_origin: str | Sequence[str] | None = None,
        allowed_headers: list[str] | None = None,
        expose_headers: list[str] | None = None,
        allow_credentials: bool | None = None,
        max_age: int | None = None,
    ) -> None:
        cls._cors(
            model,
            view_name,
            allowed_origin,
            allowed_headers,
            expose_headers,
            allow_credentials,
            max_age,
        )(None)

    @property
    def _cors_settings(self) -> _CORSSettings:
        return cast("_CORSSettings", self.settings.cors)

    @reg.dispatch_method(
        reg.match_instance("model"),
        reg.match_key("view_name", _view_name),
    )
    def get_cors_allowed_origin(
        self,
        model: object | None,
        request: Request[Any],
        requested_origin: str | None,
    ) -> str | None:
        """The value of ``Access-Control-Allow-Origin``.

        The default is the ``allowed_origin`` setting. If that is a list of
        origins, it is ``requested_origin`` if that is in the list and
        otherwise ``None``. ``None`` or an empty string means that the header
        isn't sent at all.

        An implementation returns a single origin, or ``"*"``, never a list.
        """
        return action.match_origin(self._cors_settings.allowed_origin, requested_origin)

    @reg.dispatch_method(
        reg.match_instance("model"),
        reg.match_key("view_name", _view_name),
    )
    def get_cors_allowed_methods(
        self,
        model: object | None,
        request: Request[Any],
        requested_method: str | None,
    ) -> list[str]:
        if model is None:
            return self._cors_settings.allowed_verbs
        res: list[str] = []
        for m in self._cors_settings.allowed_verbs:
            f = request.app.get_view.by_predicates(
                model=model.__class__, name=request.view_name, request_method=m
            )
            if f and f.component:
                res.append(m)
        return res

    @reg.dispatch_method(
        reg.match_instance("model"),
        reg.match_key("view_name", _view_name),
    )
    def get_cors_allowed_headers(
        self,
        model: object | None,
        request: Request[Any],
        requested_headers: str | None,
    ) -> list[str]:
        return self._cors_settings.allowed_headers

    @reg.dispatch_method(
        reg.match_instance("model"),
        reg.match_key("view_name", _view_name),
    )
    def get_cors_expose_headers(
        self, model: object | None, request: Request[Any]
    ) -> list[str]:
        return self._cors_settings.expose_headers

    @reg.dispatch_method(
        reg.match_instance("model"),
        reg.match_key("view_name", _view_name),
    )
    def get_cors_allow_credentials(
        self, model: object | None, request: Request[Any]
    ) -> bool:
        return self._cors_settings.allow_credentials

    @reg.dispatch_method(
        reg.match_instance("model"),
        reg.match_key("view_name", _view_name),
    )
    def get_cors_max_age(self, model: object | None, request: Request[Any]) -> int:
        return self._cors_settings.max_age


CORSApp = App


@App.setting_section(section="cors")
def cors_settings() -> dict[str, Any]:
    return {
        "allowed_verbs": ["GET", "PUT", "POST", "PATCH", "DELETE", "OPTIONS"],
        "allowed_origin": "*",
        "expose_headers": ["Content-Type", "Authorization"],
        "allowed_headers": ["Content-Type", "Authorization"],
        "max_age": 60,
        "allow_credentials": False,
    }


def _resolve_context(app: App, request: Request[Any]) -> tuple[object | None, Any]:
    """Find the model that the CORS settings should be looked up for.

    Returns the model the request is addressed to, ``app`` itself if there
    is none, or ``None`` if the model can't be accessed (unauthorized),
    together with the app that owns the model. That is a mounted app if the
    path leads into one.

    As a side effect this sets ``request.view_name``, which the ``get_cors_*``
    methods dispatch on. Otherwise the request is left untouched.
    """
    # Morepath doesn't keep the resolved model on the request, so it can't be
    # taken from there once the request has been handled. Resolving the model
    # consumes the path and calls the path functions, which may have side
    # effects on the request (``request.after`` for example). So do it on a
    # copy, like ``Request.resolve_path`` does, to leave the real request as
    # it is.
    lookup = app.request(request.environ.copy())
    try:
        model = resolve_model(lookup)
    except HTTPUnauthorized:
        return None, app
    except Exception:
        return app, app
    request.view_name = get_view_name(lookup.unconsumed)
    # Don't use ``model or app``: a model may well be falsy, for example
    # an empty collection.
    return (app if model is None else model), lookup.app


@App.tween_factory(over=morepath.EXCVIEW)
def cors_tween(app: App, handler: Tween) -> Tween:
    def cors_handler(request: Request[Any]) -> Response:
        preflight = request.method == "OPTIONS"
        requested_origin = request.headers.get("Origin")

        # Looking up the model costs one more call of its path function, so
        # only do it if a browser is going to apply CORS rules to the response.
        context: object | None
        if preflight or requested_origin:
            context, owner = _resolve_context(app, request)
        else:
            context, owner = app, app

        response: Response
        if preflight:
            response = request.ResponseClass()
            # The handler isn't called, so the request is still in the app
            # it came in. The views are in the app that owns the model.
            request.app = owner
        else:
            response = handler(request)

        # Access-Control-Allow-Methods
        requested_method = request.headers.get("Access-Control-Request-Method")

        if preflight:
            allowed_methods = app.get_cors_allowed_methods(
                context, request, requested_method
            )
            if not allowed_methods:
                return request.ResponseClass(status_code=404)
            response.headers.add(
                "Access-Control-Allow-Methods",
                ",".join(["OPTIONS", *allowed_methods]),
            )

        # Access-Control-Allow-Headers
        requested_headers = request.headers.get("Access-Control-Request-Headers")

        if preflight:
            allowed_headers = app.get_cors_allowed_headers(
                context, request, requested_headers
            )
            response.headers.add(
                "Access-Control-Allow-Headers", ",".join(allowed_headers)
            )

        # Access-Control-Allow-Origin
        allowed_origin: str | None = None
        varies = True
        if requested_origin or preflight:
            allowed_origin = app.get_cors_allowed_origin(
                context, request, requested_origin
            )
            if allowed_origin:
                response.headers.add("Access-Control-Allow-Origin", allowed_origin)
            varies = allowed_origin != "*"
        else:
            # The model isn't known, so go by the setting of the app.
            settings = cast("_CORSSettings", app.settings.cors)
            varies = settings.allowed_origin != "*"

        # The response depends on the origin of the request, also if it
        # doesn't get the header: for another origin, or without any.
        # A cache must not hand it out for the wrong one.
        if varies:
            response.headers.add("Vary", "Origin")

        # Access-Control-Expose-Headers
        exposed_headers = app.get_cors_expose_headers(context, request)
        response.headers.add("Access-Control-Expose-Headers", ",".join(exposed_headers))

        # Access-Control-Allow-Credentials
        allow_credentials = app.get_cors_allow_credentials(context, request)
        if allow_credentials is True:
            response.headers.add("Access-Control-Allow-Credentials", "true")
            if allowed_origin == "*":
                # Browsers reject this, so it never works: tell the developer
                _warn_wildcard_credentials(type(context), request.view_name)

        if preflight:
            max_age = app.get_cors_max_age(context, request)
            response.headers.add("Access-Control-Max-Age", str(max_age))

        return response

    return cors_handler
