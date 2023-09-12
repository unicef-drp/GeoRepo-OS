from django.urls import re_path
from django.contrib.auth.mixins import UserPassesTestMixin
from revproxy.views import ProxyView


class FlowerProxyView(UserPassesTestMixin, ProxyView):
    # `flower` is Docker container, you can use `localhost` instead
    upstream = 'http://{}:{}'.format('worker', 8080)
    url_prefix = 'flower'
    rewrite = (
        (r'^/{}$'.format(url_prefix), r'/{}/'.format(url_prefix)),
    )

    def test_func(self):
        return self.request.user.is_superuser

    @classmethod
    def as_url(cls):
        return re_path(
            r'^(?P<path>{}.*)$'.format(cls.url_prefix),
            cls.as_view()
        )
