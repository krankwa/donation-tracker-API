import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'donation_backend.settings')

app = Celery('donation_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
