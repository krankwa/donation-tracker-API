from rest_framework import permissions


class IsDonator(permissions.BasePermission):
    """Permission class to check if user is a donator"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'donator'


class IsAffected(permissions.BasePermission):
    """Permission class to check if user is affected"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'affected'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permission class to allow owners to edit and others to read only"""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'donator'):
            return obj.donator == request.user
        elif hasattr(obj, 'requester'):
            return obj.requester == request.user
        
        return False
