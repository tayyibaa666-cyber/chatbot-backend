"""
IMPROVED TRAINING SERVICES - WITH DETAILED LOGGING & ERROR TRACKING
Fixes:
- Detailed per-URL logging
- Real failure reasons stored in job
- Better error messages
- Proper status handling

===================================================
MODIFIED: URL crawling/scraping sections commented out.
Only document upload (RAG) training is active.
===================================================
"""

import os
import re
import time
import hashlib
import threading
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

# import requests               # ❌ COMMENTED OUT - not needed without URL crawling
# from bs4 import BeautifulSoup # ❌ COMMENTED OUT - only used for URL HTML extraction

from django.utils import timezone

from .models import Chatbot, Document, IngestionJob
from .vectorstore import get_vectorstore
# from .website_crawler import discover_site_urls, CrawlDiscoverConfig  # ❌ COMMENTED OUT - URL discovery not needed

# Setup logger
logger = logging.getLogger(__name__)

# Disable SSL warnings
# import urllib3                                                          # ❌ COMMENTED OUT - not needed without URL crawling
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)    # ❌ COMMENTED OUT


class TrainingStatus:
    FETCHING = "fetching"
    PROCESSING = "processing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


# ❌ COMMENTED OUT - Only used for URL media filtering, not needed for document upload
# MEDIA_EXTENSIONS = (
#     ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg",
#     ".mp4", ".mov", ".avi", ".mkv",
#     ".mp3", ".wav",
#     ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
#     ".zip", ".rar", ".7z", ".tar", ".gz",
# )

# ❌ COMMENTED OUT - URL utility functions not needed for document-only training
# def normalize_url(url: str) -> str:
#     p = urlparse((url or "").strip())
#     if not p.scheme:
#         p = p._replace(scheme="https")
#     p = p._replace(fragment="")
#     return urlunparse(p)

# def is_sitemap_or_xml(url: str) -> bool:
#     u = (url or "").lower().strip()
#     if not u.endswith(".xml"):
#         return False
#     return "sitemap" in u or "sitemap_" in u or "sitemap-" in u or "sitemapindex" in u

# def is_media(url: str) -> bool:
#     u = (url or "").lower().strip()
#     return any(u.endswith(ext) for ext in MEDIA_EXTENSIONS)

# def classify_page_type(url: str) -> str:
#     u = (url or "").lower()
#     if u.endswith("/") or u.rstrip("/").endswith(urlparse(u).netloc):
#         return "homepage"
#     if "about" in u:
#         return "about"
#     if "contact" in u:
#         return "contact"
#     if "pricing" in u:
#         return "pricing"
#     if "service" in u:
#         return "services"
#     if "faq" in u:
#         return "faq"
#     if "blog" in u or "/post" in u or "/articles" in u:
#         return "blog"
#     return "generic"


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


# ❌ COMMENTED OUT - extract_main_text used only for URL/HTML extraction
# def extract_main_text(html: str) -> str:
#     if not html:
#         return ""
#     soup = BeautifulSoup(html, "html.parser")
#     for tag in soup(["script", "style", "noscript", "svg"]):
#         tag.decompose()
#     for sel in ["header", "footer", "nav", "aside", ".nav", ".navbar", ".menu", ".footer", ".header"]:
#         for t in soup.select(sel):
#             t.decompose()
#     main = soup.find("main") or soup.find("article") or soup.body or soup
#     text = main.get_text(separator="\n", strip=True)
#     text = re.sub(r"\n{3,}", "\n\n", text).strip()
#     return text


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    if not text:
        return []
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def extract_text_from_uploaded_file(file_bytes: bytes, filename: str) -> str:
    """
    Best-effort extraction with detailed logging.
    """
    name = (filename or "").lower().strip()

    # PDF support
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for p in reader.pages:
                pages.append(p.extract_text() or "")
            text = "\n\n".join(pages).strip()
            logger.info(f"Extracted {len(text)} chars from PDF: {filename}")
            return text
        except Exception as e:
            logger.warning(f"PDF extraction failed for {filename}: {e}. Trying plain text...")
            try:
                return (file_bytes or b"").decode("utf-8", errors="ignore").strip()
            except:
                return ""

    # Plain text
    try:
        text = (file_bytes or b"").decode("utf-8", errors="ignore").strip()
        logger.info(f"Extracted {len(text)} chars from text file: {filename}")
        return text
    except Exception as e:
        logger.error(f"Text extraction failed for {filename}: {e}")
        return ""


# ❌ COMMENTED OUT - FetchResult dataclass only used for URL crawling
# @dataclass
# class FetchResult:
#     url: str
#     ok: bool
#     status_code: Optional[int]
#     content_type: str
#     title: str
#     text: str
#     error: str = ""
#     final_url: str = ""  # After redirects
#     bytes_downloaded: int = 0


# ❌ COMMENTED OUT - PageFetcher class only used for URL crawling
# class PageFetcher:
#     def __init__(self, timeout: int = 15):
#         self.timeout = timeout
#         self.headers = {
#             "User-Agent": (
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/122.0.0.0 Safari/537.36"
#             )
#         }
#
#     def fetch(self, url: str) -> FetchResult:
#         url = normalize_url(url)
#
#         if is_sitemap_or_xml(url):
#             logger.info(f"Skipped sitemap: {url}")
#             return FetchResult(url=url, ok=False, status_code=None, content_type="", title="", text="", error="Sitemap XML (not trainable)")
#
#         if is_media(url):
#             logger.info(f"Skipped media: {url}")
#             return FetchResult(url=url, ok=False, status_code=None, content_type="", title="", text="", error="Media file (not trainable)")
#
#         try:
#             r = requests.get(url, timeout=self.timeout, headers=self.headers, allow_redirects=True, verify=False)
#             ct = (r.headers.get("Content-Type") or "").lower()
#             final_url = r.url
#             bytes_downloaded = len(r.content) if r.content else 0
#
#             logger.info(f"Fetched {url} -> {r.status_code}, {ct}, {bytes_downloaded} bytes")
#
#             if r.status_code != 200:
#                 return FetchResult(
#                     url=url, ok=False, status_code=r.status_code, content_type=ct,
#                     title="", text="", error=f"HTTP {r.status_code}",
#                     final_url=final_url, bytes_downloaded=bytes_downloaded
#                 )
#
#             if "text/html" not in ct and "application/xhtml" not in ct:
#                 return FetchResult(
#                     url=url, ok=False, status_code=r.status_code, content_type=ct,
#                     title="", text="", error=f"Non-HTML content: {ct}",
#                     final_url=final_url, bytes_downloaded=bytes_downloaded
#                 )
#
#             html = r.text or ""
#             soup = BeautifulSoup(html, "html.parser")
#             title = (soup.title.get_text(strip=True) if soup.title else "").strip()
#             text = extract_main_text(html)
#
#             logger.info(f"Extracted {len(text)} chars from {url}")
#
#             return FetchResult(
#                 url=url, ok=True, status_code=r.status_code, content_type=ct,
#                 title=title, text=text, final_url=final_url, bytes_downloaded=bytes_downloaded
#             )
#
#         except requests.exceptions.Timeout:
#             logger.warning(f"Timeout fetching {url}")
#             return FetchResult(url=url, ok=False, status_code=None, content_type="", title="", text="", error="Timeout")
#         except requests.exceptions.SSLError as e:
#             logger.warning(f"SSL error fetching {url}: {e}")
#             return FetchResult(url=url, ok=False, status_code=None, content_type="", title="", text="", error="SSL Error")
#         except requests.exceptions.ConnectionError as e:
#             logger.warning(f"Connection error fetching {url}: {e}")
#             return FetchResult(url=url, ok=False, status_code=None, content_type="", title="", text="", error="Connection Error")
#         except Exception as e:
#             logger.error(f"Error fetching {url}: {e}")
#             return FetchResult(url=url, ok=False, status_code=None, content_type="", title="", text="", error=str(e)[:100])


class ImprovedTrainingPipeline:
    MIN_TEXT_LEN = 100
    # MIN_PAGES_REQUIRED = 3  # ❌ COMMENTED OUT - not needed for document-only training

    def __init__(
        self,
        bot: Chatbot,
        url_list: List[str],           # kept for API compatibility but ignored
        uploaded_file_bytes: Optional[bytes] = None,
        uploaded_file_name: Optional[str] = None,
        job_id: Optional[str] = None,
        discover_max_pages: int = 50,  # kept for API compatibility but ignored
        discover_max_depth: int = 3,   # kept for API compatibility but ignored
    ):
        self.bot = bot
        self.url_list = []             # ❌ Always empty - URL training disabled
        self.uploaded_file_bytes = uploaded_file_bytes
        self.uploaded_file_name = uploaded_file_name
        self.job_id = job_id
        # self.discover_max_pages = discover_max_pages  # ❌ COMMENTED OUT - not used
        # self.discover_max_depth = discover_max_depth  # ❌ COMMENTED OUT - not used
        # self.fetcher = PageFetcher(timeout=15)         # ❌ COMMENTED OUT - PageFetcher removed
        self.last_error = ""

    def start_background(self):
        t = threading.Thread(target=self.run, daemon=True)
        t.start()

    def _job(self) -> Optional[IngestionJob]:
        if not self.job_id:
            return None
        try:
            return IngestionJob.objects.get(id=self.job_id, chatbot=self.bot)
        except Exception:
            return None

    def _job_update(self, status: str, message: str, cur: int = 0, total: int = 0):
        job = self._job()
        if not job:
            return
        job.status = status
        job.message = message
        job.progress_current = cur
        job.progress_total = total
        if status == "running" and not job.started_at:
            job.started_at = timezone.now()
        if status in ["completed", "failed"]:
            job.finished_at = timezone.now()
        job.save()

        logger.info(f"Job {self.job_id[:8]}... {status}: {message}")

    def _set_bot_status(self, status: str):
        self.bot.status = status
        self.bot.save(update_fields=["status", "updated_at"])
        logger.info(f"Bot {self.bot.id} status: {status}")

    # ❌ COMMENTED OUT - _discover_urls only used for URL crawling
    # def _discover_urls(self) -> List[str]:
    #     all_urls: List[str] = []
    #     for seed in self.url_list:
    #         seed = normalize_url(seed)
    #         logger.info(f"Discovering URLs from: {seed}")
    #         cfg = CrawlDiscoverConfig(
    #             max_pages=self.discover_max_pages,
    #             max_depth=self.discover_max_depth,
    #             timeout=12,
    #         )
    #         try:
    #             discovered = discover_site_urls(seed, cfg)
    #             discovered = [u for u in discovered if not is_sitemap_or_xml(u) and not is_media(u)]
    #             all_urls.extend(discovered)
    #             logger.info(f"Discovered {len(discovered)} URLs from {seed}")
    #         except Exception as e:
    #             logger.error(f"Discovery failed for {seed}: {e}")
    #             self.last_error = f"Discovery failed: {str(e)[:100]}"
    #     return list(dict.fromkeys(all_urls))

    def _store_lc_documents(self, lc_docs):
        try:
            vectorstore = get_vectorstore()
            if lc_docs:
                vectorstore.add_documents(lc_docs)
                logger.info(f"Stored {len(lc_docs)} chunks in Pinecone")
        except Exception as e:
            logger.error(f"Pinecone storage failed: {e}")
            self.last_error = f"Pinecone error: {str(e)[:100]}"
            raise

    # ❌ COMMENTED OUT - _store_web_documents only used for URL crawling results
    # def _store_web_documents(self, docs: List[Tuple[str, FetchResult]]):
    #     from langchain_core.documents import Document as LCDocument
    #     lc_docs = []
    #     for url, fr in docs:
    #         page_type = classify_page_type(url)
    #         nhash = content_hash(fr.text)
    #         Document.objects.update_or_create(
    #             chatbot=self.bot,
    #             normalized_url=url,
    #             defaults={
    #                 "source_url": url,
    #                 "raw_content": fr.text,
    #                 "content_hash": nhash,
    #                 "page_type": page_type,
    #                 "title": fr.title or "",
    #                 "mime_type": fr.content_type or "",
    #                 "http_status": fr.status_code or None,
    #                 "error": "",
    #             }
    #         )
    #         chunks = chunk_text(fr.text, 1200, 150)
    #         for i, c in enumerate(chunks):
    #             lc_docs.append(
    #                 LCDocument(
    #                     page_content=c,
    #                     metadata={
    #                         "bot_id": str(self.bot.id),
    #                         "source": url,
    #                         "title": fr.title or "",
    #                         "page_type": page_type,
    #                         "chunk": i,
    #                     }
    #                 )
    #             )
    #     self._store_lc_documents(lc_docs)

    def _store_uploaded_file(self, file_bytes: bytes, filename: str):
        from langchain_core.documents import Document as LCDocument

        text = extract_text_from_uploaded_file(file_bytes, filename)

        if not text or len(text) < 50:
            error_msg = f"File too short: {len(text)} chars (need 50+). File: {filename}"
            logger.error(error_msg)
            self.last_error = error_msg
            raise RuntimeError(error_msg)

        nhash = content_hash(text)

        Document.objects.create(
            chatbot=self.bot,
            source_url=None,
            normalized_url=None,
            raw_content=text,
            content_hash=nhash,
            page_type="generic",
            title=filename or "uploaded_file",
            mime_type="uploaded",
            http_status=None,
            error="",
        )

        chunks = chunk_text(text, 1200, 150)
        lc_docs = []
        src = filename or "uploaded_file"
        for i, c in enumerate(chunks):
            lc_docs.append(
                LCDocument(
                    page_content=c,
                    metadata={
                        "bot_id": str(self.bot.id),
                        "source": src,
                        "title": filename or "uploaded_file",
                        "page_type": "generic",
                        "chunk": i,
                    }
                )
            )

        self._store_lc_documents(lc_docs)

    def run(self):
        try:
            self._set_bot_status(TrainingStatus.FETCHING)
            self._job_update("running", "Starting ingestion...")

            # ✅ ACTIVE - File upload training (RAG)
            if self.uploaded_file_bytes:
                self._set_bot_status(TrainingStatus.PROCESSING)
                self._job_update("processing", "Extracting uploaded file...")
                try:
                    self._store_uploaded_file(self.uploaded_file_bytes, self.uploaded_file_name or "file")
                    logger.info("File upload processed successfully")
                except Exception as e:
                    logger.error(f"File processing failed: {e}")
                    raise

            # ❌ COMMENTED OUT - URL crawling training disabled
            # if self.url_list:
            #     self._set_bot_status(TrainingStatus.FETCHING)
            #     self._job_update("running", "Discovering pages...")
            #
            #     urls = self._discover_urls()
            #     total = len(urls)
            #
            #     if total == 0 and not self.uploaded_file_bytes:
            #         error_msg = "No pages discovered (site blocked or no accessible content)"
            #         logger.error(error_msg)
            #         self.last_error = error_msg
            #         self._set_bot_status(TrainingStatus.FAILED)
            #         self._job_update("failed", error_msg)
            #         return
            #
            #     self._job_update("running", f"Discovered {total} pages. Fetching...", 0, total)
            #
            #     good: List[Tuple[str, FetchResult]] = []
            #     failed = 0
            #     failure_reasons = {}
            #
            #     for idx, url in enumerate(urls, start=1):
            #         fr = self.fetcher.fetch(url)
            #         if fr.ok and len(fr.text) >= self.MIN_TEXT_LEN:
            #             good.append((url, fr))
            #         else:
            #             failed += 1
            #             reason = fr.error or "text too short"
            #             failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            #         self._job_update("running", f"Fetched {idx}/{total} pages...", idx, total)
            #         time.sleep(0.05)
            #
            #     if failure_reasons:
            #         summary = ", ".join([f"{reason}: {count}" for reason, count in failure_reasons.items()])
            #         logger.warning(f"Fetch failures: {summary}")
            #         self.last_error = summary
            #
            #     if not self.uploaded_file_bytes and len(good) < self.MIN_PAGES_REQUIRED:
            #         error_msg = f"Training failed: only {len(good)} usable pages (failed={failed}). Reasons: {self.last_error}"
            #         logger.error(error_msg)
            #         self._set_bot_status(TrainingStatus.FAILED)
            #         self._job_update("failed", error_msg)
            #         return
            #
            #     combined_len = sum(len(fr.text) for _, fr in good)
            #     if not self.uploaded_file_bytes and combined_len < 2000:
            #         error_msg = f"Training failed: extracted content too small ({combined_len} chars)"
            #         logger.error(error_msg)
            #         self.last_error = error_msg
            #         self._set_bot_status(TrainingStatus.FAILED)
            #         self._job_update("failed", error_msg)
            #         return
            #
            #     self._set_bot_status(TrainingStatus.TRAINING)
            #     self._job_update("training", "Chunking + indexing into Pinecone...")
            #     self._store_web_documents(good)

            # ✅ Success
            self._set_bot_status(TrainingStatus.COMPLETED)
            self._job_update("completed", "Training completed successfully.")
            logger.info(f"Bot {self.bot.id} training completed")

        except Exception as e:
            error_msg = f"Training failed: {str(e)}"
            logger.error(f"Bot {self.bot.id} training error: {e}", exc_info=True)
            self.last_error = error_msg
            self._set_bot_status(TrainingStatus.FAILED)
            self._job_update("failed", error_msg)