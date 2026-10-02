from django.contrib import admin
from chatbot.models import AIModelConfig, Chatbot, ChatSession, ChatMessage, ContextSnippet

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    readonly_fields = ('role', 'content', 'timestamp')
    can_delete = False
    extra = 0

@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'model_name', 'temperature', 'updated_at')
    list_filter = ('provider',)
    search_fields = ('name', 'model_name', 'system_prompt')
    fieldsets = (
        ('General Config', {
            'fields': ('name', 'provider', 'model_name')
        }),
        ('API Parameters', {
            'fields': ('api_key', 'api_base_url', 'temperature')
        }),
        ('Behavior Guidance', {
            'fields': ('system_prompt',),
            'description': 'System prompt guidelines to frame the chatbot responses'
        }),
    )

@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ('bot_name', 'enabled', 'model_config', 'created_at')
    list_editable = ('enabled',)
    list_filter = ('enabled', 'model_config')
    search_fields = ('bot_name', 'welcome_message')

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user_ip', 'created_at')
    readonly_fields = ('session_id', 'user_ip', 'created_at')
    inlines = [ChatMessageInline]
    search_fields = ('session_id', 'user_ip')

@admin.register(ContextSnippet)
class ContextSnippetAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'created_at')
    search_fields = ('text',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'content_summary', 'timestamp')
    readonly_fields = ('session', 'role', 'content', 'timestamp', 'retrieval_meta')
    list_filter = ('role', 'timestamp')
    search_fields = ('content',)

    def content_summary(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    content_summary.short_description = "Message Snippet"
