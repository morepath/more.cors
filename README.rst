.. image:: https://github.com/morepath/more.cors/workflows/CI/badge.svg?branch=master
   :target: https://github.com/morepath/more.cors/actions?workflow=CI
   :alt: CI Status

.. image:: https://img.shields.io/pypi/v/more.cors.svg
  :target: https://pypi.org/project/more.cors/

.. image:: https://img.shields.io/pypi/pyversions/more.cors.svg
  :target: https://pypi.org/project/more.cors/



more.cors: CORS support for Morepath
====================================

This package adds CORS support to Morepath.


Quick start
-----------

Install ``more.cors``:

.. code-block:: console

    $ pip install -U more.cors

Extend your App class from CORSApp:

.. code-block:: python

    from more.cors import CORSApp


    class App(CORSApp):
        pass

This will add basic CORS support to your Morepath app.


Settings
--------

more.cors provides settings in the 'cors' section. Here are the defaults:

.. code-block:: python

    @App.setting_section(section='cors')
    def cors_settings():
        return {
            'allowed_verbs': ['GET', 'PUT', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
            'allowed_origin': '*',
            'expose_headers': ['Content-Type', 'Authorization'],
            'allowed_headers': ['Content-Type', 'Authorization'],
            'max_age': 60,
            'allow_credentials': False
        }

The following settings are available:

allowed_verbs
  A list of allowed HTTP request methods.

allowed_origin
  The origin that may access the resource, for example
  ``https://example.com``: the scheme, the host and the port if it isn't the
  default one, without a path or a trailing slash. It has to be the same as
  the ``Origin`` header of the request.
  For requests **without credentials**, "*" can be used as a wildcard,
  allowing any origin to access the resource.
  Browsers reject the wildcard for requests with credentials, so you have to
  set an explicit origin if you set ``allow_credentials``.
  To allow several origins, set a list of them, see `Allow several origins`_.
  ``None`` or an empty string means that the ``Access-Control-Allow-Origin``
  header is not sent at all, so no origin is allowed. Together with the
  settings for single views (see below) this allows to enable CORS for
  selected views only.

expose_headers
  A list of HTTP headers which can be exposed as part of the response.
  This has to be a list of strings, not a single string.

allowed_headers
  A list of HTTP headers which can be used during the actual request.
  This has to be a list of strings, not a single string.

max_age
  Maximum number of seconds the results of a preflight request can be cached.

allow_credentials
  Boolean which indicates whether or not the actual request can be made using
  credentials.
  Credentials are cookies, authorization headers or TLS client certificates.
  This requires an explicit ``allowed_origin``, not "*". If more.cors sends
  both, it logs a warning, once for every model and view.


Allow several origins
---------------------

A browser only accepts a single origin in the response. To allow several,
set a list of origins. The response then contains the origin of the request
if it is in the list, and no ``Access-Control-Allow-Origin`` header if it is
not, so the browser blocks the request:

.. code-block:: python

    @App.setting(section='cors', name='allowed_origin')
    def get_allowed_origin():
        return ['https://app.example.com', 'https://admin.example.com']

This also works for a single view, see below:

.. code-block:: python

    App.cors(
        model=Document,
        allowed_origin=['https://app.example.com', 'https://admin.example.com']
    )

The wildcard "*" can't be part of the list, which is an error when the app is
configured. Use ``allowed_origin='*'`` to allow every origin.

This is also how to allow credentials for more than one origin. Do not
copy the ``Origin`` header of the request into the response without checking
it against a list. That allows every website to read the responses with the
credentials of your users.


Specify CORS settings for a single view
---------------------------------------

more.cors exposes the ``App.cors()`` class method.
This can be used to specify settings for a single view:

.. code-block:: python

    App.cors(
        model=Root,
        view_name='view2',
        allowed_headers=['Cache-Control'],
        expose_headers=['Cookie'],
        allowed_origin='https://foo.com',
        allow_credentials=True,
        max_age=10
    )

If you leave out ``view_name``, the settings are for the default view of the
model, which is the view without a name:

.. code-block:: python

    App.cors(model=Document, allowed_origin='https://example.com')

model
  Specifies the corresponding view model.

view_name
  The name of the view. Leave it out for the default view of the model.
  Every named view needs its own ``App.cors()`` call.

allowed_headers, expose_headers, allowed_origin, allow_credentials, max_age
  The settings which can be specified. For details see Settings_.
  Settings that you leave out fall back to the settings in the ``cors``
  section.


How it works
------------

Preflight requests
  more.cors answers every ``OPTIONS`` request itself, so views registered
  for the ``OPTIONS`` method are never called.
  ``Access-Control-Allow-Methods`` lists ``OPTIONS`` and those of the
  ``allowed_verbs`` for which the path has a view. If there is none, for
  example because the path doesn't exist, the response is ``404 Not Found``.
  A preflight request also succeeds if the path function raises
  ``HTTPUnauthorized``, as browsers don't send credentials with it. In this
  case all ``allowed_verbs`` are listed.

Other requests
  The responses to requests with an ``Origin`` header get the CORS headers.
  This includes error responses that Morepath creates for you, like
  ``404 Not Found`` or ``403 Forbidden``. Without the headers the browser
  would report a CORS error instead of the actual error.

Vary
  Unless ``allowed_origin`` is the wildcard, every response gets
  ``Vary: Origin``, also if it has no ``Access-Control-Allow-Origin`` header.
  The response depends on the origin of the request, and a cache must not
  hand out a response made for one origin, or for none, to another.
  This is based on the setting for the app, as the model isn't known for
  requests without an ``Origin`` header.

Mounted apps
  The settings are always those of the app that more.cors is used in, not
  of mounted apps: a tween of a mounted app is never called. Preflight
  requests list the methods for which the mounted app has a view.

Path functions
  To find the settings for the model of a request, more.cors needs to know
  which model that is, and Morepath doesn't tell. So it resolves the path
  on a copy of the request, which calls your path function.
  For a preflight request that is the only call, as your views are not
  called. For other requests with an ``Origin`` header it is one more call
  than usual. Requests without an ``Origin`` header are not affected.


Unhandled exceptions
--------------------

An exception that isn't turned into a response never reaches more.cors. The
server then answers with its own error page, without CORS headers, and the
browser reports a CORS error instead of the ``500 Internal Server Error``.
Register an exception view to avoid this:

.. code-block:: python

    @App.json(model=Exception)
    def exception_view(self, request):
        @request.after
        def set_status(response):
            response.status = 500

        return {'error': 'Internal Server Error'}

Note that this also keeps the exception from reaching a WSGI middleware that
reports errors, so you should log it in the view.
