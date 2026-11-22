CHANGES
=======

1.0.0 (unreleased)
------------------

New
~~~

- Add support for several allowed origins: ``allowed_origin`` can be a list
  of origins, for the ``cors`` settings and for ``App.cors()``. The origin of
  the request is sent back if it is in the list, otherwise the header is left
  out. A list with ``"*"`` in it is an error.

Changed
~~~~~~~

- ``App.cors()`` without ``view_name`` now applies to the default
  view of the model. Before it never matched anything.

  The settings for models that are falsy, like an empty collection, are no
  longer ignored either.

- ``None`` or an empty string for ``allowed_origin`` now means
  that the ``Access-Control-Allow-Origin`` header is not sent. Before it
  raised an error or sent an empty header.

- Log a warning if a response has both ``Access-Control-Allow-Origin: *`` and
  ``Access-Control-Allow-Credentials``. Browsers reject that, so it never
  works for requests with credentials. This is logged once for every model
  and view.

- Responses get ``Vary: Origin`` unless ``allowed_origin`` is
  ``"*"``. Before it was only sent together with an
  ``Access-Control-Allow-Origin`` header, so a cache could hand out a response
  without it, for example for a request without an ``Origin`` header, to a
  request that needs it.

- Add type annotations and integrate ``mypy`` and ``pyright``.

Fixed
~~~~~

- Fix preflight requests for paths in mounted apps failing with ``404 Not
  Found``.

- Fix preflight requests failing with ``404 Not Found`` with Morepath 1.0.

- Fix the settings of ``App.cors()`` for models other than the root model
  being ignored for the actual request, while the preflight request used
  them. The browser rejected the response of the actual request because it
  didn't match the preflight.

  To find the model, the path function is now called an additional time for
  requests with an ``Origin`` header.

Others
~~~~~~
- Add type annotations and integrate ``mypy`` and ``pyright``.

- Switch to ``pyproject.toml`` based project setup.

- Switch to ``src-layout`` based file structure.

- Switch to native namespace package defined in PEP 420.

- Add support for Python 3.11 - 3.15.

- Drop support for Python below 3.11.

- Support Pypy 3.12.

- Switch from black, flake8, isort and pyupgrade to Ruff_ linter and formatter.

  .. _Ruff: https://docs.astral.sh/ruff

- Replace ``pre-commit`` integration with our custom tracked
  pre-commit git hook for Ruff checks on staged Python files.

- Fix linting and formatting errors.

- Update ``README.rst``.

- Remove coveralls integration.

- Use GitHub Actions for CI.

- Adjust the deployment strategy:
  
  * Move the Pypi upload from ``zest.release`` to ``gh-actions``.

  * Use ``v`` + version as release tags like ``v1.0.0``.

  * So we still use ``zest.release`` but without publishing to Pypi.
    The Pypi upload is triggered by pushing the new release tag to GitHub.
    This happens in the Release workflow in ``.github/workflows/release.yml``.
    With this workflow we get Trusted Publishing with short-lived OIDC tokens
    that PyPI issues to one specific repository, workflow file and environment (``pypi``).
    We also get PEP 740 provenance and can set required reviewers for the environment
    and a ruleset who can create release tags and trigger releases.

- Make an overall cleanup.


0.3 (2020-04-26)
----------------

- **Removed**: Removed support for Python 2.
  
  You have to upgrade to Python 3 if you want to use this version.

- Added support for Python 3.7 and 3.8 and PyPy 3.6.

- Make Python 3.7 the default testing environment.

- Add integration for the Black code formatter.


0.2 (2018-06-11)
----------------

- Fix list of allowed verbs for failed (unauthorized) preflight (see `PR #4`_).

.. _PR #4: https://github.com/morepath/more.cors/pull/4


0.1 (2018-06-08)
----------------

- Initial public release
