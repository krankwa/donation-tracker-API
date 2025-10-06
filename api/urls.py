from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    register, login, get_current_user,
    register_affected, login_affected,
    UserViewSet, LocationViewSet, DonationViewSet,
    DonationTrackingViewSet, EmergencyRequestViewSet,
    AnonymousLocationViewSet, DonationHistoryViewSet, DonationRatingViewSet,
    location_update, stop_tracking
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'locations', LocationViewSet)
router.register(r'donations', DonationViewSet)
router.register(r'tracking', DonationTrackingViewSet)
router.register(r'emergency-requests', EmergencyRequestViewSet)
router.register(r'anonymous-locations', AnonymousLocationViewSet, basename='anonymous-location')
router.register(r'donation-history', DonationHistoryViewSet, basename='donation-history')
router.register(r'donation-ratings', DonationRatingViewSet, basename='donation-rating')

urlpatterns = [
    path('auth/register/', register, name='register'),
    path('auth/register-affected/', register_affected, name='register-affected'),
    path('auth/login/', login, name='login'),
    path('auth/login-affected/', login_affected, name='login-affected'),
    path('auth/me/', get_current_user, name='current-user'),
    path('location-updates/', location_update, name='location-update'),
    path('stop-tracking/', stop_tracking, name='stop-tracking'),
    path('', include(router.urls)),
]
