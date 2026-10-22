from __future__ import annotations

import logging
import types
from typing import cast

import pytest
from webob.exc import HTTPUnauthorized
from webtest import TestApp as Client

import morepath
from more.cors import CORSApp


class App(CORSApp):
    pass


class Object:
    pass


class FailedObject:
    pass


class UnauthorizedObject:
    pass


class Root:
    pass


class Collection:
    """A model that is falsy, like an empty collection."""

    def __bool__(self) -> bool:
        return False


class Counted:
    pass


class Hooked:
    pass


class Boom:
    pass


path_calls = {"counted": 0}
after_calls = {"hooked": 0}


@App.path(path="/", model=Root)
def get_root(request: morepath.Request[App]) -> Root:
    return Root()


@App.path(path="obj", model=Object)
def get_object(request: morepath.Request[App]) -> Object:
    return Object()


@App.path(path="failedobj", model=FailedObject)
def get_failed_object(request: morepath.Request[App]) -> FailedObject:
    raise Exception()


@App.path(path="unauthorized", model=UnauthorizedObject)
def get_unauthorized_object(
    request: morepath.Request[App],
) -> UnauthorizedObject:
    raise HTTPUnauthorized


@App.path(path="collection", model=Collection)
def get_collection(request: morepath.Request[App]) -> Collection:
    return Collection()


@App.path(path="counted", model=Counted)
def get_counted(request: morepath.Request[App]) -> Counted:
    path_calls["counted"] += 1
    return Counted()


@App.path(path="hooked", model=Hooked)
def get_hooked(request: morepath.Request[App]) -> Hooked:
    # path functions may change the request, for example register a hook
    @request.after
    def count(response: morepath.Response) -> None:
        after_calls["hooked"] += 1

    return Hooked()


@App.path(path="boom", model=Boom)
def get_boom(request: morepath.Request[App]) -> Boom:
    return Boom()


@App.json(model=Root)
def view(context: Root, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "index"}


@App.json(model=Root, request_method="POST")
def post_view(context: Root, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "index-post"}


@App.json(model=Root, name="view2")
def view2(context: Root, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "view2"}


@App.json(model=Root, name="view2", request_method="POST")
def post_view2(context: Root, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "view2-post"}


@App.json(model=Object)
def object_view(context: Object, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "object"}


@App.json(model=Object, request_method="POST")
def object_post_view(context: Object, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "object-post"}


@App.json(model=Collection)
def collection_view(
    context: Collection, request: morepath.Request[App]
) -> dict[str, str]:
    return {"view": "collection"}


@App.json(model=Counted)
def counted_view(context: Counted, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "counted"}


@App.json(model=Hooked)
def hooked_view(context: Hooked, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "hooked"}


@App.json(model=Boom)
def boom_view(context: Boom, request: morepath.Request[App]) -> dict[str, str]:
    raise RuntimeError("boom")


App.cors(
    model=Root,
    view_name="view2",
    allowed_headers=["Cache-Control"],
    expose_headers=["Cookie"],
    allowed_origin="http://localhost.localdomain",
    allow_credentials=True,
    max_age=10,
)

# No ``view_name``: this is for the default view of a model other than Root.
App.cors(
    model=Object,
    allowed_origin="http://object.example",
    allow_credentials=True,
)

App.cors(model=Collection, allowed_origin="http://collection.example")


def get_client(app: type[CORSApp]) -> Client:
    # equivalent to ``class Tapp(app): pass``, which mypy can't check
    tapp = cast("type[CORSApp]", types.new_class("Tapp", (app,)))
    morepath.autoscan()
    morepath.commit(tapp)
    return Client(tapp())


def test_cors_preflight() -> None:
    c = get_client(App)

    r = c.options("/", headers={"Origin": "http://hello.world.com/"})

    assert r.headers.get("Access-Control-Allow-Methods", "").split(",") == [
        "OPTIONS",
        "GET",
        "POST",
    ]
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    assert r.headers.get("Access-Control-Allow-Headers", "").split(",") == [
        "Content-Type",
        "Authorization",
    ]
    assert r.headers.get("Access-Control-Expose-Headers", "").split(",") == [
        "Content-Type",
        "Authorization",
    ]

    assert r.headers.get("Access-Control-Allow-Credentials") is None
    assert r.headers.get("Access-Control-Max-Age") == "60"


def test_cors_override() -> None:
    c = get_client(App)
    r = c.options("/view2", headers={"Origin": "http://hello.world.com/"})

    assert r.headers.get("Access-Control-Allow-Methods", "").split(",") == [
        "OPTIONS",
        "GET",
        "POST",
    ]
    assert (
        r.headers.get("Access-Control-Allow-Origin") == "http://localhost.localdomain"
    )
    assert r.headers.get("Access-Control-Allow-Headers", "").split(",") == [
        "Cache-Control"
    ]
    assert r.headers.get("Access-Control-Expose-Headers", "").split(",") == ["Cookie"]

    assert r.headers.get("Access-Control-Allow-Credentials") == "true"
    assert r.headers.get("Access-Control-Max-Age") == "10"


def test_cors_non_preflight() -> None:
    c = get_client(App)

    r = c.get("/", headers={"Origin": "http://hello.world.com/"})

    # the view must still be published normally
    assert r.json == {"view": "index"}
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    assert r.headers.get("Access-Control-Expose-Headers", "").split(",") == [
        "Content-Type",
        "Authorization",
    ]

    assert r.headers.get("Access-Control-Allow-Credentials") is None
    assert r.headers.get("Access-Control-Max-Age") is None


def test_cors_override_non_preflight() -> None:
    c = get_client(App)

    r = c.get("/view2", headers={"Origin": "http://hello.world.com/"})

    assert r.json == {"view": "view2"}
    assert (
        r.headers.get("Access-Control-Allow-Origin") == "http://localhost.localdomain"
    )
    assert r.headers.get("Access-Control-Expose-Headers") == "Cookie"
    assert r.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_override_other_model_preflight_and_actual_request() -> None:
    # The settings that make the preflight succeed must also be sent with
    # the actual request, otherwise the browser rejects its response.
    c = get_client(App)
    origin = {"Origin": "http://object.example"}

    r = c.options("/obj", headers=origin)
    assert r.headers.get("Access-Control-Allow-Origin") == ("http://object.example")
    assert r.headers.get("Access-Control-Allow-Credentials") == "true"

    for r in (c.get("/obj", headers=origin), c.post("/obj", headers=origin)):
        assert r.headers.get("Access-Control-Allow-Origin") == ("http://object.example")
        assert r.headers.get("Access-Control-Allow-Credentials") == "true"

    # other models are not affected
    r = c.get("/", headers=origin)
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    assert r.headers.get("Access-Control-Allow-Credentials") is None


def test_cors_override_falsy_model() -> None:
    c = get_client(App)
    origin = {"Origin": "http://collection.example"}

    r = c.options("/collection", headers=origin)
    assert r.headers.get("Access-Control-Allow-Origin") == ("http://collection.example")

    r = c.get("/collection", headers=origin)
    assert r.json == {"view": "collection"}
    assert r.headers.get("Access-Control-Allow-Origin") == ("http://collection.example")


def test_cors_error_response() -> None:
    # Without CORS headers the browser would hide the real error.
    c = get_client(App)

    r = c.get(
        "/doesnotexist",
        headers={"Origin": "http://hello.world.com/"},
        status=404,
    )

    assert r.headers.get("Access-Control-Allow-Origin") == "*"


def test_cors_unauthorized_preflight() -> None:
    c = get_client(App)

    r = c.options("/unauthorized")

    assert r.headers.get("Access-Control-Allow-Methods", "").split(",") == [
        "OPTIONS",
        *cast("CORSApp", c.app).settings.cors.allowed_verbs,
    ]


def test_cors_no_allowed_verbs() -> None:
    # use a subclass, so the setting doesn't leak into the other tests
    class NoVerbsApp(App):
        pass

    @NoVerbsApp.setting(section="cors", name="allowed_verbs")
    def get_allowed_verbs() -> list[str]:
        return []

    c = get_client(NoVerbsApp)

    c.options("/", headers={"Origin": "http://hello.world.com/"}, status=404)


def test_cors_failed_view() -> None:

    c = get_client(App)

    r = c.options("/failedobj", expect_errors=True)

    assert r.status_code == 404


def test_cors_no_allowed_origin() -> None:
    # an unset origin means: don't send the header, instead of crashing
    # (``None``) or sending an invalid empty header (``""``)
    class NoOriginApp(App):
        pass

    @NoOriginApp.setting(section="cors", name="allowed_origin")
    def get_allowed_origin() -> None:
        return None

    c = get_client(NoOriginApp)

    for r in (
        c.get("/", headers={"Origin": "http://hello.world.com/"}),
        c.options("/", headers={"Origin": "http://hello.world.com/"}),
    ):
        assert "Access-Control-Allow-Origin" not in r.headers
        # a model may still enable it, so the response depends on the origin
        assert r.headers.get("Vary") == "Origin"

    # ... but the settings of a model still enable it for that model
    r = c.get("/obj", headers={"Origin": "http://object.example"})
    assert r.headers.get("Access-Control-Allow-Origin") == ("http://object.example")


def test_cors_resolves_model_only_for_cors_requests() -> None:
    # Looking up the model for the CORS settings calls the path function
    # once more. That should only happen if the request is a CORS request.
    c = get_client(App)

    path_calls["counted"] = 0
    c.get("/counted")
    assert path_calls["counted"] == 1

    path_calls["counted"] = 0
    r = c.get("/counted", headers={"Origin": "http://hello.world.com/"})
    assert r.json == {"view": "counted"}
    assert path_calls["counted"] == 2


def test_cors_leaves_request_alone() -> None:
    # finding the model for the CORS settings must not have side effects
    # on the request that is being handled
    c = get_client(App)

    for headers in ({}, {"Origin": "http://hello.world.com/"}):
        after_calls["hooked"] = 0
        r = c.get("/hooked", headers=headers)
        assert r.json == {"view": "hooked"}
        assert after_calls["hooked"] == 1


def test_cors_exception_view() -> None:
    # An exception that isn't turned into a response never reaches the CORS
    # tween. An exception view does that, so the browser gets the real error.
    class ExceptionViewApp(App):
        pass

    @ExceptionViewApp.json(model=Exception)
    def exception_view(
        self: Exception, request: morepath.Request[ExceptionViewApp]
    ) -> dict[str, str]:
        @request.after
        def set_status(response: morepath.Response) -> None:
            response.status = 500

        return {"error": "internal server error"}

    c = get_client(ExceptionViewApp)

    r = c.get("/boom", headers={"Origin": "http://hello.world.com/"}, status=500)

    assert r.json == {"error": "internal server error"}
    assert r.headers.get("Access-Control-Allow-Origin") == "*"


ORIGINS = ["http://a.example", "http://b.example"]


class Listed:
    pass


class Unlisted:
    pass


@App.path(path="listed", model=Listed)
def get_listed(request: morepath.Request[App]) -> Listed:
    return Listed()


@App.path(path="unlisted", model=Unlisted)
def get_unlisted(request: morepath.Request[App]) -> Unlisted:
    return Unlisted()


@App.json(model=Listed)
def listed_view(context: Listed, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "listed"}


@App.json(model=Unlisted)
def unlisted_view(context: Unlisted, request: morepath.Request[App]) -> dict[str, str]:
    return {"view": "unlisted"}


def test_cors_multiple_origins() -> None:
    class MultiApp(App):
        pass

    @MultiApp.setting(section="cors", name="allowed_origin")
    def get_allowed_origin() -> list[str]:
        return ORIGINS

    c = get_client(MultiApp)

    for origin in ORIGINS:
        for r in (
            c.get("/", headers={"Origin": origin}),
            c.options("/", headers={"Origin": origin}),
        ):
            assert r.headers.get("Access-Control-Allow-Origin") == origin
            assert r.headers.get("Vary") == "Origin"

    # not in the list: no header, but caches have to know why
    for r in (
        c.get("/", headers={"Origin": "http://evil.example"}),
        c.options("/", headers={"Origin": "http://evil.example"}),
    ):
        assert "Access-Control-Allow-Origin" not in r.headers
        assert r.headers.get("Vary") == "Origin"


def test_cors_multiple_origins_for_model() -> None:
    class MultiApp(App):
        pass

    MultiApp.cors(model=Listed, allowed_origin=ORIGINS)
    MultiApp.cors(model=Unlisted, allowed_origin=[])
    c = get_client(MultiApp)

    for origin in ORIGINS:
        r = c.get("/listed", headers={"Origin": origin})
        assert r.headers.get("Access-Control-Allow-Origin") == origin

    r = c.get("/listed", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in r.headers

    # the other models keep the settings of the app, the wildcard
    r = c.get("/", headers={"Origin": "http://evil.example"})
    assert r.headers.get("Access-Control-Allow-Origin") == "*"

    # an empty list allows no origin
    r = c.get("/unlisted", headers={"Origin": ORIGINS[0]})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_cors_wildcard_is_not_an_origin_in_a_list() -> None:
    class WildApp(CORSApp):
        pass

    WildApp.cors(model=Object, allowed_origin=["http://a.example", "*"])

    # reported when the app is configured
    with pytest.raises(ValueError):
        morepath.commit(WildApp)


def test_cors_vary() -> None:
    # the wildcard is the same for every origin, and for none
    c = get_client(App)
    for r in (
        c.get("/"),
        c.get("/", headers={"Origin": "http://hello.world.com/"}),
    ):
        assert "Vary" not in r.headers

    # an explicit origin is only sent if the request has an origin
    class FixedApp(App):
        pass

    @FixedApp.setting(section="cors", name="allowed_origin")
    def get_allowed_origin() -> str:
        return ORIGINS[0]

    c = get_client(FixedApp)
    r = c.get("/")
    assert "Access-Control-Allow-Origin" not in r.headers
    assert r.headers.get("Vary") == "Origin"
    r = c.get("/", headers={"Origin": ORIGINS[0]})
    assert r.headers.get("Access-Control-Allow-Origin") == ORIGINS[0]
    assert r.headers.get("Vary") == "Origin"


class MountedModel:
    pass


class ParentApp(CORSApp):
    pass


class MountedApp(CORSApp):
    pass


@ParentApp.path(path="/", model=Root)
def get_parent_root(request: morepath.Request[ParentApp]) -> Root:
    return Root()


@ParentApp.json(model=Root)
def parent_view(context: Root, request: morepath.Request[ParentApp]) -> dict[str, str]:
    return {"view": "parent"}


@ParentApp.mount(path="mounted", app=MountedApp)
def mount_app() -> MountedApp:
    return MountedApp()


@MountedApp.path(path="model", model=MountedModel)
def get_mounted_model(request: morepath.Request[MountedApp]) -> MountedModel:
    return MountedModel()


@MountedApp.json(model=MountedModel)
def mounted_view(
    context: MountedModel, request: morepath.Request[MountedApp]
) -> dict[str, str]:
    return {"view": "mounted"}


@MountedApp.json(model=MountedModel, request_method="PUT")
def mounted_put_view(
    context: MountedModel, request: morepath.Request[MountedApp]
) -> dict[str, str]:
    return {"view": "mounted-put"}


def test_cors_mounted_app() -> None:
    morepath.commit(ParentApp, MountedApp)
    c = Client(ParentApp())
    headers = {"Origin": "http://hello.world.com/"}

    # the views are in the mounted app
    r = c.options("/mounted/model", headers=headers)
    assert r.headers.get("Access-Control-Allow-Methods", "").split(",") == [
        "OPTIONS",
        "GET",
        "PUT",
    ]
    assert r.headers.get("Access-Control-Allow-Origin") == "*"

    r = c.put("/mounted/model", headers=headers)
    assert r.headers.get("Access-Control-Allow-Origin") == "*"

    # still a 404 if the mounted app has no views for the path
    r = c.options("/mounted/nothing", headers=headers, expect_errors=True)
    assert r.status_code == 404

    # the app itself is as before
    r = c.options("/", headers=headers)
    assert r.headers.get("Access-Control-Allow-Methods", "").split(",") == [
        "OPTIONS",
        "GET",
    ]


class WildCredentials:
    pass


@App.path(path="wildcred", model=WildCredentials)
def get_wild_credentials(request: morepath.Request[App]) -> WildCredentials:
    return WildCredentials()


@App.json(model=WildCredentials)
def wild_credentials_view(
    context: WildCredentials, request: morepath.Request[App]
) -> dict[str, str]:
    return {"view": "wildcred"}


# credentials, but the origin is left at the default: the wildcard
App.cors(model=WildCredentials, allow_credentials=True)


def wildcard_warnings(
    caplog: pytest.LogCaptureFixture,
) -> list[logging.LogRecord]:
    return [r for r in caplog.records if "allow_credentials" in r.message]


def test_cors_warns_about_wildcard_with_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    c = get_client(App)
    headers = {"Origin": "http://hello.world.com/"}

    # set for a single model
    with caplog.at_level(logging.WARNING):
        c.get("/wildcred", headers=headers)
    assert len(wildcard_warnings(caplog)) == 1
    assert "WildCredentials" in wildcard_warnings(caplog)[0].message

    # ... but only once
    with caplog.at_level(logging.WARNING):
        c.get("/wildcred", headers=headers)
        c.options("/wildcred", headers=headers)
    assert len(wildcard_warnings(caplog)) == 1

    # the response is not changed by it
    r = c.get("/wildcred", headers=headers)
    assert r.headers.get("Access-Control-Allow-Origin") == "*"
    assert r.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_warns_about_wildcard_with_credentials_in_settings(
    caplog: pytest.LogCaptureFixture,
) -> None:

    class CredentialsApp(App):
        pass

    @CredentialsApp.setting(section="cors", name="allow_credentials")
    def get_allow_credentials() -> bool:
        return True

    c = get_client(CredentialsApp)

    with caplog.at_level(logging.WARNING):
        c.get("/", headers={"Origin": "http://hello.world.com/"})
    assert len(wildcard_warnings(caplog)) == 1


def test_cors_does_not_warn_without_wildcard_or_origin(
    caplog: pytest.LogCaptureFixture,
) -> None:

    class ExplicitApp(App):
        pass

    @ExplicitApp.setting(section="cors", name="allow_credentials")
    def get_allow_credentials() -> bool:
        return True

    @ExplicitApp.setting(section="cors", name="allowed_origin")
    def get_allowed_origin() -> list[str]:
        return ORIGINS

    c = get_client(ExplicitApp)

    with caplog.at_level(logging.WARNING):
        # an explicit origin, or a list of them
        c.get("/", headers={"Origin": ORIGINS[0]})
        c.get("/", headers={"Origin": "http://evil.example"})
        # the wildcard isn't sent without an origin, so it isn't a problem
        get_client(App).get("/wildcred")
    assert not wildcard_warnings(caplog)
