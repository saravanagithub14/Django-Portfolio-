from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    site_title = models.CharField(max_length=255, default="My Portfolio")
    site_description = models.TextField(blank=True, default="")
    tagline = models.CharField(max_length=255, blank=True, default="")
    tagline_sub = models.CharField(max_length=255, blank=True, default="")
    profile_image = models.CharField(max_length=255, default="static/images/profile.jpg")
    intro = models.TextField(blank=True, default="")
    
    # Social handles
    email = models.EmailField(blank=True, default="")
    github = models.URLField(blank=True, default="")
    github_handle = models.CharField(max_length=100, blank=True, default="")
    linkedin = models.URLField(blank=True, default="")
    linkedin_handle = models.CharField(max_length=100, blank=True, default="")
    medium = models.URLField(blank=True, default="")
    medium_handle = models.CharField(max_length=100, blank=True, default="")
    whatsapp = models.URLField(blank=True, default="")
    whatsapp_number = models.CharField(max_length=50, blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    instagram_handle = models.CharField(max_length=100, blank=True, default="")
    orcid = models.CharField(max_length=50, blank=True, default="")
    researchgate = models.URLField(blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    resume_url = models.CharField(max_length=255, default="static/resume.pdf")

    # Landing page configurations
    landing_quote = models.TextField(blank=True, default="")
    landing_highlight = models.TextField(blank=True, default="")
    landing_author = models.CharField(max_length=100, blank=True, default="")
    landing_welcome = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.site_title} ({self.user.username})"

class Role(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

class Metric(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='metrics')
    value = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.value} - {self.label}"

class NavigationItem(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='navigation_items')
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=255, blank=True, default="")
    active_id = models.CharField(max_length=50, blank=True, default="")
    dropdown = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        prefix = f"{self.parent.label} > " if self.parent else ""
        return f"{prefix}{self.label} ({'Dropdown' if self.dropdown else self.url})"

class BioSection(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='bio_section')
    journey_label = models.CharField(max_length=100, default="Professional Journey")
    journey_title = models.CharField(max_length=255, default="")
    teaching_label = models.CharField(max_length=100, default="Teaching & Mentorship")
    teaching_title = models.CharField(max_length=255, default="")
    teaching_description = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Bio Details for {self.profile.site_title}"

class JourneyParagraph(models.Model):
    bio_section = models.ForeignKey(BioSection, on_delete=models.CASCADE, related_name='paragraphs')
    text = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Paragraph {self.order} ({self.text[:30]}...)"

class Strength(models.Model):
    bio_section = models.ForeignKey(BioSection, on_delete=models.CASCADE, related_name='strengths')
    icon = models.CharField(max_length=10, default="🧪")
    title = models.CharField(max_length=100)
    description = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

class SpokenLanguage(models.Model):
    bio_section = models.ForeignKey(BioSection, on_delete=models.CASCADE, related_name='languages')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=100)
    level = models.IntegerField(default=100) # 0 to 100 percentage
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.name} ({self.proficiency})"

class ExploreGridItem(models.Model):
    bio_section = models.ForeignKey(BioSection, on_delete=models.CASCADE, related_name='explore_grid')
    icon = models.CharField(max_length=10, default="🕸️")
    title = models.CharField(max_length=100)
    desc = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

# --- SKILLS MODEL ---
class SkillCategory(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='skill_categories')
    accordion_id = models.CharField(max_length=100, default="core-ai")
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Skill Categories"
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

class Skill(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=255)
    highlight = models.BooleanField(default=False)
    tier = models.IntegerField(default=1) # 1, 2, or 3
    context = models.CharField(max_length=255, blank=True, default="")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

# --- PROJECTS MODEL ---
class ProjectPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='project_page')
    page_label = models.CharField(max_length=100, default="Portfolio")
    page_title = models.CharField(max_length=255, default="Projects")
    page_sub = models.TextField(blank=True, default="")
    featured_heading = models.CharField(max_length=255, default="⭐ Featured AI Projects")

    def __str__(self):
        return f"Project Page for {self.profile.site_title}"

class ProjectCategory(models.Model):
    project_page = models.ForeignKey(ProjectPage, on_delete=models.CASCADE, related_name='categories')
    heading = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Project Categories"
        ordering = ['order', 'id']

    def __str__(self):
        return self.heading

class Project(models.Model):
    project_page = models.ForeignKey(ProjectPage, on_delete=models.CASCADE, related_name='projects')
    category = models.ForeignKey(ProjectCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    emoji = models.CharField(max_length=10, default="🧠")
    title = models.CharField(max_length=255)
    description = models.TextField()
    tags = models.CharField(max_length=255, blank=True, default="") # Comma-separated tags
    github_url = models.CharField(max_length=255, default="#")
    demo_url = models.CharField(max_length=255, default="#")
    featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

# --- EXPERIENCE MODEL ---
class ExperiencePage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='experience_page')
    page_label = models.CharField(max_length=100, default="Career History")
    page_title = models.CharField(max_length=255, default="Experience")
    page_sub = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Experience Page for {self.profile.site_title}"

class ExperienceSection(models.Model):
    experience_page = models.ForeignKey(ExperiencePage, on_delete=models.CASCADE, related_name='sections')
    heading = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.heading

class Job(models.Model):
    section = models.ForeignKey(ExperienceSection, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    period = models.CharField(max_length=100)
    description = models.TextField() # Paragraph of job role
    tags = models.CharField(max_length=255, blank=True, default="") # Comma-separated
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.title} at {self.company}"

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

# --- EDUCATION MODEL ---
class EducationPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='education_page')
    page_label = models.CharField(max_length=100, default="Academic Background")
    page_title = models.CharField(max_length=255, default="Education & Certifications")
    page_sub = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Education Page for {self.profile.site_title}"

class Degree(models.Model):
    education_page = models.ForeignKey(EducationPage, on_delete=models.CASCADE, related_name='degrees')
    icon = models.CharField(max_length=10, default="🎓")
    degree = models.CharField(max_length=255)
    school = models.CharField(max_length=255)
    year = models.CharField(max_length=100)
    detail = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.degree} - {self.school}"

class Certification(models.Model):
    education_page = models.ForeignKey(EducationPage, on_delete=models.CASCADE, related_name='certifications')
    badge = models.CharField(max_length=10, default="🎖")
    name = models.CharField(max_length=255)
    detail = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

# --- PUBLICATIONS MODEL ---
class PublicationsPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='publications_page')
    page_label = models.CharField(max_length=100, default="Research Output")
    page_title = models.CharField(max_length=255, default="Publications & Achievements")
    page_sub = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Publications Page for {self.profile.site_title}"

class BookChapter(models.Model):
    publications_page = models.ForeignKey(PublicationsPage, on_delete=models.CASCADE, related_name='book_chapters')
    title = models.CharField(max_length=255)
    meta = models.TextField() # allows HTML like <em> or links
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

class ResearchArticle(models.Model):
    publications_page = models.ForeignKey(PublicationsPage, on_delete=models.CASCADE, related_name='research_articles')
    title = models.CharField(max_length=255)
    meta = models.TextField() # allows HTML
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

class Achievement(models.Model):
    publications_page = models.ForeignKey(PublicationsPage, on_delete=models.CASCADE, related_name='achievements')
    icon = models.CharField(max_length=10, default="🎖")
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

# --- SPEAKING & TALKS (WORKSHOPS) MODEL ---
class WorkshopsPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='workshops_page')
    page_label = models.CharField(max_length=100, default="Speaking & Training")
    page_title = models.CharField(max_length=255, default="Workshops & Talks")
    page_sub = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Workshops Page for {self.profile.site_title}"

class WorkshopItem(models.Model):
    workshops_page = models.ForeignKey(WorkshopsPage, on_delete=models.CASCADE, related_name='workshops')
    icon = models.CharField(max_length=10, default="⚙️")
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

class SeminarItem(models.Model):
    workshops_page = models.ForeignKey(WorkshopsPage, on_delete=models.CASCADE, related_name='seminars')
    icon = models.CharField(max_length=10, default="🤖")
    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

# --- CURRENT FOCUS MODEL ---
class FocusPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='focus_page')
    page_label = models.CharField(max_length=100, default="Now")
    page_title = models.CharField(max_length=255, default="Current Focus")
    page_sub = models.TextField(blank=True, default="")
    positioning_tagline = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Focus Page for {self.profile.site_title}"

class FocusCard(models.Model):
    focus_page = models.ForeignKey(FocusPage, on_delete=models.CASCADE, related_name='cards')
    icon = models.CharField(max_length=10, default="🤖")
    title = models.CharField(max_length=100)
    description = models.TextField()
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

class FocusPositioningEntry(models.Model):
    focus_page = models.ForeignKey(FocusPage, on_delete=models.CASCADE, related_name='positioning_entries')
    text = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text

# --- LANGUAGE CONFIG MODEL ---
class LanguagePage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='languages_page')
    page_label = models.CharField(max_length=100, default="Languages")
    page_title = models.CharField(max_length=255, default="Polyglot & Programmer")
    page_sub = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Language Page for {self.profile.site_title}"

class SpokenLang(models.Model):
    language_page = models.ForeignKey(LanguagePage, on_delete=models.CASCADE, related_name='spoken')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=100)
    level = models.IntegerField(default=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

class ProgrammingLang(models.Model):
    language_page = models.ForeignKey(LanguagePage, on_delete=models.CASCADE, related_name='programming')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=100)
    level = models.IntegerField(default=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

# --- GALLERY MODEL ---
class GalleryPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='gallery_page')
    page_label = models.CharField(max_length=100, default="Media")
    page_title = models.CharField(max_length=255, default="Gallery")
    page_sub = models.TextField(blank=True, default="")
    featured_title = models.CharField(max_length=255, blank=True, default="")
    featured_description = models.TextField(blank=True, default="")
    featured_embed_url = models.CharField(max_length=255, blank=True, default="")
    featured_category = models.CharField(max_length=100, blank=True, default="")
    featured_duration = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"Gallery Page for {self.profile.site_title}"

class ReelItem(models.Model):
    gallery_page = models.ForeignKey(GalleryPage, on_delete=models.CASCADE, related_name='reels')
    title = models.CharField(max_length=255)
    reel_url = models.CharField(max_length=255)
    reel_id = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

class VideoItem(models.Model):
    gallery_page = models.ForeignKey(GalleryPage, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255)
    description = models.TextField()
    embed_url = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

# --- BLOG MODEL ---
class BlogPage(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='blog_page')
    page_label = models.CharField(max_length=100, default="Thoughts")
    page_title = models.CharField(max_length=255, default="Blog")
    page_sub = models.TextField(blank=True, default="")
    stats_total_posts = models.CharField(max_length=50, blank=True, default="")
    stats_platform = models.CharField(max_length=100, blank=True, default="")
    stats_topics = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"Blog Page for {self.profile.site_title}"

class BlogPost(models.Model):
    blog_page = models.ForeignKey(BlogPage, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    excerpt = models.TextField()
    category = models.CharField(max_length=100)
    date = models.CharField(max_length=50) # e.g. "2026", "2024"
    read_time = models.CharField(max_length=100)
    emoji = models.CharField(max_length=10, default="📝")
    tags = models.CharField(max_length=255, blank=True, default="") # Comma-separated
    medium_url = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

# --- GRAPH NODE MODEL (OBSIDIAN 3D GRAPH) ---
class GraphNode(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='graph_nodes')
    node_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    node_type = models.CharField(max_length=100, default="leaf") # root, category, leaf
    navigate_to = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.node_id} ({self.name})"
