from cms.conf.global_settings import *

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = ':memory:'

INSTALLED_APPS = [
    'cms',
    'menus', 
    'mptt',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.contenttypes',
]

CMS_TEMPLATES = [('template.html', 'template.html')]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.core.context_processors.request',
]

LANGUAGES = [
    ('rm', 'Romantsch'),
    ('de', 'German'),
    ('it', 'Italian'),
    ('fr', 'French'),
]

CMS_LANGUAGES = LANGUAGES 