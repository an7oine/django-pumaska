# -*- coding: utf-8 -*-

import setuptools

setuptools._install_setup_requires({'setup_requires': ['git-versiointi']})
from versiointi import asennustiedot

setuptools.setup(
  name='django-pumaska',
  description='Sisäkkäisten lomakkeiden ja -sarjojen käsittely',
  url='https://github.com/an7oine/django-pumaska',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@pispalanit.fi',
  packages=setuptools.find_packages(),
  include_package_data=True,
  entry_points={
    'django.sovellus': [
      'pumaska = pumaska',
    ],
  },
  zip_safe=False,
  **asennustiedot(__file__),
)
