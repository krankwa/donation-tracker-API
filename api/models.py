from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model with role-based access"""
    
    ROLE_CHOICES = [
        ('donator', 'Donator'),
        ('affected', 'Affected'),
        ('admin', 'Admin'),
    ]
    
    username = None
    email = models.EmailField(unique=True)  # Reverted to required
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='donator')
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_location_shared = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_location_shared']),
        ]


class Location(models.Model):
    """Track user locations in real-time"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locations')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)
    accuracy = models.FloatField(null=True, blank=True)  # GPS accuracy in meters
    
    def __str__(self):
        return f"{self.user.email} - {self.latitude}, {self.longitude}"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'is_current']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['is_current']),
        ]
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['is_current']),
        ]


class Donation(models.Model):
    """Track relief goods donations"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('water', 'Water'),
        ('clothing', 'Clothing'),
        ('medicine', 'Medicine'),
        ('shelter', 'Shelter Materials'),
        ('hygiene', 'Hygiene Products'),
        ('other', 'Other'),
    ]
    
    donator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='donations_made',
        limit_choices_to={'role': 'donator'}
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations_received',
        limit_choices_to={'role': 'affected'}
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=50)  # e.g., "boxes", "liters", "pieces"
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    pickup_location = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    delivery_location = models.TextField(blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    image = models.ImageField(upload_to='donations/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.title} by {self.donator.email}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['donator', '-created_at']),
            models.Index(fields=['recipient', '-created_at']),
        ]


class DonationTracking(models.Model):
    """Track donation delivery progress"""
    
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='tracking_history')
    status = models.CharField(max_length=20, choices=Donation.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.donation.title} - {self.status}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Donation Tracking'


class EmergencyRequest(models.Model):
    """Emergency relief requests from affected users"""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('fulfilled', 'Fulfilled'),
        ('closed', 'Closed'),
    ]
    
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='emergency_requests',
        limit_choices_to={'role': 'affected'}
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Donation.CATEGORY_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    quantity_needed = models.PositiveIntegerField()
    unit = models.CharField(max_length=50)
    
    location = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    people_affected = models.PositiveIntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} by {self.requester.email}"
    
    class Meta:
        ordering = ['-priority', '-created_at']


class AnonymousLocation(models.Model):
    """Track locations of anonymous affected users (no registration required)"""
    
    # Contact information (phone is required, others are optional)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^(09|\+639)\d{9}$',
            message="Phone number must be a valid PH mobile number (e.g., 09171234567 or +639171234567)"
        )]
    )
    facebook = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    
    # Location details
    photo = models.ImageField(upload_to='anonymous_locations/', blank=True, null=True)
    
    # Supply needs (stored as JSON)
    supply_needs = models.JSONField(default=dict, blank=True)
    # Expected structure: {
    #   'water': int,
    #   'food': int,
    #   'people_count': int,
    #   'medical_supplies': int,
    #   'clothing': int,
    #   'shelter_materials': int,
    #   'other': str
    # }
    
    # Location data
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Session identifier (to allow updating same user's location)
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # QR Code and Donation Tracking
    qr_code = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True, 
                                help_text="Unique QR code for donators to scan")
    donation_received = models.BooleanField(default=False, 
                                           help_text="Whether this location has received donation")
    donated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anonymous_donations_made',
        limit_choices_to={'role': 'donator'},
        help_text="Donator who scanned the QR code"
    )
    donation_timestamp = models.DateTimeField(null=True, blank=True,
                                             help_text="When the donation was received")
    next_request_allowed_at = models.DateTimeField(null=True, blank=True,
                                                   help_text="When this phone can create another request (3 hours after donation)")
    
    def __str__(self):
        return f"Anonymous User - {self.phone} ({self.latitude}, {self.longitude})"
    
    class Meta:
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['session_id']),
            models.Index(fields=['is_active', '-last_seen']),
            models.Index(fields=['qr_code']),
        ]


class DonatorOnTheWay(models.Model):
    """Track donators who are on their way to help affected users"""
    
    location = models.ForeignKey(
        AnonymousLocation,
        on_delete=models.CASCADE,
        related_name='donators_on_the_way'
    )
    donator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='helping_locations',
        limit_choices_to={'role': 'donator'}
    )
    marked_at = models.DateTimeField(auto_now_add=True)
    arrived = models.BooleanField(default=False)
    is_tracking = models.BooleanField(default=False)  # Track if location sharing is active
    last_location_update = models.DateTimeField(null=True, blank=True)  # Last tracking update
    
    def __str__(self):
        return f"{self.donator.email} → {self.location.phone}"
    
    class Meta:
        unique_together = ['location', 'donator']
        ordering = ['-marked_at']


class LocationUpdate(models.Model):
    """Track real-time location updates from donators on the way"""
    
    donator_on_the_way = models.ForeignKey(
        DonatorOnTheWay,
        on_delete=models.CASCADE,
        related_name='location_updates'
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.FloatField(help_text="Location accuracy in meters")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.donator_on_the_way.donator.email} @ {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['donator_on_the_way', '-timestamp']),
        ]


class DonationHistory(models.Model):
    """Track QR-based donations for public viewing"""
    
    # Donator information
    donator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='qr_donations_made',
        limit_choices_to={'role': 'donator'}
    )
    
    # Affected user information (from AnonymousLocation)
    affected_first_name = models.CharField(max_length=100)
    affected_last_name = models.CharField(max_length=100)
    affected_phone = models.CharField(max_length=15)
    
    # Location information
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Supply needs that were fulfilled (stored as JSON)
    supply_needs_fulfilled = models.JSONField(default=dict, blank=True)
    
    # QR Code used
    qr_code = models.CharField(max_length=100, db_index=True)
    
    # Timestamps
    donated_at = models.DateTimeField(auto_now_add=True)
    
    # Optional notes
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.donator.email} → {self.affected_first_name} {self.affected_last_name} ({self.donated_at.strftime('%Y-%m-%d %H:%M')})"
    
    class Meta:
        ordering = ['-donated_at']
        verbose_name_plural = 'Donation History'
        indexes = [
            models.Index(fields=['donator', '-donated_at']),
            models.Index(fields=['-donated_at']),
        ]


class DonationRating(models.Model):
    """Track ratings and supply confirmations from affected users"""
    
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    # Reference to the donation history
    donation_history = models.OneToOneField(
        DonationHistory,
        on_delete=models.CASCADE,
        related_name='rating'
    )
    
    # Rating from affected user
    rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    comment = models.TextField(blank=True)
    
    # Supply confirmation from affected user
    supplies_confirmed = models.JSONField(default=dict, blank=True)
    # Expected structure: {
    #   'water_received': int,
    #   'food_received': int,
    #   'medical_supplies_received': int,
    #   'clothing_received': int,
    #   'shelter_materials_received': int,
    #   'other_items': str,
    #   'all_supplies_received': bool
    # }
    
    # Timestamps
    rated_at = models.DateTimeField(auto_now_add=True)
    
    # Session info for anonymous affected users
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    def __str__(self):
        rating_text = f"{self.rating} stars" if self.rating else "No rating"
        return f"Rating for {self.donation_history.donator.email} → {self.donation_history.affected_first_name}: {rating_text}"
    
    class Meta:
        ordering = ['-rated_at']
        verbose_name_plural = 'Donation Ratings'
