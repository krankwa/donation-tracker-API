from rest_framework import viewsets, status, permissions, parsers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .models import User, Location, Donation, DonationTracking, EmergencyRequest, AnonymousLocation, DonationHistory, DonationRating
from .serializers import (
    UserSerializer, UserProfileSerializer, LocationSerializer,
    DonationSerializer, DonationTrackingSerializer, EmergencyRequestSerializer,
    AnonymousLocationSerializer, DonationHistorySerializer, DonationRatingSerializer
)
from .permissions import IsDonator, IsAffected, IsOwnerOrReadOnly


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login user and return JWT tokens"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Please provide both email and password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def register_affected(request):
    """Register an affected user with phone number only (no password)"""
    phone_number = request.data.get('phone_number')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    address = request.data.get('address', '')
    
    if not phone_number or not first_name or not last_name:
        return Response(
            {'error': 'Phone number, first name, and last name are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user with this phone number already exists
    if User.objects.filter(phone_number=phone_number).exists():
        return Response(
            {'error': 'User with this phone number already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create affected user (no password, no email required)
    user = User.objects.create(
        email=f"{phone_number}@affected.local",  # Dummy email
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role='affected',
        address=address
    )
    user.set_unusable_password()  # No password authentication
    user.save()
    
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_affected(request):
    """Login affected user with phone number only (no password)"""
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response(
            {'error': 'Please provide phone number'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(phone_number=phone_number, role='affected')
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response(
            {'error': 'No affected user found with this phone number'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User CRUD operations"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter users based on role if specified"""
        queryset = User.objects.all()
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset
    
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return UserProfileSerializer
        return UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_location_sharing(self, request, pk=None):
        """Toggle location sharing for affected users"""
        user = self.get_object()
        
        if user.id != request.user.id:
            return Response(
                {'error': 'You can only toggle your own location sharing'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user.is_location_shared = not user.is_location_shared
        user.save()
        
        return Response({
            'is_location_shared': user.is_location_shared
        })


class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for Location tracking"""
    queryset = Location.objects.select_related('user').all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter locations based on permissions"""
        # Use select_related for user to reduce queries
        queryset = Location.objects.select_related('user').all()
        
        # Only show locations of users who have enabled location sharing
        queryset = queryset.filter(user__is_location_shared=True)
        
        # Filter by user if specified
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter current locations only
        current_only = self.request.query_params.get('current_only', None)
        if current_only == 'true':
            queryset = queryset.filter(is_current=True)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create location for current user"""
        # Mark previous locations as not current
        Location.objects.filter(user=self.request.user, is_current=True).update(is_current=False)
        
        # Save new location
        serializer.save(user=self.request.user, is_current=True)
    
    @action(detail=False, methods=['get'])
    def affected_users(self, request):
        """Get current locations of all affected users with shared location"""
        locations = Location.objects.filter(
            user__role='affected',
            user__is_location_shared=True,
            is_current=True
        )
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)


class DonationViewSet(viewsets.ModelViewSet):
    """ViewSet for Donation management"""
    queryset = Donation.objects.select_related('donator', 'recipient').all()
    serializer_class = DonationSerializer
    permission_classes = [IsAuthenticated]
    
    @method_decorator(cache_page(60 * 2))  # Cache for 2 minutes
    def list(self, request, *args, **kwargs):
        """Cached list view"""
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        """Filter donations based on user role and parameters"""
        # Use select_related for foreign keys to reduce queries
        queryset = Donation.objects.select_related('donator', 'recipient').all()
        
        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by user role
        if self.request.user.role == 'donator':
            # Donators see their own donations
            my_donations = self.request.query_params.get('my_donations', None)
            if my_donations == 'true':
                queryset = queryset.filter(donator=self.request.user)
        elif self.request.user.role == 'affected':
            # Affected users see available donations or their assigned ones
            my_donations = self.request.query_params.get('my_donations', None)
            if my_donations == 'true':
                queryset = queryset.filter(recipient=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create donation with current user as donator"""
        if self.request.user.role != 'donator':
            raise permissions.PermissionDenied("Only donators can create donations")
        
        serializer.save(donator=self.request.user)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update donation status"""
        donation = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions
        if donation.donator != request.user and donation.recipient != request.user:
            return Response(
                {'error': 'You do not have permission to update this donation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update donation
        donation.status = new_status
        if new_status == 'delivered':
            donation.delivered_at = timezone.now()
        donation.save()
        
        # Create tracking entry
        DonationTracking.objects.create(
            donation=donation,
            status=new_status,
            notes=notes,
            updated_by=request.user
        )
        
        serializer = self.get_serializer(donation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_recipient(self, request, pk=None):
        """Assign donation to an affected user"""
        donation = self.get_object()
        recipient_id = request.data.get('recipient_id')
        
        if donation.donator != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Only the donator can assign recipients'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            recipient = User.objects.get(id=recipient_id, role='affected')
            donation.recipient = recipient
            donation.status = 'approved'
            donation.save()
            
            serializer = self.get_serializer(donation)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'Recipient not found or not an affected user'},
                status=status.HTTP_404_NOT_FOUND
            )


class DonationTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing donation tracking history"""
    queryset = DonationTracking.objects.all()
    serializer_class = DonationTrackingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter tracking by donation"""
        queryset = DonationTracking.objects.select_related('donation', 'updated_by').all()
        
        donation_id = self.request.query_params.get('donation', None)
        if donation_id:
            queryset = queryset.filter(donation_id=donation_id)
        
        return queryset


class EmergencyRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Emergency requests"""
    queryset = EmergencyRequest.objects.all()
    serializer_class = EmergencyRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter emergency requests"""
        queryset = EmergencyRequest.objects.select_related('requester').all()
        
        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        # My requests
        my_requests = self.request.query_params.get('my_requests', None)
        if my_requests == 'true':
            queryset = queryset.filter(requester=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create emergency request with current user as requester"""
        if self.request.user.role != 'affected':
            raise permissions.PermissionDenied("Only affected users can create emergency requests")
        
        serializer.save(requester=self.request.user)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update emergency request status"""
        emergency_request = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        emergency_request.status = new_status
        if new_status == 'fulfilled':
            emergency_request.fulfilled_at = timezone.now()
        emergency_request.save()
        
        serializer = self.get_serializer(emergency_request)
        return Response(serializer.data)


class AnonymousLocationViewSet(viewsets.ModelViewSet):
    """ViewSet for anonymous affected user locations (no authentication required)"""
    queryset = AnonymousLocation.objects.filter(is_active=True)
    serializer_class = AnonymousLocationSerializer
    permission_classes = []  # No authentication required
    throttle_classes = []  # Disable throttling for this endpoint to support frequent polling
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    
    def get_queryset(self):
        """Get active anonymous locations"""
        # Only return locations updated in the last 24 hours
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        recent_locations = AnonymousLocation.objects.filter(
            is_active=True,
            last_seen__gte=cutoff_time
        )
        
        return recent_locations
    
    def create(self, request, *args, **kwargs):
        """Create or update anonymous location with photo and supply needs"""
        print("\n=== Anonymous Location Create Request ===")
        print(f"Request data keys: {request.data.keys()}")
        print(f"Phone: {request.data.get('phone')}")
        print(f"Session ID: {request.data.get('session_id')}")
        print(f"Photo present: {'photo' in request.data}")
        print(f"Files: {request.FILES.keys() if hasattr(request, 'FILES') else 'No FILES'}")
        
        # Debug photo details
        if 'photo' in request.FILES:
            photo = request.FILES['photo']
            print(f"Photo from FILES - Name: {photo.name}, Size: {photo.size}, Type: {type(photo)}")
        if 'photo' in request.data:
            photo_data = request.data['photo']
            print(f"Photo from DATA - Type: {type(photo_data)}, Value: {str(photo_data)[:100]}...")
        
        print(f"Content-Type header: {request.content_type}")
        print(f"Request method: {request.method}")
        
        phone = request.data.get('phone')
        session_id = request.data.get('session_id', '')
        
        # Check if user is restricted (3-hour cooldown)
        recent_donation = AnonymousLocation.objects.filter(
            phone=phone,
            donation_received=True,
            next_request_allowed_at__gt=timezone.now()
        ).first()
        
        if recent_donation:
            time_remaining = (recent_donation.next_request_allowed_at - timezone.now()).total_seconds()
            hours_remaining = int(time_remaining // 3600)
            minutes_remaining = int((time_remaining % 3600) // 60)
            
            print(f"User restricted! Phone: {phone}, Time remaining: {hours_remaining}h {minutes_remaining}m")
            
            return Response({
                'error': 'You recently received a donation. Please wait before requesting help again.',
                'restriction': {
                    'restricted': True,
                    'next_allowed_at': recent_donation.next_request_allowed_at,
                    'time_remaining_seconds': int(time_remaining),
                    'message': f'You can request help again in {hours_remaining} hour(s) and {minutes_remaining} minute(s)'
                }
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Only find existing location by session_id (not by phone)
        # This allows multiple users with same phone to have separate locations
        existing = None
        if session_id:
            existing = AnonymousLocation.objects.filter(
                session_id=session_id,
                is_active=True
            ).first()
            print(f"Looking for existing session: {session_id}, Found: {existing is not None}")
        
        if existing:
            # Update existing location
            print(f"Updating existing location: {existing.id}")
            
            # Fix photo data - use the file from request.FILES instead of request.data
            data = request.data.copy()
            if 'photo' in request.FILES:
                data['photo'] = request.FILES['photo']
                print(f"Using photo from FILES for update: {request.FILES['photo']}")
            
            serializer = self.get_serializer(existing, data=data, partial=True)
            try:
                serializer.is_valid(raise_exception=True)
                serializer.save(last_seen=timezone.now())
                print("Update successful!")
                return Response(serializer.data)
            except Exception as e:
                print(f"Update validation failed: {str(e)}")
                if hasattr(serializer, '_errors'):
                    print(f"Serializer errors: {serializer._errors}")
                raise
        else:
            # Create new location
            print("Creating new location")
            
            # Fix photo data - use the file from request.FILES instead of request.data
            data = request.data.copy()
            if 'photo' in request.FILES:
                data['photo'] = request.FILES['photo']
                print(f"Using photo from FILES: {request.FILES['photo']}")
            
            serializer = self.get_serializer(data=data)
            try:
                serializer.is_valid(raise_exception=True)
                location = serializer.save(last_seen=timezone.now())
                
                # Generate unique QR code for this location
                import uuid
                location.qr_code = f"LOC-{uuid.uuid4().hex[:12].upper()}"
                location.save()
                
                print(f"Create successful! ID: {location.id}, QR Code: {location.qr_code}, last_seen: {location.last_seen}")
                
                # Refresh serializer data to include qr_code
                serializer = self.get_serializer(location)
                return Response(serializer.data, status=201)
            except Exception as e:
                print(f"Create validation failed: {str(e)}")
                if hasattr(serializer, '_errors'):
                    print(f"Serializer errors: {serializer._errors}")
                raise
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active anonymous locations (public endpoint)"""
        locations = self.get_queryset()
        serializer = self.get_serializer(locations, many=True)
        response = Response(serializer.data)
        
        # Add cache-busting headers to ensure fresh data
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate anonymous location (stop sharing) - completely deletes the data"""
        print(f"\n=== Deactivate Location Request ===")
        print(f"Location ID: {pk}")
        print(f"Request method: {request.method}")
        
        from django.db import transaction
        
        try:
            # Use atomic transaction for immediate commit
            with transaction.atomic():
                location = self.get_object()
                phone = location.phone
                location_id = location.id
                print(f"Found location: ID={location_id}, Phone={phone}")
                
                # Delete immediately
                location.delete()
                print(f"Successfully deleted anonymous location ID={location_id} for phone: {phone}")
            
            # Force database commit and clear any caches
            from django.db import connection
            connection.close()
            
            response = Response({'status': 'location sharing stopped and data deleted'})
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        except Exception as e:
            print(f"Error deactivating location: {str(e)}")
            raise
    
    @action(detail=True, methods=['post'])
    def mark_on_the_way(self, request, pk=None):
        """Mark donator as 'on the way' to this location"""
        from .models import DonatorOnTheWay
        from django.db import transaction
        
        print(f"\n=== Mark On The Way Request ===")
        print(f"Location ID: {pk}")
        print(f"User: {request.user}")
        
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        location = self.get_object()
        
        # Check if location already received donation
        if location.donation_received:
            return Response(
                {'error': 'This location has already received a donation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Create or update donator on the way record
                donator_entry, created = DonatorOnTheWay.objects.get_or_create(
                    location=location,
                    donator=request.user,
                    defaults={'arrived': False, 'is_tracking': True}
                )
                
                if not created:
                    # If already exists, reset status and enable tracking
                    donator_entry.arrived = False
                    donator_entry.is_tracking = True
                    donator_entry.marked_at = timezone.now()
                    donator_entry.save()
                
                print(f"Donator {request.user.email} marked as on the way to location {location.id}")
                
                # Broadcast that donator is on the way via WebSocket
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    # Create display name from first_name + last_name, fallback to email username
                    display_name = f"{request.user.first_name} {request.user.last_name}".strip()
                    if not display_name:
                        display_name = request.user.username or request.user.email.split('@')[0]
                    
                    tracking_data = {
                        'locationId': location.id,
                        'donatorId': request.user.id,
                        'donatorUsername': request.user.username or request.user.email.split('@')[0],
                        'donatorFirstName': request.user.first_name,
                        'donatorLastName': request.user.last_name,
                        'message': f"{display_name} is on the way for supplies",
                        'status': 'tracking_started',
                        'timestamp': donator_entry.marked_at.isoformat()
                    }
                    
                    async_to_sync(channel_layer.group_send)(
                        'locations',
                        {
                            'type': 'donator_tracking_update',
                            'data': tracking_data
                        }
                    )
                
                # Get updated location with donators
                serializer = self.get_serializer(location)
                
                return Response({
                    'status': 'marked as on the way',
                    'location': serializer.data,
                    'message': 'Please contact the affected user first to verify the location'
                })
        except Exception as e:
            print(f"Error marking on the way: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def scan_qr_code(self, request):
        """Scan QR code and mark donation as received"""
        from datetime import timedelta
        from django.db import transaction
        from .models import DonatorOnTheWay, DonationHistory
        
        print(f"\n=== QR Code Scan Request ===")
        print(f"User: {request.user}")
        print(f"QR Code: {request.data.get('qr_code')}")
        
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        qr_code = request.data.get('qr_code')
        if not qr_code:
            return Response(
                {'error': 'QR code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            location = AnonymousLocation.objects.get(qr_code=qr_code, is_active=True)
        except AnonymousLocation.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired QR code'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already received donation
        if location.donation_received:
            return Response(
                {'error': 'This location has already received a donation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Mark location as received donation
                location.donation_received = True
                location.donated_by_user = request.user
                location.donation_timestamp = timezone.now()
                location.next_request_allowed_at = timezone.now() + timedelta(hours=3)
                location.is_active = False  # Deactivate location after donation
                location.save()
                
                # Mark donator as arrived
                DonatorOnTheWay.objects.filter(
                    location=location,
                    donator=request.user
                ).update(arrived=True)
                
                # Create donation history record
                donation_history = DonationHistory.objects.create(
                    donator=request.user,
                    affected_first_name=location.first_name,
                    affected_last_name=location.last_name,
                    affected_phone=location.phone,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    supply_needs_fulfilled=location.supply_needs,
                    qr_code=qr_code
                )
                
                # Send real-time notification to affected user
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        'locations',
                        {
                            'type': 'qr_scan_notification',
                            'data': {
                                'session_id': location.session_id,
                                'donation_history_id': donation_history.id,
                                'donator_name': f"{request.user.first_name} {request.user.last_name}",
                                'donator_email': request.user.email,
                                'supply_needs_fulfilled': location.supply_needs,
                                'qr_code': qr_code,
                                'donated_at': donation_history.donated_at.isoformat()
                            }
                        }
                    )
                
                print(f"Donation completed! Location {location.id} received donation from {request.user.email}")
                print(f"Next request allowed at: {location.next_request_allowed_at}")
                print(f"Donation history record created and notification sent")
                
                serializer = self.get_serializer(location)
                
                return Response({
                    'status': 'donation recorded successfully',
                    'location': serializer.data,
                    'message': 'Thank you for your donation!',
                    'next_request_allowed_at': location.next_request_allowed_at
                })
        except Exception as e:
            print(f"Error processing QR code scan: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DonationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing donation history from QR-based donations.
    GET /api/donation-history/ - List all donations (public)
    GET /api/donation-history/my-donations/ - Authenticated donator's personal history
    """
    queryset = DonationHistory.objects.all()
    serializer_class = DonationHistorySerializer
    permission_classes = [AllowAny]  # Public viewing
    
    def get_queryset(self):
        """Return all donations, ordered by most recent"""
        return DonationHistory.objects.select_related('donator').order_by('-donated_at')
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_donations(self, request):
        """Get authenticated donator's donation history"""
        if request.user.role != 'donator':
            return Response(
                {'error': 'Only donators can view their donation history'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        donations = DonationHistory.objects.filter(
            donator=request.user
        ).order_by('-donated_at')
        
        serializer = self.get_serializer(donations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def donator_acknowledgments(self, request):
        """Get detailed donation history with supply confirmations for a donator"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        
        donations = DonationHistory.objects.filter(donator=request.user).order_by('-donated_at')
        
        acknowledgments = []
        for donation in donations:
            try:
                rating = donation.rating
                supplies_confirmed = rating.supplies_confirmed if rating else {}
                user_rating = rating.rating if rating else None
                user_comment = rating.comment if rating else ""
                rated_at = rating.rated_at if rating else None
            except:
                supplies_confirmed = {}
                user_rating = None
                user_comment = ""
                rated_at = None
            
            acknowledgments.append({
                'donation_id': donation.id,
                'affected_user': f"{donation.affected_first_name} {donation.affected_last_name}",
                'location': {
                    'latitude': float(donation.latitude),
                    'longitude': float(donation.longitude)
                },
                'donated_at': donation.donated_at,
                'supplies_donated': donation.supply_needs_fulfilled,  # Now reflects actual supplies donated
                'supplies_received': {
                    'water': supplies_confirmed.get('water_received', 0),
                    'food': supplies_confirmed.get('food_received', 0),
                    'medical_supplies': supplies_confirmed.get('medical_supplies_received', 0),
                    'clothing': supplies_confirmed.get('clothing_received', 0),
                    'shelter_materials': supplies_confirmed.get('shelter_materials_received', 0),
                    'other_items': supplies_confirmed.get('other_items', ''),
                    'all_supplies_received': supplies_confirmed.get('all_supplies_received', False)
                },
                'user_feedback': {
                    'rating': user_rating,
                    'comment': user_comment,
                    'rated_at': rated_at
                },
                'has_confirmation': rating is not None
            })
        
        return Response({
            'total_donations': donations.count(),
            'acknowledgments': acknowledgments
        })

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def contributors_ranking(self, request):
        """Get ranking of top contributors based on QR donation activity"""
        from django.db.models import Count, Q, Avg
        from collections import defaultdict
        
        # Get donation counts per donator
        donator_stats = DonationHistory.objects.values(
            'donator__id', 'donator__first_name', 'donator__last_name', 'donator__email'
        ).annotate(
            total_donations=Count('id')
        ).order_by('-total_donations')
        
        # Calculate supply contributions for each donator
        contributors = []
        for i, donator_data in enumerate(donator_stats[:10]):  # Top 10 contributors
            donator_id = donator_data['donator__id']
            
            # Get all donations by this donator
            donations = DonationHistory.objects.filter(donator_id=donator_id)
            
            # Calculate average rating from affected users
            ratings_queryset = DonationRating.objects.filter(
                donation_history__donator_id=donator_id
            ).aggregate(
                avg_rating=Avg('rating'),
                total_ratings=Count('id')
            )
            
            avg_rating = ratings_queryset['avg_rating']
            total_ratings = ratings_queryset['total_ratings']
            
            # Round average rating to 1 decimal place
            if avg_rating is not None:
                avg_rating = round(avg_rating, 1)
            
            # Sum up supply contributions (promised vs confirmed)
            total_people_helped = 0
            promised_supplies = {'water': 0, 'food': 0, 'medical_supplies': 0, 'clothing': 0, 'shelter_materials': 0}
            confirmed_supplies = {'water': 0, 'food': 0, 'medical_supplies': 0, 'clothing': 0, 'shelter_materials': 0}
            
            for donation in donations:
                # Promised supplies (what was in the QR scan)
                supplies = donation.supply_needs_fulfilled or {}
                total_people_helped += supplies.get('people_count', 0)
                promised_supplies['water'] += supplies.get('water', 0)
                promised_supplies['food'] += supplies.get('food', 0)
                promised_supplies['medical_supplies'] += supplies.get('medical_supplies', 0)
                promised_supplies['clothing'] += supplies.get('clothing', 0)
                promised_supplies['shelter_materials'] += supplies.get('shelter_materials', 0)
                
                # Confirmed supplies (what affected user actually received)
                try:
                    rating = donation.rating
                    if rating and rating.supplies_confirmed:
                        confirmed = rating.supplies_confirmed
                        confirmed_supplies['water'] += confirmed.get('water_received', 0)
                        confirmed_supplies['food'] += confirmed.get('food_received', 0)
                        confirmed_supplies['medical_supplies'] += confirmed.get('medical_supplies_received', 0)
                        confirmed_supplies['clothing'] += confirmed.get('clothing_received', 0)
                        confirmed_supplies['shelter_materials'] += confirmed.get('shelter_materials_received', 0)
                except:
                    # No rating yet, skip confirmed supplies
                    pass
            
            contributors.append({
                'rank': i + 1,
                'donator_id': donator_id,
                'donator_name': f"{donator_data['donator__first_name']} {donator_data['donator__last_name']}",
                'donator_email': donator_data['donator__email'],
                'total_donations': donator_data['total_donations'],
                'total_people_helped': total_people_helped,
                'average_rating': avg_rating,
                'total_ratings': total_ratings,
                'supplies_promised': promised_supplies,
                'supplies_confirmed': confirmed_supplies,
                'supply_fulfillment_rate': self._calculate_fulfillment_rate(promised_supplies, confirmed_supplies)
            })
        
        return Response(contributors)
    
    def _calculate_fulfillment_rate(self, promised, confirmed):
        """Calculate the percentage of promised supplies that were actually delivered"""
        total_promised = sum(promised.values())
        total_confirmed = sum(confirmed.values())
        
        if total_promised == 0:
            return 100.0 if total_confirmed == 0 else 0.0
        
        return round((total_confirmed / total_promised) * 100, 1)


class DonationRatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for donation ratings and supply confirmations.
    POST /api/donation-ratings/ - Create rating/confirmation (by session_id)
    GET /api/donation-ratings/ - List all ratings (admin)
    """
    queryset = DonationRating.objects.all()
    serializer_class = DonationRatingSerializer
    permission_classes = [AllowAny]  # Allow anonymous affected users to rate
    
    def create(self, request, *args, **kwargs):
        """Create rating and supply confirmation from affected user"""
        donation_history_id = request.data.get('donation_history_id')
        session_id = request.data.get('session_id')
        
        if not donation_history_id or not session_id:
            return Response(
                {'error': 'donation_history_id and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            donation_history = DonationHistory.objects.get(id=donation_history_id)
        except DonationHistory.DoesNotExist:
            return Response(
                {'error': 'Donation history not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if rating already exists
        if hasattr(donation_history, 'rating'):
            return Response(
                {'error': 'Rating already exists for this donation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create rating with session validation
        data = request.data.copy()
        data['donation_history'] = donation_history_id
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            rating = serializer.save()
            
            # Update DonationHistory with actual supplies received
            supplies_confirmed = rating.supplies_confirmed
            if supplies_confirmed:
                # Convert the supplies_confirmed format to supply_needs_fulfilled format
                actual_supplies = {
                    'water': supplies_confirmed.get('water_received', 0),
                    'food': supplies_confirmed.get('food_received', 0),
                    'medical_supplies': supplies_confirmed.get('medical_supplies_received', 0),
                    'clothing': supplies_confirmed.get('clothing_received', 0),
                    'shelter_materials': supplies_confirmed.get('shelter_materials_received', 0),
                }
                
                # Only include non-zero values
                actual_supplies = {k: v for k, v in actual_supplies.items() if v > 0}
                
                # Add other items if provided
                if supplies_confirmed.get('other_items'):
                    actual_supplies['other'] = supplies_confirmed.get('other_items')
                
                # Update the donation history to reflect actual supplies received
                donation_history.supply_needs_fulfilled = actual_supplies
                donation_history.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def location_update(request):
    """Handle real-time location updates from donators on the way"""
    from .models import LocationUpdate, DonatorOnTheWay
    from django.utils import timezone
    
    try:
        data = request.data
        location_id = data.get('locationId')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy', 0)
        
        print(f"\n=== Location Update Request ===")
        print(f"Location ID: {location_id}")
        print(f"User: {request.user}")
        print(f"Coordinates: {latitude}, {longitude}")
        print(f"Accuracy: {accuracy}m")
        
        if not all([location_id, latitude, longitude]):
            return Response(
                {'error': 'locationId, latitude, and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find the donator on the way record
        try:
            donator_entry = DonatorOnTheWay.objects.get(
                location_id=location_id,
                donator=request.user,
                is_tracking=True
            )
        except DonatorOnTheWay.DoesNotExist:
            return Response(
                {'error': 'No active tracking found for this location'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create location update record
        location_update = LocationUpdate.objects.create(
            donator_on_the_way=donator_entry,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy
        )
        
        # Update the donator entry with last update time
        donator_entry.last_location_update = timezone.now()
        donator_entry.save()
        
        print(f"Location update saved for donator {request.user.email}")
        
        # Broadcast location update via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            # Create display name from first_name + last_name, fallback to email username
            display_name = f"{request.user.first_name} {request.user.last_name}".strip()
            if not display_name:
                display_name = request.user.username or request.user.email.split('@')[0]
            
            tracking_data = {
                'locationId': location_id,
                'donatorId': request.user.id,
                'donatorUsername': request.user.username or request.user.email.split('@')[0],
                'donatorFirstName': request.user.first_name,
                'donatorLastName': request.user.last_name,
                'latitude': float(latitude),
                'longitude': float(longitude),
                'accuracy': accuracy,
                'timestamp': location_update.timestamp.isoformat(),
                'message': f"{display_name} is on the way for supplies"
            }
            
            async_to_sync(channel_layer.group_send)(
                'locations',
                {
                    'type': 'donator_tracking_update',
                    'data': tracking_data
                }
            )
        
        return Response({
            'status': 'success',
            'message': 'Location update received',
            'timestamp': location_update.timestamp
        })
        
    except Exception as e:
        print(f"Error processing location update: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_tracking(request):
    """Stop location tracking for a donator"""
    from .models import DonatorOnTheWay
    
    try:
        location_id = request.data.get('locationId')
        
        print(f"\n=== Stop Tracking Request ===")
        print(f"Location ID: {location_id}")
        print(f"User: {request.user}")
        
        if not location_id:
            return Response(
                {'error': 'locationId is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find and update the donator on the way record
        try:
            donator_entry = DonatorOnTheWay.objects.get(
                location_id=location_id,
                donator=request.user
            )
            donator_entry.is_tracking = False
            donator_entry.save()
            
            print(f"Tracking stopped for donator {request.user.email}")
            
            # Broadcast tracking stop via WebSocket
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                # Create display name from first_name + last_name, fallback to email username
                display_name = f"{request.user.first_name} {request.user.last_name}".strip()
                if not display_name:
                    display_name = request.user.username or request.user.email.split('@')[0]
                
                tracking_data = {
                    'locationId': location_id,
                    'donatorId': request.user.id,
                    'donatorUsername': request.user.username or request.user.email.split('@')[0],
                    'status': 'tracking_stopped',
                    'message': f"{display_name} has stopped location sharing",
                }
                
                async_to_sync(channel_layer.group_send)(
                    'locations',
                    {
                        'type': 'donator_tracking_update',
                        'data': tracking_data
                    }
                )
            
            return Response({
                'status': 'success',
                'message': 'Location tracking stopped'
            })
            
        except DonatorOnTheWay.DoesNotExist:
            return Response(
                {'error': 'No tracking record found for this location'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except Exception as e:
        print(f"Error stopping tracking: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



