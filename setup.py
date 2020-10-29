# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
  setup_requires=['git-versiointi>=1.5rc4'],
  name='django-pumaska',
  description='Sisäkkäisten lomakkeiden ja -sarjojen käsittely',
  url='https://github.com/an7oine/django-pumaska',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@pispalanit.fi',
  packages=find_packages(),
  include_package_data=True,
  entry_points={
    'django.sovellus': [
      'pumaska = pumaska',
    ],
  },
  zip_safe=False,
)
