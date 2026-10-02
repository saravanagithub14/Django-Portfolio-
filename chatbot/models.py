from django.db import models

class AIModelConfig(models.Model):
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('openai', 'OpenAI GPT'),
        ('groq', 'Groq (Llama 3)'),
        ('ollama', 'Ollama (Local LLM)'),
        ('mock', 'Mock / Keyword Matching Only'),
    ]

    name = models.CharField(max_length=100, default="Gemini Config")
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default='gemini')
    model_name = models.CharField(max_length=100, default="gemini-1.5-flash", help_text="e.g. gemini-1.5-flash, gpt-4o, llama3")
    api_key = models.CharField(max_length=255, blank=True, default="", help_text="Leave blank if using local Ollama or Mock provider")
    api_base_url = models.CharField(max_length=255, blank=True, default="", help_text="Base URL for API requests (optional)")
    system_prompt = models.TextField(
        blank=True, 
        default="You are an AI assistant representing Saravana Perumal R., a biologist turned AI engineer. Answer questions about his experience, projects, skills, education, and research with professional discipline and scientific rigor. If you do not know the answer, say so, and offer to help contact him.",
        help_text="Instructions for the AI model"
    )
    temperature = models.FloatField(default=0.7, help_text="Controls randomness: 0.0 is analytical, 1.0 is creative")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Model Configuration"

    def __str__(self):
        return f"{self.name} ({self.get_provider_display()} - {self.model_name})"

class Chatbot(models.Model):
    bot_name = models.CharField(max_length=100, default="Saravana's AI")
    enabled = models.BooleanField(default=True)
    welcome_message = models.TextField(default="Hi! I'm Saravana's AI assistant. Ask me anything about my experience, skills, or projects.")
    model_config = models.ForeignKey(AIModelConfig, on_delete=models.SET_NULL, null=True, blank=True, related_name='chatbots')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bot_name} ({'Enabled' if self.enabled else 'Disabled'})"

class ChatSession(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session: {self.session_id[:8]}..."

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    retrieval_meta = models.JSONField(
        null=True, blank=True,
        help_text="Assistant turns: routed question, intent, filters, retrieved chunks, fallback, provider, latency"
    )

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role.capitalize()}: {self.content[:50]}..."

class ContextSnippet(models.Model):
    """Text added through POST /update_context. Included as `type: update` chunks in every index build."""
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Snippet {self.pk}: {self.text[:50]}..."
