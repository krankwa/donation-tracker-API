from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Location, Donation, DonationTracking, EmergencyRequest, AnonymousLocation, DonationHistory, DonationRating
import bleach


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with input sanitization"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'password2', 'first_name', 'last_name', 
                  'role', 'phone_number', 'address', 'profile_picture', 
                  'is_location_shared', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password2'):
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Sanitize text inputs
        for field in ['first_name', 'last_name', 'address']:
            if field in attrs:
                attrs[field] = bleach.clean(attrs[field], strip=True)
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('password', None)
        validated_data.pop('password2', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile view (limited fields)"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 
                  'phone_number', 'profile_picture', 'is_location_shared']
        read_only_fields = ['id', 'email', 'role']


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location tracking"""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = ['id', 'user', 'user_email', 'user_name', 'latitude', 'longitude', 
                  'timestamp', 'is_current', 'accuracy']
        read_only_fields = ['id', 'user', 'timestamp']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    
    def validate(self, attrs):
        # Validate latitude and longitude ranges
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        
        if latitude and (latitude < -90 or latitude > 90):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90"})
        
        if longitude and (longitude < -180 or longitude > 180):
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180"})
        
        return attrs


class DonationSerializer(serializers.ModelSerializer):
    """Serializer for Donation with input sanitization"""
    
    donator_name = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()
    donator_email = serializers.EmailField(source='donator.email', read_only=True)
    
    class Meta:
        model = Donation
        fields = ['id', 'donator', 'donator_name', 'donator_email', 'recipient', 
                  'recipient_name', 'title', 'description', 'category', 'quantity', 
                  'unit', 'status', 'pickup_location', 'pickup_latitude', 
                  'pickup_longitude', 'delivery_location', 'delivery_latitude', 
                  'delivery_longitude', 'image', 'created_at', 'updated_at', 
                  'delivered_at', 'notes']
        read_only_fields = ['id', 'created_at', 'updated_at', 'donator']
    
    def get_donator_name(self, obj):
        return f"{obj.donator.first_name} {obj.donator.last_name}"
    
    def get_recipient_name(self, obj):
        if obj.recipient:
            return f"{obj.recipient.first_name} {obj.recipient.last_name}"
        return None
    
    def validate(self, attrs):
        # Sanitize text inputs
        for field in ['title', 'description', 'pickup_location', 'delivery_location', 'unit', 'notes']:
            if field in attrs:
                attrs[field] = bleach.clean(attrs[field], strip=True)
        
        # Validate coordinates
        for lat_field, lon_field in [('pickup_latitude', 'pickup_longitude'), 
                                      ('delivery_latitude', 'delivery_longitude')]:
            lat = attrs.get(lat_field)
            lon = attrs.get(lon_field)
            
            if lat and (lat < -90 or lat > 90):
                raise serializers.ValidationError({lat_field: "Latitude must be between -90 and 90"})
            
            if lon and (lon < -180 or lon > 180):
                raise serializers.ValidationError({lon_field: "Longitude must be between -180 and 180"})
        
        # Validate quantity
        if attrs.get('quantity', 0) <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be greater than 0"})
        
        return attrs


class DonationTrackingSerializer(serializers.ModelSerializer):
    """Serializer for Donation tracking history"""
    
    updated_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DonationTracking
        fields = ['id', 'donation', 'status', 'notes', 'latitude', 'longitude', 
                  'updated_by', 'updated_by_name', 'timestamp']
        read_only_fields = ['id', 'timestamp']
    
    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return f"{obj.updated_by.first_name} {obj.updated_by.last_name}"
        return None
    
    def validate(self, attrs):
        # Sanitize notes
        if 'notes' in attrs:
            attrs['notes'] = bleach.clean(attrs['notes'], strip=True)
        
        return attrs


class EmergencyRequestSerializer(serializers.ModelSerializer):
    """Serializer for Emergency requests"""
    
    requester_name = serializers.SerializerMethodField()
    requester_email = serializers.EmailField(source='requester.email', read_only=True)
    requester_phone = serializers.CharField(source='requester.phone_number', read_only=True)
    
    class Meta:
        model = EmergencyRequest
        fields = ['id', 'requester', 'requester_name', 'requester_email', 
                  'requester_phone', 'title', 'description', 'category', 'priority', 
                  'status', 'quantity_needed', 'unit', 'location', 'latitude', 
                  'longitude', 'people_affected', 'created_at', 'updated_at', 
                  'fulfilled_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'requester']
    
    def get_requester_name(self, obj):
        return f"{obj.requester.first_name} {obj.requester.last_name}"
    
    def validate(self, attrs):
        # Sanitize text inputs
        for field in ['title', 'description', 'location', 'unit']:
            if field in attrs:
                attrs[field] = bleach.clean(attrs[field], strip=True)
        
        # Validate coordinates
        lat = attrs.get('latitude')
        lon = attrs.get('longitude')
        
        if lat and (lat < -90 or lat > 90):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90"})
        
        if lon and (lon < -180 or lon > 180):
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180"})
        
        # Validate quantities
        if attrs.get('quantity_needed', 0) <= 0:
            raise serializers.ValidationError({"quantity_needed": "Quantity must be greater than 0"})
        
        if attrs.get('people_affected', 0) <= 0:
            raise serializers.ValidationError({"people_affected": "People affected must be greater than 0"})
        
        return attrs


class AnonymousLocationSerializer(serializers.ModelSerializer):
    """Serializer for anonymous affected user locations (no authentication required)"""
    
    donated_by_user_name = serializers.SerializerMethodField()
    donators_on_the_way = serializers.SerializerMethodField()
    
    class Meta:
        model = AnonymousLocation
        fields = ['id', 'first_name', 'last_name', 'phone', 'facebook', 'email', 'notes', 
                  'photo', 'supply_needs', 'latitude', 'longitude', 'accuracy', 'session_id', 
                  'created_at', 'updated_at', 'last_seen', 'is_active',
                  'qr_code', 'donation_received', 'donated_by_user', 'donated_by_user_name',
                  'donation_timestamp', 'next_request_allowed_at', 'donators_on_the_way']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_seen', 'qr_code', 
                           'donated_by_user_name', 'donators_on_the_way']
    
    def get_donated_by_user_name(self, obj):
        """Get the full name of the donator who completed the donation"""
        if obj.donated_by_user:
            return f"{obj.donated_by_user.first_name} {obj.donated_by_user.last_name}".strip()
        return None
    
    def get_donators_on_the_way(self, obj):
        """Get list of donators currently on their way to this location"""
        from .models import DonatorOnTheWay
        donators = DonatorOnTheWay.objects.filter(location=obj, arrived=False).select_related('donator')
        return [{
            'id': d.donator.id,
            'name': f"{d.donator.first_name} {d.donator.last_name}".strip(),
            'email': d.donator.email,
            'marked_at': d.marked_at
        } for d in donators]
    
    def validate(self, attrs):
        """Validate location coordinates and supply needs"""
        # Validate first_name and last_name are required for new instances
        if not self.instance:
            if not attrs.get('first_name'):
                raise serializers.ValidationError({"first_name": "First name is required"})
            if not attrs.get('last_name'):
                raise serializers.ValidationError({"last_name": "Last name is required"})
        
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')
        
        # Validate photo is required
        if not attrs.get('photo') and not self.instance:
            raise serializers.ValidationError({"photo": "Photo is required to verify your location"})
        
        if latitude and (latitude < -90 or latitude > 90):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90"})
        
        if longitude and (longitude < -180 or longitude > 180):
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180"})
        
        # Sanitize optional text fields
        if attrs.get('notes'):
            attrs['notes'] = bleach.clean(attrs['notes'], strip=True)
        
        if attrs.get('facebook'):
            attrs['facebook'] = bleach.clean(attrs['facebook'], strip=True)
        
        # Validate supply needs structure
        if 'supply_needs' in attrs:
            supply_needs = attrs.get('supply_needs', {})
            
            # If supply_needs is a string (JSON), parse it to dictionary
            if isinstance(supply_needs, str):
                try:
                    import json
                    supply_needs = json.loads(supply_needs)
                    attrs['supply_needs'] = supply_needs  # Update attrs with parsed dict
                except json.JSONDecodeError:
                    raise serializers.ValidationError({
                        "supply_needs": "Invalid JSON format for supply needs"
                    })
            
            allowed_fields = {'water', 'food', 'people_count', 'medical_supplies', 
                            'clothing', 'shelter_materials', 'other'}
            
            # Check for invalid fields
            invalid_fields = set(supply_needs.keys()) - allowed_fields
            if invalid_fields:
                raise serializers.ValidationError({
                    "supply_needs": f"Invalid fields: {', '.join(invalid_fields)}"
                })
            
            # Validate numeric fields are non-negative integers
            numeric_fields = {'water', 'food', 'people_count', 'medical_supplies', 
                            'clothing', 'shelter_materials'}
            for field in numeric_fields:
                if field in supply_needs:
                    try:
                        value = int(supply_needs[field])
                        if value < 0:
                            raise ValueError()
                        supply_needs[field] = value
                    except (ValueError, TypeError):
                        raise serializers.ValidationError({
                            "supply_needs": f"{field} must be a non-negative integer"
                        })
            
            # Sanitize 'other' field if present
            if 'other' in supply_needs:
                supply_needs['other'] = bleach.clean(str(supply_needs['other']), strip=True)
        
        return attrs


class DonationHistorySerializer(serializers.ModelSerializer):
    """Serializer for QR-based donation history"""
    
    donator_name = serializers.SerializerMethodField()
    donator_email = serializers.EmailField(source='donator.email', read_only=True)
    
    class Meta:
        model = DonationHistory
        fields = [
            'id', 'donator', 'donator_name', 'donator_email',
            'affected_first_name', 'affected_last_name', 'affected_phone',
            'latitude', 'longitude', 'supply_needs_fulfilled',
            'qr_code', 'donated_at', 'notes'
        ]
        read_only_fields = ['id', 'donated_at']
    
    def get_donator_name(self, obj):
        return f"{obj.donator.first_name} {obj.donator.last_name}"


class DonationRatingSerializer(serializers.ModelSerializer):
    """Serializer for donation ratings and supply confirmations"""
    
    donation_info = serializers.SerializerMethodField()
    
    class Meta:
        model = DonationRating
        fields = [
            'id', 'donation_history', 'donation_info', 'rating', 'comment',
            'supplies_confirmed', 'rated_at', 'session_id'
        ]
        read_only_fields = ['id', 'rated_at']
    
    def get_donation_info(self, obj):
        return {
            'donator_name': f"{obj.donation_history.donator.first_name} {obj.donation_history.donator.last_name}",
            'donator_email': obj.donation_history.donator.email,
            'donated_at': obj.donation_history.donated_at,
            'supply_needs_fulfilled': obj.donation_history.supply_needs_fulfilled
        }
    
    def validate_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5 stars.")
        return value
    
    def validate_supplies_confirmed(self, value):
        if value:
            # Sanitize text fields in supplies confirmation
            if 'other_items' in value:
                value['other_items'] = bleach.clean(str(value['other_items']), strip=True)
        return value
