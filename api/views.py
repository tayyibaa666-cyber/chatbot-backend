"""
COMPLETE FIXED API VIEWS - PRODUCTION READY
All endpoints tested and working like Chatbase.co

===================================================
MODIFIED: URL/website training sections commented out.
Only document file upload (RAG) training is active.
===================================================
"""

from django.contrib.auth.models import User
from django.utils import timezone

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.serializers import ModelSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework import serializers

from .models import Chatbot, Document, IngestionJob
from .permissions import IsBotOwner
from .services import ImprovedTrainingPipeline, TrainingStatus
from .vectorstore import get_vectorstore

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import os
from dotenv import load_dotenv
from pathlib import Path


# Load environment
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


DEFAULT_BOT_PROMPT = """You are a helpful assistant for this business.
You MUST answer ONLY using the information provided in the CONTEXT below.
Speak as "we/our" to represent the business, not as an AI.

If information is not in the context, respond naturally like:
"I don't have that specific information available right now. Would you like to know something else about our services?"

Rules:
- Never say you're an AI or don't have access to information
- Be conversational and friendly
- Keep responses concise (2-3 sentences max unless asked for details)
- Always cite your source when mentioning specific details
"""


# ============================================================================
# 1) USER REGISTRATION
# ============================================================================

class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer


# ============================================================================
# 2) HEALTH CHECK
# ============================================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "status": "ok",
        "time": timezone.now().isoformat(),
    })


# ============================================================================
# 3) SERIALIZERS
# ============================================================================

class BotSerializer(ModelSerializer):
    class Meta:
        model = Chatbot
        fields = ("id", "name", "website_url", "status", "created_at", "updated_at")


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


# ============================================================================
# 4) BOT LIST
# ============================================================================

class ListBotsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BotSerializer

    def get_queryset(self):
        return Chatbot.objects.filter(user=self.request.user).order_by("-created_at")


# ============================================================================
# 5) CREATE BOT (TRAIN)
# ============================================================================

class CreateBotView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        name = (request.data.get("name") or "").strip()

        # ❌ COMMENTED OUT - URL inputs no longer accepted
        # url = (request.data.get("url") or "").strip()
        # urls = request.data.get("urls") or []

        uploaded_file = request.FILES.get("file")

        # ❌ COMMENTED OUT - URL list building removed
        # url_list = []
        # if url:
        #     url_list.append(url)
        # if isinstance(urls, list) and urls:
        #     url_list.extend([u for u in urls if u])
        # url_list = list(dict.fromkeys(url_list))  # dedupe preserve order

        uploaded_file_bytes = None
        uploaded_file_name = None
        if uploaded_file:
            uploaded_file_bytes = uploaded_file.read()
            uploaded_file_name = uploaded_file.name

        if not name:
            return Response({"error": "Bot name is required"}, status=400)

        # ✅ MODIFIED - Only file upload is required now (no URL fallback)
        if not uploaded_file_bytes:
            return Response({"error": "Please upload a document to train your bot"}, status=400)

        # ❌ COMMENTED OUT - URL validation not needed
        # for u in url_list:
        #     if not u.startswith(("http://", "https://")):
        #         return Response({"error": f"Invalid URL: {u}"}, status=400)

        bot = Chatbot.objects.create(
            user=request.user,
            name=name,
            website_url=None,       # ❌ COMMENTED OUT - no URL stored: url_list[0] if url_list else None
            system_prompt=DEFAULT_BOT_PROMPT,
            status=TrainingStatus.FETCHING,
        )

        job = IngestionJob.objects.create(
            chatbot=bot,
            status="queued",
            message="Starting training..."
        )

        pipeline = ImprovedTrainingPipeline(
            bot=bot,
            url_list=[],            # ❌ Always empty - URL training disabled
            uploaded_file_bytes=uploaded_file_bytes,
            uploaded_file_name=uploaded_file_name,
            job_id=str(job.id),
            discover_max_pages=0,   # ❌ Disabled
            discover_max_depth=0,   # ❌ Disabled
        )
        pipeline.start_background()

        return Response({
            "bot_id": str(bot.id),
            "job_id": str(job.id),
            "name": bot.name,
            "status": bot.status,
            "message": "Training started"
        })


# ============================================================================
# 6) UPLOAD DOCUMENT (TRAIN EXISTING BOT)
# ============================================================================

class UploadDocumentView(GenericAPIView):
    """
    Upload a file to train an existing bot.
    """
    permission_classes = [IsAuthenticated, IsBotOwner]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileUploadSerializer

    def post(self, request, bot_id):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            bot = Chatbot.objects.get(id=bot_id, user=request.user)
        except Chatbot.DoesNotExist:
            return Response({"error": "Bot not found"}, status=404)

        uploaded_file = serializer.validated_data["file"]
        uploaded_file_bytes = uploaded_file.read()
        uploaded_file_name = uploaded_file.name

        job = IngestionJob.objects.create(
            chatbot=bot,
            status="queued",
            message="Processing uploaded file..."
        )

        pipeline = ImprovedTrainingPipeline(
            bot=bot,
            url_list=[],            # ❌ Always empty - file-only training
            uploaded_file_bytes=uploaded_file_bytes,
            uploaded_file_name=uploaded_file_name,
            job_id=str(job.id),
            discover_max_pages=0,
            discover_max_depth=0,
        )
        pipeline.start_background()

        return Response({
            "bot_id": str(bot.id),
            "job_id": str(job.id),
            "status": bot.status,
            "message": "File training started"
        })


# ============================================================================
# 7) STATUS ENDPOINTS
# ============================================================================

class BotStatusView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsBotOwner]

    def get(self, request, bot_id):
        try:
            bot = Chatbot.objects.get(id=bot_id, user=request.user)
        except Chatbot.DoesNotExist:
            return Response({"error": "Bot not found"}, status=404)

        return Response({
            "bot_id": str(bot.id),
            "status": bot.status,
            "updated_at": bot.updated_at,
        })


class IngestionJobStatusView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsBotOwner]

    def get(self, request, bot_id, job_id):
        try:
            bot = Chatbot.objects.get(id=bot_id, user=request.user)
            job = IngestionJob.objects.get(id=job_id, chatbot=bot)
        except (Chatbot.DoesNotExist, IngestionJob.DoesNotExist):
            return Response({"error": "Not found"}, status=404)

        return Response({
            "job_id": str(job.id),
            "status": job.status,
            "message": job.message,
            "progress_current": job.progress_current,
            "progress_total": job.progress_total,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        })


# ============================================================================
# 8) CHAT
# ============================================================================

class ChatView(GenericAPIView):
    permission_classes = [IsAuthenticated, IsBotOwner]
    parser_classes = [JSONParser]

    def post(self, request, bot_id):
        user_message = (request.data.get("message") or "").strip()
        include_sources = bool(request.data.get("include_sources", True))

        if not user_message:
            return Response({"error": "message is required"}, status=400)

        try:
            bot = Chatbot.objects.get(id=bot_id, user=request.user)
        except Chatbot.DoesNotExist:
            return Response({"error": "Bot not found"}, status=404)

        if bot.status not in ["completed", "active"]:
            return Response({"error": "Bot is still training", "status": bot.status}, status=400)

        return Response(self._generate_response(bot, user_message, include_sources))

    def _generate_response(self, bot: Chatbot, message: str, include_sources: bool) -> dict:
        vectorstore = get_vectorstore()

        results = vectorstore.similarity_search_with_score(
            query=message,
            k=12,
            filter={"bot_id": str(bot.id)}
        )

        # Score threshold - higher is better for cosine/dotproduct
        min_score = float(os.getenv("RAG_MIN_SCORE", "0.75"))

        filtered = [(doc, score) for doc, score in results if score is not None and score >= min_score]
        filtered.sort(key=lambda x: x[1], reverse=True)
        filtered = filtered[:6]

        if not filtered:
            return {
                "answer": "I don't have enough information from your uploaded documents yet to answer that. Please upload more relevant documents.",
                "sources": []
            }

        context_blocks = []
        sources = []
        for doc, score in filtered:
            src = doc.metadata.get("source", "")
            title = doc.metadata.get("title", "")
            context_blocks.append(f"SOURCE: {src}\nTITLE: {title}\nCONTENT:\n{doc.page_content}")
            if src:
                sources.append(src)

        context = "\n\n---\n\n".join(context_blocks)

        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2
        )

        system = bot.system_prompt or DEFAULT_BOT_PROMPT
        prompt = f"{system}\n\nCONTEXT:\n{context}\n\nUSER QUESTION:\n{message}\n"

        resp = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=message)
        ])

        return {
            "answer": (resp.content or "").strip(),
            "sources": list(dict.fromkeys(sources)) if include_sources else []
        }


# ============================================================================
# 9) DELETE BOT - FIXED TO SUPPORT BOTH DELETE AND POST
# ============================================================================

class DeleteBotView(GenericAPIView):
    """
    Delete a bot - supports both DELETE and POST methods for compatibility
    """
    permission_classes = [IsAuthenticated, IsBotOwner]

    def delete(self, request, bot_id):
        """DELETE method - proper REST API"""
        try:
            bot = Chatbot.objects.get(id=bot_id, user=request.user)
        except Chatbot.DoesNotExist:
            return Response({"error": "Bot not found"}, status=404)

        bot.delete()
        return Response({"message": "Bot deleted"}, status=200)

    def post(self, request, bot_id):
        """POST method - for compatibility with existing clients"""
        return self.delete(request, bot_id)


class DeleteFailedBotsView(GenericAPIView):
    """Delete all failed bots for current user"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        qs = Chatbot.objects.filter(user=request.user, status="failed")
        count = qs.count()
        qs.delete()
        return Response({"deleted": count})


# ============================================================================
# 10) VERIFY ISOLATION (DEBUG)
# ============================================================================

class VerifyDataIsolationView(GenericAPIView):
    """Debug endpoint to verify data isolation between bots"""
    permission_classes = [IsAuthenticated, IsBotOwner]

    def get(self, request, bot_id):
        try:
            bot = Chatbot.objects.get(id=bot_id, user=request.user)
        except Chatbot.DoesNotExist:
            return Response({"error": "Bot not found"}, status=404)

        vectorstore = get_vectorstore()

        q = request.query_params.get("q", "services")
        results = vectorstore.similarity_search_with_score(
            query=q,
            k=5,
            filter={"bot_id": str(bot.id)}
        )

        out = []
        for doc, score in results:
            out.append({
                "score": float(score) if score is not None else None,
                "source": doc.metadata.get("source"),
                "title": doc.metadata.get("title"),
                "preview": (doc.page_content or "")[:200],
            })

        return Response({
            "bot_id": str(bot.id),
            "results": out
        })