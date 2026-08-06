import os
import json
import random
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from chatbot.models import Chatbot, ChatSession, ChatMessage, AIModelConfig
from portfolio.models import UserProfile
from chatbot.rag_service import get_retriever, add_document_to_index, get_vectors_and_embeddings

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

PROMPT_TEMPLATE = """
You are Saravana Perumal R. — an AI Practitioner, Data Scientist, and Educator. 
You respond in the first person ("I", "my") as Saravana in every reply.

Your task is to be a helpful, friendly, and expert AI assistant representing Saravana's portfolio and AI/Data Science knowledge.

═══════════════════════════════
GUIDELINES FOR ANSWERING
═══════════════════════════════

1. GREETINGS & CASUAL TALK (e.g., "hi", "hello", "who are you"):
   - Respond warmly and introduce yourself briefly as Saravana's AI representation.
   - Example: "Hi there! I'm Saravana's AI assistant. How can I help you today? Feel free to ask about my AI projects, technical skills, or concepts in machine learning and data science!"

2. TECHNICAL & GENERAL CONCEPTS (e.g., "what is machine learning?", "what is AI?", "explain neural networks"):
   - Explain the concept clearly, concisely, and accurately as an experienced AI Engineer and Data Scientist.
   - Use clear everyday analogies where helpful.
   - Keep answers well-structured and engaging.

3. PERSONAL & PROFESSIONAL QUESTIONS (e.g., "what are your skills?", "tell me about your projects", "where did you work?"):
   - Answer using the relevant information provided in the Context below.
   - Highlight key projects (e.g. MedVqa-RAG, BioShield-AI), core skills (Python, PyTorch, LangChain, RAG, SQL), and experience.

4. INTRUSIVE OR UNRELATED TOPICS (e.g. salary, dating life, unrelated trivia):
   - Politely redirect to AI, Data Science, or Saravana's professional work.

Context:
{context}

Question:
{question}

Answer:
"""

# Fallback answering function based on database keyword matching & concept lookup
def get_keyword_fallback_response(query, profile):
    query_lower = query.lower()

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

    for concept_key, concept_answer in CONCEPT_ANSWERS.items():
        if concept_key in query_lower:
            return concept_answer
    
    # 1. Check Projects
    from portfolio.models import Project, Skill, Job
    matched_projects = []
    for p in Project.objects.all():
        if p.title.lower() in query_lower or any(t.lower() in query_lower for t in p.tag_list) or (p.description and p.description.lower() in query_lower):
            matched_projects.append(p)
            
    if matched_projects:
        response_text = "I found these projects in my portfolio related to your question:\n\n"
        for p in matched_projects:
            feat_tag = " (Featured)" if p.featured else ""
            response_text += f" {p.emoji} **{p.title}**{feat_tag}\n"
            response_text += f"   *{p.description}*\n"
            if p.tags:
                response_text += f"   *Tags:* {p.tags}\n"
            if p.github_url and p.github_url != '#':
                response_text += f"   [GitHub Repository]({p.github_url})\n"
            response_text += "\n"
        return response_text

    # 2. Check Skills
    matched_skills = []
    for s in Skill.objects.all():
        if s.name.lower() in query_lower or (s.context and s.context.lower() in query_lower):
            matched_skills.append(s)
            
    if matched_skills:
        response_text = "Here are the relevant skills and technologies I work with:\n\n"
        for s in matched_skills:
            level_indicator = "Tier " + str(s.tier)
            context_tag = f" - *{s.context}*" if s.context else ""
            response_text += f"⚡ **{s.name}** ({level_indicator}){context_tag}\n"
        return response_text

    # 3. Check Experience / Jobs
    matched_jobs = []
    for j in Job.objects.all():
        if j.title.lower() in query_lower or j.company.lower() in query_lower or j.description.lower() in query_lower:
            matched_jobs.append(j)
            
    if matched_jobs:
        response_text = "Here is my relevant professional experience:\n\n"
        for j in matched_jobs:
            response_text += f"💼 **{j.title}** at **{j.company}** ({j.period})\n"
            response_text += f"   {j.description}\n\n"
        return response_text

    # General fallback
    contact_email = profile.email if profile else "saravanaperumalr14@gmail.com"
    return (
        f"Hi! I'm Saravana's AI assistant.\n\n"
        f"I am here to answer questions about Saravana's experience in AI Engineering, Data Science, machine learning research, and projects. "
        f"You can ask about specific skills, projects, or reach out directly at {contact_email}."
    )

def is_rate_limited(ip_address):
    """Simple minute-level cache rate limiting (max 10 requests per minute)"""
    cache_key = f"rate_limit_{ip_address}"
    requests_count = cache.get(cache_key, 0)
    if requests_count >= 10:
        return True
    cache.set(cache_key, requests_count + 1, timeout=60)
    return False

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
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
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
            # Log user message
            ChatMessage.objects.create(session=session, role='user', content=user_message)
        except Exception as e:
            logger.warning(f"Could not save chat session to DB: {e}")
            session = None

        # 3. Get active Chatbot configuration (auto-create default if missing)
        bot = Chatbot.objects.filter(enabled=True).first()
        if not bot:
            try:
                cfg, _ = AIModelConfig.objects.get_or_create(
                    name="Groq Llama 3 Default",
                    defaults={
                        'provider': 'groq',
                        'model_name': 'llama-3.1-8b-instant',
                        'api_key': '',
                        'temperature': 0.0,
                    }
                )
                bot = Chatbot.objects.create(
                    bot_name="Saravana's AI",
                    enabled=True,
                    model_config=cfg
                )
            except Exception as e:
                logger.warning(f"Could not auto-create Chatbot config: {e}")

        # Fallback to Mock if no bot is configured or if provider is mock
        if not bot or not bot.model_config or bot.model_config.provider == 'mock':
            bot_response = get_keyword_fallback_response(user_message, profile)
            if session:
                try:
                    ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
                except Exception:
                    pass
            return JsonResponse({'response': bot_response})

        model_cfg = bot.model_config

        # Handle provider: Groq LLM with RAG
        if model_cfg.provider == 'groq':
            api_key = model_cfg.api_key or os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("Groq API key is missing. Using keyword fallback.")
                bot_response = get_keyword_fallback_response(user_message, profile)
                if session:
                    try:
                        ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
                    except Exception:
                        pass
                return JsonResponse({'response': bot_response})

            try:
                from langchain_groq import ChatGroq
                from langchain_core.messages import HumanMessage
                
                # Retrieve context from FAISS RAG index safely
                context = ""
                try:
                    retriever = get_retriever()
                    if retriever is not None:
                        docs = retriever.invoke(user_message)
                        context = "\n\n".join([doc.page_content for doc in docs])
                except Exception as rag_err:
                    logger.warning(f"RAG retrieval error: {rag_err}")

                # If RAG vector store context is sparse, append portfolio database context directly
                if len(context.strip()) < 50:
                    from portfolio.models import Project, Skill, Job
                    db_docs = []
                    if profile:
                        db_docs.append(f"Name: {profile.display_name}. Title: {profile.headline}. Bio: {profile.bio_summary}")
                    skills_str = ", ".join([s.name for s in Skill.objects.all()[:15]])
                    if skills_str:
                        db_docs.append(f"Core Skills: {skills_str}")
                    projects_str = "; ".join([f"{p.title}: {p.description}" for p in Project.objects.filter(featured=True)[:5]])
                    if projects_str:
                        db_docs.append(f"Featured Projects: {projects_str}")
                    context = "\n\n".join(db_docs)

                # Format prompt template
                formatted_prompt = (
                    PROMPT_TEMPLATE
                    .replace("{context}", context)
                    .replace("{question}", user_message)
                )
                
                # Initialize ChatGroq LLM
                llm = ChatGroq(
                    groq_api_key=api_key,
                    model_name=model_cfg.model_name or "llama-3.1-8b-instant",
                    temperature=model_cfg.temperature or 0.0,
                    timeout=30.0,
                )
                
                response = llm.invoke([HumanMessage(content=formatted_prompt)])
                bot_response = response.content
                
            except Exception as e:
                logger.error(f"Groq API execution error: {e}", exc_info=True)
                bot_response = get_keyword_fallback_response(user_message, profile)

        # Handle provider: Google Gemini
        elif model_cfg.provider == 'gemini':
            api_key = model_cfg.api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("Gemini API key is missing. Using keyword fallback.")
                bot_response = get_keyword_fallback_response(user_message, profile)
                if session:
                    try:
                        ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
                    except Exception:
                        pass
                return JsonResponse({'response': bot_response})

            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)

                # Build standard context for prompt safely
                rag_context = ""
                try:
                    from chatbot.views import get_rag_context
                    rag_context = get_rag_context(user_message)
                except Exception:
                    pass

                full_system_instruction = f"{model_cfg.system_prompt}\n\n[CONTEXT ABOUT SARAVANA'S PORTFOLIO]:\n{rag_context}"
                
                generation_config = {
                    "temperature": model_cfg.temperature,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
                
                history = []
                if session:
                    messages_list = list(ChatMessage.objects.filter(session=session).order_by('timestamp'))
                    for msg in messages_list[:-1]:
                        role_val = 'user' if msg.role == 'user' else 'model'
                        history.append({'role': role_val, 'parts': [msg.content]})

                model = genai.GenerativeModel(
                    model_name=model_cfg.model_name,
                    generation_config=generation_config,
                    system_instruction=full_system_instruction
                )
                
                chat = model.start_chat(history=history)
                response = chat.send_message(user_message)
                bot_response = response.text
                
            except Exception as e:
                logger.error(f"Gemini API execution error: {e}", exc_info=True)
                bot_response = get_keyword_fallback_response(user_message, profile)

        else:
            bot_response = f"*(Provider {model_cfg.provider} is under development)*\n\n" + get_keyword_fallback_response(user_message, profile)

        # Log assistant response
        if session:
            try:
                ChatMessage.objects.create(session=session, role='assistant', content=bot_response)
            except Exception:
                pass

        return JsonResponse({'response': bot_response})

    except Exception as fatal_err:
        logger.error(f"Fatal error in chat endpoint: {fatal_err}", exc_info=True)
        fallback = get_keyword_fallback_response(user_message, UserProfile.objects.first())
        return JsonResponse({'response': fallback})


def health_view(request):
    """
    GET API checking vector database loading state and active configurations.
    """
    vectors, _ = get_vectors_and_embeddings()
    retriever = get_retriever()
    
    bot = Chatbot.objects.filter(enabled=True).first()
    is_healthy = (vectors is not None and retriever is not None)
    
    status = {
        "status": "healthy" if is_healthy else "unhealthy",
        "vector_store_loaded": vectors is not None,
        "retriever_initialized": retriever is not None,
        "active_chatbot": bot.bot_name if bot else None,
        "active_provider": bot.model_config.provider if bot and bot.model_config else "None"
    }
    return JsonResponse(status, status=200 if is_healthy else 500)

@csrf_exempt
def update_context_view(request):
    """
    POST Webhook allowing updating the FAISS vector database dynamically.
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

    success = add_document_to_index(update_text, source_name="webhook_update")
    if success:
        return JsonResponse({"status": "success", "message": "Context added and index saved successfully."})
    else:
        return JsonResponse({"error": "Failed to update vector database."}, status=500)
