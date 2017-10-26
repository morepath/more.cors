from setuptools import setup, find_packages
import sys
import os

version = '0.1'

setup(name='more.cors',
      version=version,
      description="CORS support for Morepath",
      long_description="""\
""",
      classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='morepath CORS',
      author='Izhar Firdaus',
      author_email='kagesenshi.87@gmail.com',
      url='http://github.com/kagesenshi/more.cors',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      namespace_packages=['more'],
      zip_safe=False,
      install_requires=[
          'setuptools',
          'morepath',
      ],
      entry_points={
          'morepath': [
              'scan = more.cors'
          ]
      }
      )
