from cms.api import create_page
from cms.models.pagemodel import Page
from cms.test_utils.util.request_factory import RequestFactory
from django import template
from django.contrib.auth.models import AnonymousUser
from djangocmsbench.utils import run_benchmark

rf = RequestFactory()
request = rf.get('/')
request.user = AnonymousUser()
context = template.Context({
    'request': request
})
tpl = template.Template("{% load menu_tags %}{% show_menu %}")

def benchmark():
    tpl.render(context)

def setup():
    """
    Build tree:
    
    3 levels
    5 per level/branch
    """
    names = ['a', 'b', 'c', 'd', 'e']
    languages = ['de', 'it', 'fr', 'rm']
    for lang in languages:
        for name in names:
            page = create_page(name, 'template.html', lang, published=True, in_navigation=True)
            for name in names:
                page = Page.objects.get(pk=page.pk)
                child = create_page(name, 'template.html', lang, published=True, parent=page, in_navigation=True)
                for name in names:
                    child = Page.objects.get(pk=child.pk)
                    create_page(name, 'template.html', lang, published=True, parent=child, in_navigation=True)


run_benchmark(
    benchmark,
    setup=setup,
    meta = {
        'description': 'A simple Model.objects.get() call.',
    }
)