from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User, ServiceCategory, CustomerProfile, ProviderProfile,
    Booking, Payment, Review, WorkImage
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'phone']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Marketplace Info', {'fields': ('phone', 'role', 'avatar')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Marketplace Info', {'fields': ('phone', 'role')}),
    )


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_name']
    search_fields = ['name']


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'category', 'experience_years', 'is_verified', 'is_online']
    list_filter = ['is_verified', 'is_online', 'category']
    search_fields = ['business_name', 'user__email', 'user__username']
    actions = ['verify_providers', 'unverify_providers']

    @admin.action(description='Mark selected providers as Verified')
    def verify_providers(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f'{queryset.count()} provider(s) marked as verified.')

    @admin.action(description='Revoke verification from selected providers')
    def unverify_providers(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, f'{queryset.count()} provider(s) unverified.')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'street_address']
    search_fields = ['full_name', 'user__email']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'provider', 'status', 'scheduled_time', 'created_at']
    list_filter = ['status']
    search_fields = ['customer__full_name', 'provider__business_name']
    readonly_fields = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'amount', 'payment_method', 'status', 'paid_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['gateway_transaction_id', 'booking__id']
    readonly_fields = ['paid_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['booking__customer__full_name', 'booking__provider__business_name']


@admin.register(WorkImage)
class WorkImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'phase', 'uploaded_at']
    list_filter = ['phase']
    search_fields = ['booking__id']
