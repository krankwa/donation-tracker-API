from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/locations/$', consumers.LocationConsumer.as_asgi()),
    re_path(r'ws/donations/$', consumers.DonationConsumer.as_asgi()),
]
