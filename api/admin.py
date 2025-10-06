from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Location, Donation, DonationTracking, EmergencyRequest, DonationHistory, DonationRating


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_location_shared', 'is_active']
    list_filter = ['role', 'is_location_shared', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'address', 'profile_picture')}),
        ('Role & Permissions', {'fields': ('role', 'is_location_shared', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['user', 'latitude', 'longitude', 'is_current', 'timestamp']
    list_filter = ['is_current', 'timestamp']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['title', 'donator', 'recipient', 'category', 'status', 'quantity', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'description', 'donator__email', 'recipient__email']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'quantity', 'unit', 'image')
        }),
        ('Parties', {
            'fields': ('donator', 'recipient')
        }),
        ('Status', {
            'fields': ('status', 'delivered_at')
        }),
        ('Locations', {
            'fields': ('pickup_location', 'pickup_latitude', 'pickup_longitude',
                      'delivery_location', 'delivery_latitude', 'delivery_longitude')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(DonationTracking)
class DonationTrackingAdmin(admin.ModelAdmin):
    list_display = ['donation', 'status', 'updated_by', 'timestamp']
    list_filter = ['status', 'timestamp']
    search_fields = ['donation__title', 'notes']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'requester', 'category', 'priority', 'status', 'people_affected', 'created_at']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['title', 'description', 'requester__email']
    ordering = ['-priority', '-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('title', 'description', 'category', 'priority', 'status')
        }),
        ('Requester', {
            'fields': ('requester', 'people_affected')
        }),
        ('Need Details', {
            'fields': ('quantity_needed', 'unit')
        }),
        ('Location', {
            'fields': ('location', 'latitude', 'longitude')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'fulfilled_at')
        }),
    )


@admin.register(DonationHistory)
class DonationHistoryAdmin(admin.ModelAdmin):
    list_display = ['donator', 'affected_first_name', 'affected_last_name', 'affected_phone', 'donated_at']
    list_filter = ['donated_at']
    search_fields = ['donator__email', 'donator__first_name', 'donator__last_name', 
                    'affected_first_name', 'affected_last_name', 'affected_phone', 'qr_code']
    ordering = ['-donated_at']
    readonly_fields = ['donated_at']
    
    fieldsets = (
        ('Donator Information', {
            'fields': ('donator',)
        }),
        ('Affected User Information', {
            'fields': ('affected_first_name', 'affected_last_name', 'affected_phone')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Donation Details', {
            'fields': ('qr_code', 'supply_needs_fulfilled', 'donated_at', 'notes')
        }),
    )


@admin.register(DonationRating)
class DonationRatingAdmin(admin.ModelAdmin):
    list_display = ['donation_history', 'rating', 'rated_at', 'session_id']
    list_filter = ['rating', 'rated_at']
    search_fields = ['donation_history__donator__email', 'donation_history__affected_first_name', 
                    'donation_history__affected_last_name', 'session_id', 'comment']
    ordering = ['-rated_at']
    readonly_fields = ['rated_at']
    
    fieldsets = (
        ('Donation Reference', {
            'fields': ('donation_history',)
        }),
        ('Rating & Feedback', {
            'fields': ('rating', 'comment')
        }),
        ('Supply Confirmation', {
            'fields': ('supplies_confirmed',)
        }),
        ('Session Info', {
            'fields': ('session_id', 'rated_at')
        }),
    )
