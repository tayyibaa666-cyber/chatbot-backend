from django.db import models
from django.contrib.auth.models import User
import uuid


# ============================================================
# 1. Chatbot (Main Entity)
# ============================================================
class Chatbot(models.Model):
    """
    Represents a single chatbot created by a user.
    This is the main entity trained using website crawling and file uploads.
    """
    STATUS_CHOICES = [
        ('fetching', 'Fetching'),
        ('processing', 'Processing'),
        ('training', 'Training'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chatbots")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    website_url = models.URLField(blank=True, null=True)
    system_prompt = models.TextField(default="You are a helpful AI assistant.")

    # ✅ FIX: default must exist in STATUS_CHOICES
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='fetching'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


# ============================================================
# 2. Documents (Knowledge Base)
# ============================================================
class Document(models.Model):
    """
    Stores extracted content from URLs and uploaded files.
    Supports deduplication by content hash and normalized URL.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    # URL sources
    source_url = models.URLField(blank=True, null=True)
    normalized_url = models.URLField(blank=True, null=True, db_index=True)

    # File upload
    file_upload = models.FileField(
        upload_to="chatbot_docs/%Y/%m/%d/",
        blank=True,
        null=True
    )

    # Extracted text content
    raw_content = models.TextField()

    # Content deduplication
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True
    )

    # Page type detection
    page_type = models.CharField(
        max_length=50,
        blank=True,
        default="generic",
        choices=[
            ('homepage', 'Homepage'),
            ('about', 'About'),
            ('contact', 'Contact'),
            ('pricing', 'Pricing'),
            ('services', 'Services'),
            ('faq', 'FAQ'),
            ('blog', 'Blog'),
            ('generic', 'Generic'),
        ]
    )

    # Optional metadata
    title = models.CharField(max_length=500, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    http_status = models.IntegerField(null=True, blank=True)
    error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('chatbot', 'normalized_url')
        indexes = [
            models.Index(fields=['chatbot', 'content_hash']),
            models.Index(fields=['chatbot', 'page_type']),
        ]

    def __str__(self):
        source = (
            self.source_url
            if self.source_url
            else (self.file_upload.name if self.file_upload else "Unknown")
        )
        return f"Doc: {source}"


# ============================================================
# 3. IngestionJob (Training Progress Tracker)
# ============================================================
class IngestionJob(models.Model):
    """
    Tracks the progress of bot training jobs.
    Similar to Chatbase's ingestion job tracking.
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('processing', 'Processing'),
        ('training', 'Training'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name="jobs"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    message = models.TextField(blank=True, default="")
    progress_current = models.IntegerField(default=0)
    progress_total = models.IntegerField(default=0)

    # optional fields
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['chatbot', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Job {self.id} ({self.status})"