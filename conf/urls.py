from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import path

def trigger_error(request):
    division_by_zero = 1 / 0


# TODO 🚫 Delete the index view, route and template.
# def index(request):
#     base_url = (
#         "https://github.com/wilfredinni/django-starter-template?tab=readme-ov-file"
#     )
#     context = {}
#     context["version"] = "0.1.7"
#     context["buttons"] = [
#         {"title": "🚀 Features", "url": f"{base_url}#key-features"},
#         {"title": "📋 Requirements", "url": f"{base_url}#requirements"},
#         {"title": "🛠️ API Schema", "url": "/api/schema/swagger-ui/"},
#     ]
#     return render(request, "index.html", context)


urlpatterns = [
    path('sentry-debug/', trigger_error),
    # TODO⚡ Change the admin url to one of your choice.
    # Please avoid using the default 'admin/' or 'admin-panel/'
    path("admin-panel/", admin.site.urls, name="admin"),
    # TODO ⚡ Disable the auth endpoints you don't need.
    # Enabled: create, profile, login, logout, logoutall
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/training_data/", include("apps.training_data.urls")),
    # path("", index),
]

if settings.DEBUG:
    # import debug_toolbar

    urlpatterns += [
        path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/v1/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        # path("__debug__/", include(debug_toolbar.urls)),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
