from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    UserRegistrationView, UserProfileView, ServiceCategoryViewSet,
    ProviderProfileViewSet, BookingViewSet, PaymentViewSet, ReviewViewSet,
    WorkImageViewSet
)

router = DefaultRouter()
router.register(r'categories', ServiceCategoryViewSet, basename='category')
router.register(r'providers', ProviderProfileViewSet, basename='provider')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'work-images', WorkImageViewSet, basename='work-image')

urlpatterns = [
    # Auth endpoints
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Profile endpoint
    path('users/me/', UserProfileView.as_view(), name='user-profile'),

    # Viewset routers
    path('', include(router.urls)),
]
