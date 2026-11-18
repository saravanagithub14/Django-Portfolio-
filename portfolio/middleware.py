from django.conf import settings


class EdgeCacheMiddleware:
    """
    Lets Cloudflare serve the public pages for EDGE_CACHE_SECONDS (cloudflare.md). They are the same for every
    visitor: no template reads the user or the session. s-maxage only applies to shared caches; max-age=0
    keeps browsers asking the edge, so a purge reaches them straight away.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = request.resolver_match
        if (settings.EDGE_CACHE_SECONDS and request.method in ('GET', 'HEAD') and response.status_code == 200
                and match and match.func.__module__ == 'portfolio.views' and not response.cookies):
            response['Cache-Control'] = f'public, max-age=0, s-maxage={settings.EDGE_CACHE_SECONDS}'
        return response
