"""
API URLs Configuration - COMPLETE AND FIXED
File: api/urls.py

All endpoints tested and working properly
"""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    RegisterView,
    health_check,
    ListBotsView,
    CreateBotView,
    DeleteBotView,
    DeleteFailedBotsView,
    BotStatusView,
    IngestionJobStatusView,
    UploadDocumentView,
    ChatView,
    VerifyDataIsolationView
)

app_name = 'api'

urlpatterns = [
    # =========================================================================
    # PUBLIC ENDPOINTS (No authentication required)
    # =========================================================================
    
    # Health check - test if backend is working
    path("health/", 
         health_check, 
         name="health"),
    
    # User registration - create account
    path("register/", 
         RegisterView.as_view(), 
         name="register"),
    
    # Login - get authentication token
    path("auth/token/", 
         obtain_auth_token, 
         name="api_token_auth"),


    # =========================================================================
    # PROTECTED ENDPOINTS (Authentication required)
    # =========================================================================
    
    # Bot Management
    path("bots/", 
         ListBotsView.as_view(), 
         name="list_bots"),
    
    path("bots/create/", 
         CreateBotView.as_view(), 
         name="create_bot"),

    path("bots/failed/delete/", 
         DeleteFailedBotsView.as_view(), 
         name="delete_failed_bots"),


    # Bot-specific operations
    path("bots/<uuid:bot_id>/upload/", 
         UploadDocumentView.as_view(), 
         name="upload_doc"),
    
    path("bots/<uuid:bot_id>/chat/", 
         ChatView.as_view(), 
         name="chat"),
    
    path("bots/<uuid:bot_id>/status/", 
         BotStatusView.as_view(), 
         name="bot_status"),
    
    path("bots/<uuid:bot_id>/jobs/<uuid:job_id>/status/", 
         IngestionJobStatusView.as_view(), 
         name="job_status"),
    
    path("bots/<uuid:bot_id>/verify/", 
         VerifyDataIsolationView.as_view(), 
         name="verify_isolation"),
    
    path("bots/<uuid:bot_id>/delete/", 
         DeleteBotView.as_view(), 
         name="delete_bot"),
]