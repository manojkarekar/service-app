from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        PROVIDER = 'PROVIDER', 'Service Provider'
        ADMIN = 'ADMIN', 'Administrator'

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(
        max_length=10, 
        choices=Role.choices, 
        default=Role.CUSTOMER
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email for login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.role})"


class ServiceCategory(models.Model):
    class Group(models.TextChoices):
        HOME = 'HOME', 'Home Services'
        AUTOMOBILE = 'AUTOMOBILE', 'Automobile Services'
        CONSTRUCTION = 'CONSTRUCTION', 'Construction Services'
        TECHNOLOGY = 'TECHNOLOGY', 'Technology Services'
        PERSONAL = 'PERSONAL', 'Personal Services'

    name = models.CharField(max_length=50, unique=True)
    group = models.CharField(max_length=20, choices=Group.choices, default=Group.HOME)
    description = models.TextField(blank=True, null=True)
    icon_name = models.CharField(max_length=50, default='tools', help_text="Material/Ionicons icon name")

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return f"{self.name} ({self.get_group_display()})"


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    full_name = models.CharField(max_length=100)
    street_address = models.TextField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.full_name or self.user.email


class ProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='providers')
    business_name = models.CharField(max_length=100)
    experience_years = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    rating_avg = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    bio = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True, default='')
    avatar_url = models.TextField(blank=True, null=True, default='')
    is_verified = models.BooleanField(default=False)
    is_online = models.BooleanField(default=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.business_name} ({self.category.name if self.category else 'No Category'})"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='bookings')
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(
        max_length=15, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    scheduled_time = models.DateTimeField()
    service_address = models.TextField()
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    problem_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.customer.full_name} -> {self.provider.business_name} ({self.status})"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_length=10, decimal_places=2, max_digits=10)
    status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    gateway_transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    payment_method = models.CharField(max_length=50, default='Card')
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Payment for Booking #{self.booking.id} - {self.amount} ({self.status})"


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='reviews')
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review #{self.id} for {self.provider.business_name} - Rating: {self.rating}"


class WorkImage(models.Model):
    class Phase(models.TextChoices):
        BEFORE = 'BEFORE', 'Before Job'
        AFTER = 'AFTER', 'After Job'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='work_images')
    image = models.ImageField(upload_to='work_images/')
    phase = models.CharField(
        max_length=10, 
        choices=Phase.choices, 
        default=Phase.BEFORE
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Booking #{self.booking.id} ({self.phase})"


# Signals to automatically create profiles when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == User.Role.CUSTOMER:
            CustomerProfile.objects.create(user=instance, full_name=instance.get_full_name() or instance.username)
        elif instance.role == User.Role.PROVIDER:
            ProviderProfile.objects.create(user=instance, business_name=instance.get_full_name() or instance.username)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == User.Role.CUSTOMER:
        if hasattr(instance, 'customer_profile'):
            instance.customer_profile.save()
    elif instance.role == User.Role.PROVIDER:
        if hasattr(instance, 'provider_profile'):
            instance.provider_profile.save()
