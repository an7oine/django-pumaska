# -*- coding: utf-8 -*-

DATABASES = {'default': {
  'ENGINE': 'django.db.backends.sqlite3',
  'NAME': 'testi',
}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
INSTALLED_APPS = [
  'django.contrib.contenttypes',
  'pumaska',
  'testit',
]
MIDDLEWARE = []
SECRET_KEY = 'epäjärjestelmällistyttämättömyydellänsäkäänköhän'
TEMPLATES = [{
  'BACKEND': 'django.template.backends.django.DjangoTemplates',
  'APP_DIRS': True,
}]
USE_TZ = True
