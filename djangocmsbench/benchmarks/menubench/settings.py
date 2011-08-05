from djangocmsbench.base_settings import *
import os

INSTALLED_APPS.append('menubench')

STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
STATIC_URL = '/static/'