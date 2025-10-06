"""
Custom adapters for django-allauth social authentication
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email, user_field


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social authentication, especially for Facebook
    users without email addresses in development mode.
    """
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user instance with data from social provider.
        Generate placeholder email if not provided by the provider (Facebook in dev mode).
        """
        user = super().populate_user(request, sociallogin, data)
        
        # If no email provided by social provider, create a placeholder
        if not user.email:
            provider = sociallogin.account.provider
            uid = sociallogin.account.uid
            # Generate a unique placeholder email
            user.email = f"{provider}_{uid}@noemail.local"
        
        return user
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticated via a social provider,
        but before the login is actually processed.
        """
        # If user is already logged in, link the social account
        if request.user.is_authenticated:
            return
        
        # Check if user with this email already exists
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(email=email)
                # Connect this social account to the existing user
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
