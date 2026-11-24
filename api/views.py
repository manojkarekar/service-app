from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q, Avg
from django.utils import timezone

from .models import (
    User, ServiceCategory, CustomerProfile, ProviderProfile,
    Booking, Payment, Review, WorkImage
)
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer,
    ServiceCategorySerializer, ProviderProfileSerializer,
    CustomerProfileSerializer, BookingSerializer,
    PaymentSerializer, ReviewSerializer, WorkImageSerializer
)


# ─────────────────────────────────────────────────────────────
# Auth Views
# ─────────────────────────────────────────────────────────────

class UserRegistrationView(generics.CreateAPIView):
    """Public endpoint to register a new customer or service provider."""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Returns and updates the authenticated user's own profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ─────────────────────────────────────────────────────────────
# Service Categories
# ─────────────────────────────────────────────────────────────

class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List all available service categories. Public access."""
    queryset = ServiceCategory.objects.all().order_by('name')
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


# ─────────────────────────────────────────────────────────────
# Provider Profiles
# ─────────────────────────────────────────────────────────────

class ProviderProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve verified service providers.
    Supports filtering by category and proximity search.
    """
    serializer_class = ProviderProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = ProviderProfile.objects.filter(
            is_verified=True
        ).select_related('user', 'category')

        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by online status
        online_only = self.request.query_params.get('online')
        if online_only == 'true':
            queryset = queryset.filter(is_online=True)

        # Proximity search: ?lat=19.07&lng=72.87&radius=10
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius_km = self.request.query_params.get('radius', 10)

        if lat and lng:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                radius = float(radius_km)

                # Filter providers with coordinates set
                nearby = []
                for provider in queryset:
                    if provider.latitude and provider.longitude:
                        dist = haversine_distance(
                            user_lat, user_lng,
                            float(provider.latitude),
                            float(provider.longitude)
                        )
                        if dist <= radius:
                            provider.distance_km = round(dist, 2)
                            nearby.append(provider)

                # Sort by distance
                nearby.sort(key=lambda p: getattr(p, 'distance_km', 999))
                return nearby
            except (ValueError, TypeError):
                pass

        # Providers with highest ratings and most experience appear at top of list
        return queryset.order_by('-rating_avg', '-experience_years')


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two lat/lng points in km."""
    import math
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────────────────────
# Bookings
# ─────────────────────────────────────────────────────────────

class BookingViewSet(viewsets.ModelViewSet):
    """
    Booking CRUD + status transitions.
    - Customers can create bookings and see their own.
    - Providers see bookings assigned to them.
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CUSTOMER:
            return Booking.objects.filter(
                customer__user=user
            ).select_related(
                'provider__user', 'provider__category',
                'customer', 'payment', 'review'
            ).order_by('-created_at')

        elif user.role == User.Role.PROVIDER:
            return Booking.objects.filter(
                provider__user=user
            ).select_related(
                'customer', 'provider__category', 'payment', 'review'
            ).order_by('-created_at')

        # Admin sees all
        return Booking.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        """Auto-assign the customer profile of the logged-in user."""
        customer_profile = get_object_or_404(CustomerProfile, user=self.request.user)
        serializer.save(customer=customer_profile)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """
        Restricted status transition endpoint.
        Providers: PENDING → ACCEPTED/CANCELLED, ACCEPTED → IN_PROGRESS, IN_PROGRESS → COMPLETED
        Customers: PENDING/ACCEPTED → CANCELLED
        """
        booking = self.get_object()
        new_status = request.data.get('status')
        user = request.user

        valid_transitions = {
            User.Role.PROVIDER: {
                'PENDING': ['ACCEPTED', 'CANCELLED'],
                'ACCEPTED': ['IN_PROGRESS'],
                'IN_PROGRESS': ['COMPLETED'],
            },
            User.Role.CUSTOMER: {
                'PENDING': ['CANCELLED'],
                'ACCEPTED': ['CANCELLED'],
            },
        }

        role = user.role
        allowed = valid_transitions.get(role, {}).get(booking.status, [])

        if new_status not in allowed:
            return Response(
                {'error': f'Cannot transition from {booking.status} to {new_status} as {role}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = new_status
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['get', 'post'], url_path='location')
    def live_location(self, request, pk=None):
        """
        Track and update live provider GPS coordinates for active bookings.
        - GET: Returns provider's current location and customer destination.
        - POST: Provider updates their current latitude and longitude.
        """
        booking = self.get_object()

        if request.method == 'POST':
            lat = request.data.get('latitude')
            lng = request.data.get('longitude')
            if lat is not None and lng is not None:
                provider_profile = booking.provider
                provider_profile.latitude = float(lat)
                provider_profile.longitude = float(lng)
                provider_profile.save()
                return Response({
                    'status': 'Location updated successfully',
                    'latitude': float(lat),
                    'longitude': float(lng)
                })
            return Response({'error': 'latitude and longitude are required'}, status=status.HTTP_400_BAD_REQUEST)

        # GET: Return both locations for tracking
        provider_lat = booking.provider.latitude or 19.0760
        provider_lng = booking.provider.longitude or 72.8777
        customer_lat = booking.latitude or (booking.customer.latitude or 19.0825)
        customer_lng = booking.longitude or (booking.customer.longitude or 72.8855)

        return Response({
            'booking_id': booking.id,
            'status': booking.status,
            'provider_name': booking.provider.business_name,
            'provider_phone': booking.provider.user.phone,
            'provider_location': {
                'latitude': provider_lat,
                'longitude': provider_lng,
            },
            'customer_location': {
                'latitude': customer_lat,
                'longitude': customer_lng,
                'service_address': booking.service_address,
            }
        })


# ─────────────────────────────────────────────────────────────
# Payments
# ─────────────────────────────────────────────────────────────

class PaymentViewSet(viewsets.ModelViewSet):
    """Payment records, one per booking."""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CUSTOMER:
            return Payment.objects.filter(booking__customer__user=user)
        elif user.role == User.Role.PROVIDER:
            return Payment.objects.filter(booking__provider__user=user)
        return Payment.objects.all()

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Simulate a payment for a completed booking.
        In production, integrate Stripe/Razorpay here.
        """
        booking_id = request.data.get('booking_id')
        amount = request.data.get('amount', 0)

        booking = get_object_or_404(
            Booking, id=booking_id, customer__user=request.user
        )

        if booking.status != 'COMPLETED':
            return Response(
                {'error': 'Payment can only be made for completed bookings.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(booking, 'payment'):
            return Response(
                {'error': 'This booking has already been paid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simulated successful payment
        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            payment_method='SIMULATED',
            gateway_transaction_id=f'SIM-{booking_id}-{int(timezone.now().timestamp())}',
            status='SUCCESS',
            paid_at=timezone.now(),
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────
# Reviews
# ─────────────────────────────────────────────────────────────

class ReviewViewSet(viewsets.ModelViewSet):
    """One review per completed + paid booking."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.CUSTOMER:
            return Review.objects.filter(booking__customer__user=user)
        elif user.role == User.Role.PROVIDER:
            return Review.objects.filter(booking__provider__user=user)
        return Review.objects.all()

    def perform_create(self, serializer):
        booking = serializer.validated_data.get('booking')

        # Validate that this booking belongs to the current customer
        if booking.customer.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You can only review your own bookings.')

        # Validate booking is completed
        if booking.status != 'COMPLETED':
            from rest_framework.exceptions import ValidationError
            raise ValidationError('You can only review completed bookings.')

        review = serializer.save(
            customer=booking.customer,
            provider=booking.provider
        )

        # Update provider's overall rating average
        avg_rating = Review.objects.filter(provider=booking.provider).aggregate(Avg('rating'))['rating__avg']
        if avg_rating is not None:
            booking.provider.rating_avg = round(avg_rating, 1)
            booking.provider.save()


# ─────────────────────────────────────────────────────────────
# Work Images (Provider Portfolio)
# ─────────────────────────────────────────────────────────────

class WorkImageViewSet(viewsets.ModelViewSet):
    """Provider portfolio images."""
    serializer_class = WorkImageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.PROVIDER:
            return WorkImage.objects.filter(provider__user=user)
        # Customers can view any provider's work images
        provider_id = self.request.query_params.get('provider')
        if provider_id:
            return WorkImage.objects.filter(provider_id=provider_id)
        return WorkImage.objects.none()

    def perform_create(self, serializer):
        provider = get_object_or_404(ProviderProfile, user=self.request.user)
        serializer.save(provider=provider)
