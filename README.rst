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
