"""
LLM provider chain: CHATBOT_PROVIDER (or the active AIModelConfig) first, then any other provider
with an API key. OpenAI and Groq share one cached OpenAI SDK client; Gemini uses google.generativeai.

Calls made with fast=True (the router's JSON call) go to ROUTER_PROVIDER first: Groq by default when it has
a key, because routing is a small JSON task and Groq answered it in ~0.6s against ~1.3s for gpt-4o-mini.
"""
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# Env vars take priority over keys stored in the DB (DB keys tend to go stale)
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


LLM_TIMEOUT = 30.0

# Router calls: provider and model tried first ("chain" = the normal order). Groq's gpt-oss-20b with low
# reasoning effort routed the eval's questions correctly; without it, it sometimes broke the JSON format.
ROUTER_DEFAULT_PROVIDER = 'groq'
ROUTER_DEFAULT_MODELS = {'groq': 'openai/gpt-oss-20b'}


DEFAULT_TEMPERATURE = 0.6  # a little warmth so replies sound conversational, not robotic


MAX_OUTPUT_TOKENS = 400  # short chat-style replies


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


def call_openai_compatible(api_key, model_name, temperature, base_url, messages, max_tokens, json_mode=False):
    client = get_openai_client(api_key, base_url)
    extra = {'response_format': {'type': 'json_object'}} if json_mode else {}
    if 'gpt-oss' in model_name:
        # Reasoning model: low effort halves its latency, and the default can spend max_tokens on reasoning
        extra['reasoning_effort'] = 'low'
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


def provider_order(model_cfg, fast=False):
    """Preferred provider first (CHATBOT_PROVIDER env overrides the DB), then any other keyed provider as backup.
    Fast calls put the router provider in front of that."""
    preferred = os.getenv('CHATBOT_PROVIDER') or (model_cfg.provider if model_cfg else None)
    order = [preferred] if preferred else []
    router = router_provider() if fast else None
    if router:
        order = [router] + [p for p in order if p != router]
    return order + [p for p in PROVIDER_ENV_KEYS if p not in order]


def router_provider():
    """ROUTER_PROVIDER env ("chain" turns it off), else Groq if it has a key, else None (the normal chain)."""
    name = (os.getenv('ROUTER_PROVIDER') or '').strip().lower()
    if name == 'chain':
        return None
    name = name or ROUTER_DEFAULT_PROVIDER
    return name if name in PROVIDER_ENV_KEYS and os.getenv(PROVIDER_ENV_KEYS[name]) else None


def is_mock_provider(model_cfg):
    return (os.getenv('CHATBOT_PROVIDER') or (model_cfg.provider if model_cfg else '')) == 'mock'


def make_llm(model_cfg):
    """
    An LLM callable over the provider chain: tries each provider that has an API key, in order.
    llm(messages, temperature=None, max_tokens=..., json_mode=False, fast=False) -> (text, provider) or (None, None).
    temperature=None uses the provider's configured temperature. fast=True tries the router provider first,
    with ROUTER_MODEL (or its router default model).
    """
    def llm(messages, *, temperature=None, max_tokens=MAX_OUTPUT_TOKENS, json_mode=False, fast=False):
        router = router_provider() if fast else None
        for provider in provider_order(model_cfg, fast=fast):
            api_key, model_name, default_temperature, base_url = provider_settings(provider, model_cfg)
            if not api_key:
                continue
            if provider == router:
                model_name = os.getenv('ROUTER_MODEL') or ROUTER_DEFAULT_MODELS.get(provider) or model_name
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
