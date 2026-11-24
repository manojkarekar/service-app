from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    User, ServiceCategory, CustomerProfile, ProviderProfile,
    Booking, Payment, Review, WorkImage
)


# ─────────────────────────────────────────────────────────────
# Auth / User
# ─────────────────────────────────────────────────────────────

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.CUSTOMER)

    # Optional provider-specific fields
    business_name = serializers.CharField(required=False, allow_blank=True)
    experience_years = serializers.IntegerField(required=False, default=0)
    category = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.all(), required=False, allow_null=True
    )

    # Optional customer-specific fields
    full_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'phone', 'role',
            # Provider
            'business_name', 'experience_years', 'category',
            # Customer
            'full_name',
        ]

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        # Pop non-User fields
        role = validated_data.get('role', User.Role.CUSTOMER)
        business_name = validated_data.pop('business_name', '')
        experience_years = validated_data.pop('experience_years', 0)
        category = validated_data.pop('category', None)
        full_name = validated_data.pop('full_name', '')

        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Update the profile created by the signal
        if role == User.Role.PROVIDER:
            profile = user.provider_profile
            if business_name:
                profile.business_name = business_name
            if category:
                profile.category = category
            profile.experience_years = experience_years
            profile.save()

        elif role == User.Role.CUSTOMER:
            profile = user.customer_profile
            if full_name:
                profile.full_name = full_name
            profile.save()

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'avatar', 'profile']
        read_only_fields = ['role']

    def update(self, instance, validated_data):
        request = self.context.get('request')
        profile_data = request.data.get('profile', {}) if request else {}

        # Update base User fields
        if 'phone' in validated_data:
            instance.phone = validated_data['phone']
        if 'email' in validated_data:
            instance.email = validated_data['email']
        instance.save()

        # Update Provider profile fields
        if instance.role == User.Role.PROVIDER and hasattr(instance, 'provider_profile'):
            p = instance.provider_profile
            if 'business_name' in profile_data:
                p.business_name = profile_data['business_name']
            if 'bio' in profile_data:
                p.bio = profile_data['bio']
            if 'address' in profile_data:
                p.address = profile_data['address']
            if 'avatar_url' in profile_data:
                p.avatar_url = profile_data['avatar_url']
            if 'experience_years' in profile_data:
                try:
                    p.experience_years = int(profile_data['experience_years'])
                except (ValueError, TypeError):
                    pass
            if 'is_online' in profile_data:
                p.is_online = bool(profile_data['is_online'])
            p.save()

        # Update Customer profile fields
        elif instance.role == User.Role.CUSTOMER and hasattr(instance, 'customer_profile'):
            c = instance.customer_profile
            if 'full_name' in profile_data:
                c.full_name = profile_data['full_name']
            if 'street_address' in profile_data:
                c.street_address = profile_data['street_address']
            c.save()

        return instance

    def get_profile(self, obj):
        if obj.role == User.Role.CUSTOMER:
            try:
                return CustomerProfileSerializer(obj.customer_profile).data
            except CustomerProfile.DoesNotExist:
                return None
        elif obj.role == User.Role.PROVIDER:
            try:
                return ProviderProfileSerializer(obj.provider_profile).data
            except ProviderProfile.DoesNotExist:
                return None
        return None


# ─────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────

class ServiceCategorySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='get_group_display', read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'group', 'group_name', 'description', 'icon_name']


# ─────────────────────────────────────────────────────────────
# Profiles
# ─────────────────────────────────────────────────────────────

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'full_name', 'street_address',
            'latitude', 'longitude'
        ]


class ProviderProfileSerializer(serializers.ModelSerializer):
    category_detail = ServiceCategorySerializer(source='category', read_only=True)
    rating_avg = serializers.SerializerMethodField()
    completed_jobs_count = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = ProviderProfile
        fields = [
            'id', 'business_name', 'bio', 'address', 'avatar_url', 'avatar',
            'phone', 'category', 'category_detail',
            'experience_years', 'is_verified', 'is_online',
            'latitude', 'longitude', 'rating_avg', 'completed_jobs_count',
            'reviews_count', 'user',
        ]
        read_only_fields = ['is_verified', 'rating_avg']

    def get_avatar(self, obj):
        if obj.avatar_url:
            return obj.avatar_url
        if obj.user and obj.user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.avatar.url) if request else obj.user.avatar.url
        name_clean = obj.business_name.replace(' ', '+')
        return f"https://ui-avatars.com/api/?name={name_clean}&background=1B4FD8&color=fff&size=160&bold=true"

    def get_phone(self, obj):
        return obj.user.phone if obj.user else ''

    def get_rating_avg(self, obj):
        # Calculate fresh from reviews
        from django.db.models import Avg
        val = obj.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(val, 1) if val is not None else round(obj.rating_avg or 0.0, 1)

    def get_completed_jobs_count(self, obj):
        return obj.bookings.filter(status='COMPLETED').count()

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_user(self, obj):
        return {
            'email': obj.user.email,
            'phone': obj.user.phone,
        }


# ─────────────────────────────────────────────────────────────
# Bookings
# ─────────────────────────────────────────────────────────────

class BookingSerializer(serializers.ModelSerializer):
    customer_detail = CustomerProfileSerializer(source='customer', read_only=True)
    provider_detail = ProviderProfileSerializer(source='provider', read_only=True)
    payment = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'provider', 'customer_detail', 'provider_detail',
            'status', 'scheduled_time', 'service_address', 'latitude', 'longitude',
            'problem_description', 'payment', 'review', 'created_at',
        ]
        read_only_fields = ['status', 'customer', 'created_at']

    def get_payment(self, obj):
        try:
            return PaymentSerializer(obj.payment).data
        except Exception:
            return None

    def get_review(self, obj):
        try:
            return ReviewSerializer(obj.review).data
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────
# Payments
# ─────────────────────────────────────────────────────────────

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'booking', 'amount', 'payment_method',
            'gateway_transaction_id', 'status', 'paid_at',
        ]
        read_only_fields = ['gateway_transaction_id', 'status', 'paid_at']


# ─────────────────────────────────────────────────────────────
# Reviews
# ─────────────────────────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['created_at']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value


# ─────────────────────────────────────────────────────────────
# Work Images
# ─────────────────────────────────────────────────────────────

class WorkImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkImage
        fields = ['id', 'booking', 'image', 'phase', 'uploaded_at']
        read_only_fields = ['uploaded_at']
