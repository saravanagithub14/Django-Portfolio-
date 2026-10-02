from django.contrib import admin
from portfolio.models import (
    UserProfile, Role, Metric, NavigationItem, BioSection, JourneyParagraph, Strength,
    SpokenLanguage, ExploreGridItem, SkillCategory, Skill, ProjectPage, ProjectCategory,
    Project, ExperiencePage, ExperienceSection, Job, EducationPage, Degree, Certification,
    PublicationsPage, BookChapter, ResearchArticle, Achievement, WorkshopsPage, WorkshopItem,
    SeminarItem, FocusPage, FocusCard, FocusPositioningEntry, LanguagePage, SpokenLang,
    ProgrammingLang, GalleryPage, ReelItem, VideoItem, BlogPage, BlogPost
)

# --- Shared Inlines ---
class RoleInline(admin.TabularInline):
    model = Role
    extra = 1

class MetricInline(admin.TabularInline):
    model = Metric
    extra = 1

class NavigationItemInline(admin.TabularInline):
    model = NavigationItem
    fk_name = 'parent'
    extra = 1

# --- User Profile Admin ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('site_title', 'user', 'location', 'email')
    inlines = [RoleInline, MetricInline]
    fieldsets = (
        ('Site Identity', {
            'fields': ('user', 'site_title', 'site_description', 'tagline', 'tagline_sub', 'profile_image', 'intro')
        }),
        ('Landing Section', {
            'fields': ('landing_quote', 'landing_highlight', 'landing_author', 'landing_welcome')
        }),
        ('Social Links & Contact', {
            'fields': ('email', 'github', 'github_handle', 'linkedin', 'linkedin_handle', 'medium', 'medium_handle', 'whatsapp', 'whatsapp_number', 'instagram', 'instagram_handle', 'orcid', 'researchgate', 'location', 'resume_url')
        }),
    )

# --- Bio Admin ---
class JourneyParagraphInline(admin.TabularInline):
    model = JourneyParagraph
    extra = 1

class StrengthInline(admin.TabularInline):
    model = Strength
    extra = 1

class SpokenLanguageInline(admin.TabularInline):
    model = SpokenLanguage
    extra = 1

class ExploreGridItemInline(admin.TabularInline):
    model = ExploreGridItem
    extra = 1

@admin.register(BioSection)
class BioSectionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'journey_title', 'teaching_title')
    inlines = [JourneyParagraphInline, StrengthInline, SpokenLanguageInline, ExploreGridItemInline]

# --- Skills Admin ---
class SkillInline(admin.TabularInline):
    model = Skill
    extra = 2

@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'profile', 'accordion_id', 'active', 'order')
    list_editable = ('active', 'order')
    inlines = [SkillInline]

# --- Projects Admin ---
class ProjectInline(admin.StackedInline):
    model = Project
    extra = 1
    fieldsets = (
        (None, {
            'fields': (('emoji', 'title'), 'category', 'description', 'tags', ('github_url', 'demo_url'), 'featured', 'order')
        }),
    )

@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('heading', 'project_page', 'order')
    list_editable = ('order',)
    inlines = [ProjectInline]

@admin.register(ProjectPage)
class ProjectPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')

# --- Experience Admin ---
class JobInline(admin.StackedInline):
    model = Job
    extra = 1

@admin.register(ExperienceSection)
class ExperienceSectionAdmin(admin.ModelAdmin):
    list_display = ('heading', 'experience_page', 'order')
    list_editable = ('order',)
    inlines = [JobInline]

@admin.register(ExperiencePage)
class ExperiencePageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')

# --- Education Admin ---
class DegreeInline(admin.TabularInline):
    model = Degree
    extra = 1

class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 1

@admin.register(EducationPage)
class EducationPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')
    inlines = [DegreeInline, CertificationInline]

# --- Publications Admin ---
class BookChapterInline(admin.TabularInline):
    model = BookChapter
    extra = 1

class ResearchArticleInline(admin.TabularInline):
    model = ResearchArticle
    extra = 1

class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 1

@admin.register(PublicationsPage)
class PublicationsPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')
    inlines = [BookChapterInline, ResearchArticleInline, AchievementInline]

# --- Workshops Admin ---
class WorkshopItemInline(admin.TabularInline):
    model = WorkshopItem
    extra = 1

class SeminarItemInline(admin.TabularInline):
    model = SeminarItem
    extra = 1

@admin.register(WorkshopsPage)
class WorkshopsPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')
    inlines = [WorkshopItemInline, SeminarItemInline]

# --- Focus Admin ---
class FocusCardInline(admin.TabularInline):
    model = FocusCard
    extra = 1

class FocusPositioningEntryInline(admin.TabularInline):
    model = FocusPositioningEntry
    extra = 1

@admin.register(FocusPage)
class FocusPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')
    inlines = [FocusCardInline, FocusPositioningEntryInline]

# --- Languages Admin ---
class SpokenLangInline(admin.TabularInline):
    model = SpokenLang
    extra = 1

class ProgrammingLangInline(admin.TabularInline):
    model = ProgrammingLang
    extra = 1

@admin.register(LanguagePage)
class LanguagePageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title')
    inlines = [SpokenLangInline, ProgrammingLangInline]

# --- Gallery Admin ---
class ReelItemInline(admin.TabularInline):
    model = ReelItem
    extra = 1

class VideoItemInline(admin.TabularInline):
    model = VideoItem
    extra = 1

@admin.register(GalleryPage)
class GalleryPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title', 'featured_title')
    inlines = [ReelItemInline, VideoItemInline]

# --- Blog Admin ---
class BlogPostInline(admin.StackedInline):
    model = BlogPost
    extra = 1

@admin.register(BlogPage)
class BlogPageAdmin(admin.ModelAdmin):
    list_display = ('profile', 'page_title', 'stats_total_posts')
    inlines = [BlogPostInline]

# --- Navigation and Graph Nodes ---
@admin.register(NavigationItem)
class NavigationItemAdmin(admin.ModelAdmin):
    list_display = ('label', 'profile', 'url', 'active_id', 'dropdown', 'parent', 'order')
    list_filter = ('profile', 'dropdown', 'parent')
    list_editable = ('order',)
    inlines = [NavigationItemInline]

# GraphNode is no longer registered: the 3D graph is generated from the content above
# (portfolio/graph.py), so edits to jobs, projects, skills, etc. show up in it automatically.

# --- Flat lists for the items edited most often ---
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """All projects in one place, including featured ones (which have no category)."""
    list_display = ('title', 'category', 'featured', 'order')
    list_editable = ('featured', 'order')
    list_filter = ('featured', 'category')
    search_fields = ('title', 'description', 'tags')
    fieldsets = (
        (None, {
            'fields': ('project_page', ('emoji', 'title'), 'category', 'description', 'tags', ('github_url', 'demo_url'), 'featured', 'order'),
            'description': 'Leave GitHub/Demo as "#" to hide the buttons. Featured projects appear at the top of the Projects page.',
        }),
    )

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'period', 'section', 'order')
    list_editable = ('order',)
    list_filter = ('section',)
    search_fields = ('title', 'company', 'description', 'tags')


admin.site.site_header = "Saravana's Portfolio — Admin"
admin.site.site_title = "Portfolio Admin"
admin.site.index_title = "Edit site content (changes show on the site and in the 3D graph immediately)"
