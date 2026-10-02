import os
import json
import random
import logging
import re
from functools import lru_cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from chatbot.models import Chatbot, ChatSession, ChatMessage, AIModelConfig, ContextSnippet
from portfolio.models import UserProfile, Project, Skill, Job
from chatbot import rag_service
from chatbot.rag import pipeline

logger = logging.getLogger(__name__)

FUNNY_OBJECTIONS = [
    "My lawyers have advised me not to answer that, lest I accidentally reveal the secret recipe for my favorite filter coffee.",
    "I'd love to answer that, but my neural networks are currently staging a strike for better GPU cooling.",
    "That question exists in a parallel universe, and unfortunately my interdimensional portal is currently down for maintenance.",
    "I can neither confirm nor deny that. Mostly because my database is strictly allergic to that topic.",
    "That information is highly classified. If I told you, I'd have to explain quantum computing from scratch, and honestly, neither of us has the time.",
    "I'm a Data Scientist, not a wizard! (Though my model tuning can sometimes feel like magic.) I can't answer that.",
    "Error 418: I am a teapot, and teapots do not have opinions on this matter. Let's talk about AI or my data science experience instead!"
]

# Educational concept explanations
CONCEPT_ANSWERS = {
    'machine learning': "Machine Learning (ML) is a branch of artificial intelligence where algorithms learn underlying patterns from data to make predictions or decisions without explicit rule-based programming. In my work as an AI Engineer, I design and deploy ML pipelines spanning statistical classification, regression, and model evaluation.",
    'deep learning': "Deep Learning is a specialized subfield of machine learning inspired by biological neural networks. It utilizes multi-layered neural architectures to automatically extract features from complex, high-dimensional data like images, audio, and text.",
    'neural network': "Artificial Neural Networks (ANNs) are computational models inspired by biological brain structures. They consist of interconnected nodes (neurons) arranged in layers that process inputs, apply learned weights, and pass signals forward to produce outputs.",
    'rag': "Retrieval-Augmented Generation (RAG) is an architectural pattern that connects Large Language Models (LLMs) with external knowledge sources (like FAISS vector databases). It retrieves relevant document context before generating answers, ensuring precise, grounded, and hallucination-free responses.",
    'generative ai': "Generative AI refers to artificial intelligence models capable of generating new text, images, audio, or code based on patterns learned from vast training datasets. I specialize in building agentic Gen AI systems and RAG pipelines.",
    'llm': "Large Language Models (LLMs) are massive neural networks trained on vast text corpora to understand, reason, and generate human language. Examples include Llama 3, GPT-4, and Claude.",
    'computer vision': "Computer Vision is a field of AI enabling computers to interpret and analyze visual information from images and video feeds, using convolutional neural networks (CNNs) and vision transformers."
}

# Fallback answering function based on database keyword matching & concept lookup
def get_keyword_fallback_response(query, profile):
    query_lower = query.lower()

    for concept_key, concept_answer in CONCEPT_ANSWERS.items():
        if concept_key in query_lower:
            return concept_answer

    # 1. Check Projects
    matched_projects = []
    for p in Project.objects.all():
        if p.title.lower() in query_lower or any(t.lower() in query_lower for t in p.tag_list) or (p.description and p.description.lower() in query_lower):
            matched_projects.append(p)

    if matched_projects:
        parts = []
        for p in matched_projects[:3]:
            text = f"{p.title} is one I'm proud of. {p.description}"
            if p.github_url and p.github_url != '#':
                text += f" You can find the code at {p.github_url}"
            parts.append(text)
        intro = "Sure, here's what I've worked on along those lines." if len(parts) > 1 else "Yes, I've worked on that."
        return intro + "\n\n" + "\n\n".join(parts)

    # 2. Check Skills
    matched_skills = []
    for s in Skill.objects.all():
        if s.name.lower() in query_lower or (s.context and s.context.lower() in query_lower):
            matched_skills.append(s)

    if matched_skills:
        names = [s.name for s in matched_skills]
        joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"
        response_text = f"Yes, I work with {joined} regularly."
        contexts = [s.context for s in matched_skills if s.context]
        if contexts:
            response_text += f" Mostly for things like {contexts[0][0].lower() + contexts[0][1:]}."
        return response_text

    # 3. Check Experience / Jobs
    matched_jobs = []
    for j in Job.objects.all():
        if j.title.lower() in query_lower or j.company.lower() in query_lower or j.description.lower() in query_lower:
            matched_jobs.append(j)

    if matched_jobs:
        return "\n\n".join(
            f"I worked as a {j.title} at {j.company} ({j.period}). {j.description}" for j in matched_jobs[:2]
        )

    # General fallback
    contact_email = profile.email if profile else "saravanaperumalr14@gmail.com"
    return (
        f"Hey! I'm Saravana. Happy to chat about my work in AI engineering and data science, "
        f"the projects I've built, or the tools I use day to day. "
        f"If you'd rather talk directly, you can reach me at {contact_email}."
    )

def is_rate_limited(ip_address):
    """Simple minute-level cache rate limiting (max 10 requests per minute)"""
    cache_key = f"rate_limit_{ip_address}"
    requests_count = cache.get(cache_key, 0)
    if requests_count >= 10:
        return True
    cache.set(cache_key, requests_count + 1, timeout=60)
    return False


# ─── LLM providers ───────────────────────────────────────────────────

# Env vars take priority over keys stored in the DB (DB keys tend to go stale)
PROVIDER_ENV_KEYS = {
    'openai': 'OPENAI_API_KEY',
    'groq': 'GROQ_API_KEY',
    'gemini': 'GEMINI_API_KEY',
}
PROVIDER_DEFAULT_MODELS = {
    'openai': 'gpt-4o-mini',
    'groq': 'openai/gpt-oss-20b',
    'gemini': 'gemini-1.5-flash',
}
# Groq exposes an OpenAI-compatible API, so both go through the same client
OPENAI_COMPATIBLE_BASE_URLS = {
    'openai': None,
    'groq': 'https://api.groq.com/openai/v1',
}
HISTORY_LIMIT = 6  # previous messages sent to the LLM as conversational memory
LLM_TIMEOUT = 30.0
DEFAULT_TEMPERATURE = 0.6  # a little warmth so replies sound conversational, not robotic
MAX_OUTPUT_TOKENS = 400  # short chat-style replies


def strip_markdown(text):
    """The chat widget renders plain text, so flatten any markdown the model still produces."""
    text = re.sub(r'```.*?```', '', text, flags=re.S)                    # code blocks
    text = re.sub(r'^[ \t]*\|?[ \t]*:?-{2,}[^\n]*\n?', '', text, flags=re.M)  # table separator rows
    text = re.sub(r'^[ \t]*\|(.*)\|[ \t]*$',                                    # table rows -> "a, b, c"
                  lambda m: ', '.join(c.strip() for c in m.group(1).split('|') if c.strip()),
                  text, flags=re.M)
    text = re.sub(r'^[ \t]{0,3}#{1,6}[ \t]*', '', text, flags=re.M)            # headings
    text = re.sub(r'^[ \t]*(?:[-*•]|\d+[.)])[ \t]+', '', text, flags=re.M)     # list markers
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)          # links
    text = re.sub(r'(\*\*|__)(.+?)\1', r'\2', text)                      # bold
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'\1', text)  # italics
    text = re.sub(r'`([^`]+)`', r'\1', text)                             # inline code
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def provider_settings(provider, model_cfg):
    """(api_key, model_name, temperature, base_url) for a provider; DB config only applies to its own provider.
    <PROVIDER>_API_KEY / <PROVIDER>_MODEL env vars win over the DB."""
    own_cfg = model_cfg if model_cfg and model_cfg.provider == provider else None
    env_name = PROVIDER_ENV_KEYS.get(provider)
    api_key = (os.getenv(env_name) if env_name else None) or (own_cfg.api_key if own_cfg else None)
    model_name = (
        os.getenv(f"{provider.upper()}_MODEL")
        or (own_cfg.model_name if own_cfg else None)
        or PROVIDER_DEFAULT_MODELS.get(provider)
    )
    temperature = own_cfg.temperature if own_cfg else DEFAULT_TEMPERATURE
    base_url = (own_cfg.api_base_url if own_cfg else None) or OPENAI_COMPATIBLE_BASE_URLS.get(provider)
    return api_key, model_name, temperature, base_url


@lru_cache(maxsize=8)
def get_openai_client(api_key, base_url=None):
    """Reuse HTTP clients across requests instead of rebuilding them per message."""
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url, timeout=LLM_TIMEOUT, max_retries=1)


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


def call_openai_compatible(api_key, model_name, temperature, base_url, messages, max_tokens, json_mode=False):
    client = get_openai_client(api_key, base_url)
    extra = {'response_format': {'type': 'json_object'}} if json_mode else {}
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **extra,
    )
    return response.choices[0].message.content


def call_gemini(api_key, model_name, temperature, messages, max_tokens, json_mode=False):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    system_prompt = "\n\n".join(m['content'] for m in messages if m['role'] == 'system') or None
    turns = [m for m in messages if m['role'] != 'system']
    generation_config = {
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": max_tokens,
    }
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=system_prompt,
    )
    gemini_history = [
        {'role': 'user' if m['role'] == 'user' else 'model', 'parts': [m['content']]} for m in turns[:-1]
    ]
    return model.start_chat(history=gemini_history).send_message(turns[-1]['content']).text


def provider_order(model_cfg):
    """Preferred provider first (CHATBOT_PROVIDER env overrides the DB), then any other keyed provider as backup."""
    preferred = os.getenv('CHATBOT_PROVIDER') or (model_cfg.provider if model_cfg else None)
    order = [preferred] if preferred else []
    return order + [p for p in PROVIDER_ENV_KEYS if p not in order]


def is_mock_provider(model_cfg):
    return (os.getenv('CHATBOT_PROVIDER') or (model_cfg.provider if model_cfg else '')) == 'mock'


def make_llm(model_cfg):
    """
    An LLM callable over the provider chain: tries each provider that has an API key, in order.
    llm(messages, temperature=None, max_tokens=..., json_mode=False) -> (text, provider) or (None, None).
    temperature=None uses the provider's configured temperature.
    """
    def llm(messages, *, temperature=None, max_tokens=MAX_OUTPUT_TOKENS, json_mode=False):
        for provider in provider_order(model_cfg):
            api_key, model_name, default_temperature, base_url = provider_settings(provider, model_cfg)
            if not api_key:
                continue
            temp = default_temperature if temperature is None else temperature
            try:
                if provider in OPENAI_COMPATIBLE_BASE_URLS:
                    text = call_openai_compatible(api_key, model_name, temp, base_url, messages, max_tokens, json_mode)
                elif provider == 'gemini':
                    text = call_gemini(api_key, model_name, temp, messages, max_tokens, json_mode)
                else:
                    logger.warning(f"Provider {provider} is not supported yet.")
                    continue
                if text:
                    return text, provider
            except Exception as e:
                logger.error(f"{provider} API execution error: {e}", exc_info=True)
        return None, None
    return llm


def generate_llm_response(user_message, profile, session, model_cfg):
    """
    RAG pipeline over the provider chain. Returns (reply, retrieval_meta); reply is None when every
    provider failed (or retrieval broke), so the caller falls back to keyword matching.
    """
    history = get_history(session)
    try:
        result = pipeline.run(user_message, history, make_llm(model_cfg))
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        return None, {"error": str(e)}
    return result["reply"], result["meta"]


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
        return Chatbot.objects.create(bot_name="Saravana's AI", enabled=True, model_config=cfg)
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
        bot_response, retrieval_meta = None, None
        if model_cfg and not is_mock_provider(model_cfg):
            bot_response, retrieval_meta = generate_llm_response(user_message, profile, session, model_cfg)
        if not bot_response:
            bot_response = get_keyword_fallback_response(user_message, profile)
            if retrieval_meta is not None:
                retrieval_meta["keyword_fallback"] = True

        save_message(session, 'assistant', bot_response, retrieval_meta)
        return JsonResponse({'response': bot_response})

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
