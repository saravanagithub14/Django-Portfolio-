import json
import logging
import os

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from chatbot import rag_service
from chatbot.fallback import get_keyword_fallback_response
from chatbot.llm import DEFAULT_TEMPERATURE, PROVIDER_DEFAULT_MODELS, is_mock_provider, make_llm
from chatbot.models import AIModelConfig, Chatbot, ChatMessage, ChatSession, ContextSnippet
from chatbot.rag import pipeline
from portfolio.models import UserProfile

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 6  # previous messages sent to the LLM as conversational memory


def is_rate_limited(ip_address):
    """Simple minute-level cache rate limiting (max 10 requests per minute)"""
    cache_key = f"rate_limit_{ip_address}"
    requests_count = cache.get(cache_key, 0)
    if requests_count >= 10:
        return True
    cache.set(cache_key, requests_count + 1, timeout=60)
    return False


def get_history(session):
    """The last few messages before the current user message, oldest first."""
    if not session:
        return []
    recent = list(
        ChatMessage.objects.filter(session=session)
        .order_by('-timestamp')
        .values_list('role', 'content')[1:HISTORY_LIMIT + 1]
    )
    return [{'role': role, 'content': content} for role, content in reversed(recent)]


def generate_llm_response(user_message, profile, session, model_cfg):
    """
    RAG pipeline over the provider chain. Returns (reply, retrieval_meta, sources); reply is None when
    every provider failed (or retrieval broke), so the caller falls back to keyword matching.
    """
    history = get_history(session)
    try:
        result = pipeline.run(user_message, history, make_llm(model_cfg))
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        return None, {"error": str(e)}, []
    return result["reply"], result["meta"], result.get("sources", [])


def get_active_bot():
    """The enabled Chatbot, auto-creating a default config if none exists."""
    bot = Chatbot.objects.select_related('model_config').filter(enabled=True).first()
    if bot:
        return bot
    try:
        provider = 'openai' if os.getenv('OPENAI_API_KEY') else 'groq'
        cfg, _ = AIModelConfig.objects.get_or_create(
            name=f"{provider.title()} Default",
            defaults={
                'provider': provider,
                'model_name': os.getenv(f"{provider.upper()}_MODEL") or PROVIDER_DEFAULT_MODELS[provider],
                'api_key': '',
                'temperature': DEFAULT_TEMPERATURE,
            }
        )
        return Chatbot.objects.create(bot_name="V.E.R.A.", enabled=True, model_config=cfg)
    except Exception as e:
        logger.warning(f"Could not auto-create Chatbot config: {e}")
        return None


def save_message(session, role, content, retrieval_meta=None):
    if not session:
        return
    try:
        ChatMessage.objects.create(session=session, role=role, content=content, retrieval_meta=retrieval_meta)
    except Exception as e:
        logger.warning(f"Could not save chat message to DB: {e}")


@csrf_exempt
def chat_api_endpoint(request):
    """
    POST API endpoint for receiving user messages and returning chatbot responses.
    Automatically groups messages under Django sessions and logs messages.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    # 1. Check Rate Limiting
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')

    if is_rate_limited(ip):
        return JsonResponse({"error": "Rate limit exceeded. Please try again later."}, status=429)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Message parameter is empty'}, status=400)

    if len(user_message) > 500:
        return JsonResponse({'error': 'Message exceeds the maximum limit of 500 characters'}, status=400)

    profile = None
    try:
        # 2. Resolve Session
        try:
            if not request.session.session_key:
                request.session.create()
            django_session_key = request.session.session_key
        except Exception:
            django_session_key = "anonymous_session"

        profile = UserProfile.objects.first()

        try:
            session, _ = ChatSession.objects.get_or_create(
                session_id=django_session_key,
                defaults={'user_ip': ip}
            )
        except Exception as e:
            logger.warning(f"Could not save chat session to DB: {e}")
            session = None
        save_message(session, 'user', user_message)

        # 3. Ask the LLM chain; fall back to keyword matching if mock or every provider fails
        bot = get_active_bot()
        model_cfg = bot.model_config if bot else None
        bot_response, retrieval_meta, sources = None, None, []
        if model_cfg and not is_mock_provider(model_cfg):
            bot_response, retrieval_meta, sources = generate_llm_response(user_message, profile, session, model_cfg)
        if not bot_response:
            bot_response, sources = get_keyword_fallback_response(user_message, profile), []
            if retrieval_meta is not None:
                retrieval_meta["keyword_fallback"] = True

        save_message(session, 'assistant', bot_response, retrieval_meta)
        # "sources" feeds the widget's source chips; clients that only read "response" are unaffected
        return JsonResponse({'response': bot_response, 'sources': sources})

    except Exception as fatal_err:
        logger.error(f"Fatal error in chat endpoint: {fatal_err}", exc_info=True)
        return JsonResponse({'response': get_keyword_fallback_response(user_message, profile)})


def health_view(request):
    """
    GET API reporting the RAG index state (chunks, manifest freshness, BM25, reranker) and active config.
    """
    bot = Chatbot.objects.select_related('model_config').filter(enabled=True).first()
    try:
        rag = rag_service.status()
        is_healthy = rag["chunk_count"] > 0
    except Exception as e:
        logger.error(f"Health check could not load the RAG index: {e}", exc_info=True)
        rag, is_healthy = {"error": str(e)}, False

    status = {
        "status": "healthy" if is_healthy else "unhealthy",
        "vector_store_loaded": is_healthy,
        "active_chatbot": bot.bot_name if bot else None,
        "active_provider": os.getenv('CHATBOT_PROVIDER') or (bot.model_config.provider if bot and bot.model_config else "None"),
        "rag": rag,
    }
    return JsonResponse(status, status=200 if is_healthy else 500)


@csrf_exempt
def update_context_view(request):
    """
    POST Webhook adding a text snippet to the chatbot's knowledge. The snippet is saved as a
    ContextSnippet (so every future index build includes it) and appended to the live index.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    expected_token = os.getenv("UPDATE_TOKEN")
    if not expected_token:
        logger.error("Context update webhook called, but UPDATE_TOKEN environment variable is not configured.")
        return JsonResponse({"error": "Webhook token not configured on server."}, status=500)

    token = request.headers.get("X-Update-Token")
    if not token or token != expected_token:
        logger.warning("Unauthorized access attempt to /update_context webhook.")
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        update_text = data.get("text", "").strip()
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if not update_text:
        return JsonResponse({"error": "Text content cannot be empty."}, status=400)

    snippet = ContextSnippet.objects.create(text=update_text)
    try:
        chunk = rag_service.add_snippet_to_live_index(snippet)
    except Exception as e:
        logger.error(f"Saved snippet {snippet.pk} but could not add it to the live index: {e}", exc_info=True)
        return JsonResponse({"error": "Snippet saved, but the live index could not be updated. "
                                      "It will be included in the next index build."}, status=500)
    return JsonResponse({"status": "success", "chunk_id": chunk["chunk_id"],
                         "message": "Context added and index saved successfully."})
