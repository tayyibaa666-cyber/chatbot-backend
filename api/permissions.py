"""
Custom Permission Classes for Chatbot API
File location: api/permissions.py

This file defines custom permissions for checking if users own bots.
"""

from rest_framework.permissions import BasePermission
from .models import Chatbot


class IsBotOwner(BasePermission):
    """
    Custom permission to check if the user owns the bot.
    Used to ensure users can only access their own bots.
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        
        Args:
            request: The HTTP request
            view: The view being called
            obj: The Chatbot object being accessed
        
        Returns:
            bool: True if user owns the bot, False otherwise
        """
        # Check if the bot's user matches the request user
        return obj.user == request.user