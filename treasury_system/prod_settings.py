""" Production Settings """
# default: use settings from main settings.py if not overwritten
from .settings import *
import django_heroku
import dj_database_url

DEBUG = False
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', SECRET_KEY)
# adjust to the URL of your Heroku app
ALLOWED_HOSTS = ['treasury-system.herokuapp.com']

# Activate Django-Heroku.
django_heroku.settings(locals())

DATABASES = {
    'default': dj_database_url.config(),
}

# Static asset configuration.
STATIC_ROOT = 'staticfiles'

# Honor the 'X-Forwarded-Proto' header for request.is_secure().
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Turn off DEBUG mode.
DEBUG = False