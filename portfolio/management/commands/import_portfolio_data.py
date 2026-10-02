import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from portfolio.models import (
    UserProfile, Role, Metric, NavigationItem, BioSection, JourneyParagraph, Strength,
    SpokenLanguage, ExploreGridItem, SkillCategory, Skill, ProjectPage, ProjectCategory,
    Project, ExperiencePage, ExperienceSection, Job, EducationPage, Degree, Certification,
    PublicationsPage, BookChapter, ResearchArticle, Achievement, WorkshopsPage, WorkshopItem,
    SeminarItem, FocusPage, FocusCard, FocusPositioningEntry, LanguagePage, SpokenLang,
    ProgrammingLang, GalleryPage, ReelItem, VideoItem, BlogPage, BlogPost, GraphNode
)

class Command(BaseCommand):
    help = "Imports existing portfolio JSON data files into SQLite database models."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting portfolio JSON data import..."))

        # Setup standard admin user if none exists
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(username="admin").first()
        if not admin_user:
            self.stdout.write("No superuser found. Creating 'admin' user...")
            # Never a fixed default: the DB is committed and deployed, so a known password is a public login
            password = os.getenv("ADMIN_PASSWORD") or get_random_string(20)
            admin_user = User.objects.create_user(
                username="admin",
                email="admin@example.com",
                password=password,
                is_staff=True,
                is_superuser=True
            )
            if os.getenv("ADMIN_PASSWORD"):
                self.stdout.write(self.style.SUCCESS("'admin' user created with the password from ADMIN_PASSWORD"))
            else:
                self.stdout.write(self.style.SUCCESS(f"'admin' user created. Generated password (shown once): {password}"))

        # Find data directory
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        data_dir = base_dir / "users" / "default" / "data"

        if not data_dir.exists():
            self.stdout.write(self.style.ERROR(f"Data directory not found at {data_dir}"))
            return

        def load_json(name):
            filepath = data_dir / name
            if not filepath.exists():
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

        # 1. Config & User Profile
        config_data = load_json("config.json")
        if not config_data:
            self.stdout.write(self.style.ERROR("config.json not found. Aborting."))
            return

        # Clean existing Profile
        UserProfile.objects.filter(user=admin_user).delete()

        # Create Profile
        social = config_data.get("social", {})
        profile = UserProfile.objects.create(
            user=admin_user,
            site_title=config_data.get("site_title", ""),
            site_description=config_data.get("site_description", ""),
            tagline=config_data.get("tagline", ""),
            tagline_sub=config_data.get("tagline_sub", ""),
            profile_image=config_data.get("profile_image", "static/images/profile.jpg"),
            intro=config_data.get("intro", ""),
            email=social.get("email", ""),
            github=social.get("github", ""),
            github_handle=social.get("github_handle", ""),
            linkedin=social.get("linkedin", ""),
            linkedin_handle=social.get("linkedin_handle", ""),
            medium=social.get("medium", ""),
            medium_handle=social.get("medium_handle", ""),
            whatsapp=social.get("whatsapp", ""),
            whatsapp_number=social.get("whatsapp_number", ""),
            instagram=social.get("instagram", ""),
            instagram_handle=social.get("instagram_handle", ""),
            orcid=social.get("orcid", ""),
            researchgate=social.get("researchgate", ""),
            location=social.get("location", ""),
            resume_url=social.get("resume_url", "static/resume.pdf"),
            landing_quote=config_data.get("landing_quote", ""),
            landing_highlight=config_data.get("landing_highlight", ""),
            landing_author=config_data.get("landing_author", ""),
            landing_welcome=config_data.get("landing_welcome", "")
        )
        self.stdout.write(self.style.SUCCESS("UserProfile created."))

        # Create Roles
        for idx, role_name in enumerate(config_data.get("roles", [])):
            Role.objects.create(profile=profile, name=role_name, order=idx)
        self.stdout.write(f"  Imported {profile.roles.count()} roles.")

        # Create Metrics
        for idx, metric_data in enumerate(config_data.get("metrics", [])):
            Metric.objects.create(
                profile=profile,
                value=metric_data.get("value", ""),
                label=metric_data.get("label", ""),
                order=idx
            )
        self.stdout.write(f"  Imported {profile.metrics.count()} metrics.")

        # Create Navigation
        for idx, nav in enumerate(config_data.get("navigation", [])):
            if nav.get("dropdown"):
                parent_nav = NavigationItem.objects.create(
                    profile=profile,
                    label=nav.get("label", ""),
                    active_id=nav.get("id", ""),
                    dropdown=True,
                    order=idx
                )
                for c_idx, child in enumerate(nav.get("children", [])):
                    NavigationItem.objects.create(
                        profile=profile,
                        label=child.get("label", ""),
                        url=child.get("url", ""),
                        active_id=child.get("id", ""),
                        parent=parent_nav,
                        order=c_idx
                    )
            else:
                NavigationItem.objects.create(
                    profile=profile,
                    label=nav.get("label", ""),
                    url=nav.get("url", ""),
                    active_id=nav.get("id", ""),
                    order=idx
                )
        self.stdout.write(f"  Imported {profile.navigation_items.count()} navigation items.")

        # Create default chatbot config linked to this configuration
        try:
            from chatbot.models import AIModelConfig, Chatbot
            # Check if chatbot and config exist
            if not Chatbot.objects.exists():
                chat_widget_data = config_data.get("chat_widget", {})
                if chat_widget_data.get("enabled"):
                    ai_config = AIModelConfig.objects.create(
                        name="Default Gemini Config",
                        provider="gemini",
                        model_name="gemini-1.5-flash",
                        system_prompt=f"You are an AI assistant representing {profile.site_title}. Answer questions about his experience, projects, skills, education, and research with professional discipline. If you do not know, say so."
                    )
                    Chatbot.objects.create(
                        bot_name=chat_widget_data.get("bot_name", profile.site_title),
                        enabled=True,
                        model_config=ai_config
                    )
                    self.stdout.write(self.style.SUCCESS("Created default Chatbot configurations."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not initialize chatbot model config: {e}"))

        # 2. Bio & Details
        bio_data = load_json("bio.json")
        if bio_data:
            journey_data = bio_data.get("journey", {})
            teaching_data = bio_data.get("teaching", {})
            bio_sec = BioSection.objects.create(
                profile=profile,
                journey_label=journey_data.get("label", "Professional Journey"),
                journey_title=journey_data.get("title", ""),
                teaching_label=teaching_data.get("label", "Teaching & Mentorship"),
                teaching_title=teaching_data.get("title", ""),
                teaching_description=teaching_data.get("description", "")
            )

            # Journey Paragraphs
            for idx, para in enumerate(journey_data.get("paragraphs", [])):
                JourneyParagraph.objects.create(bio_section=bio_sec, text=para, order=idx)

            # Strengths
            strengths_data = bio_data.get("strengths", {})
            for idx, entry in enumerate(strengths_data.get("entries", [])):
                Strength.objects.create(
                    bio_section=bio_sec,
                    icon=entry.get("icon", "🧪"),
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    order=idx
                )

            # Spoken Languages
            for idx, lang in enumerate(bio_data.get("languages", [])):
                SpokenLanguage.objects.create(
                    bio_section=bio_sec,
                    name=lang.get("name", ""),
                    proficiency=lang.get("level", ""),
                    level=80, # default percentage
                    order=idx
                )

            # Explore Grid
            for idx, item in enumerate(bio_data.get("explore_grid", [])):
                ExploreGridItem.objects.create(
                    bio_section=bio_sec,
                    icon=item.get("icon", "🕸️"),
                    title=item.get("title", ""),
                    desc=item.get("desc", ""),
                    url=item.get("url", ""),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("BioSection imported successfully."))

        # 3. Skills
        skills_data = load_json("skills.json")
        if skills_data:
            for idx, group in enumerate(skills_data.get("accordion_groups", [])):
                cat = SkillCategory.objects.create(
                    profile=profile,
                    accordion_id=group.get("id", ""),
                    name=group.get("name", ""),
                    active=group.get("active", False),
                    order=idx
                )
                for s_idx, skill in enumerate(group.get("tags", [])):
                    Skill.objects.create(
                        category=cat,
                        name=skill.get("name", ""),
                        highlight=skill.get("highlight", False),
                        tier=skill.get("tier", 1),
                        context=skill.get("context", ""),
                        order=s_idx
                    )
            self.stdout.write(self.style.SUCCESS("Skills imported successfully."))

        # 4. Projects
        projects_data = load_json("projects.json")
        if projects_data:
            proj_page = ProjectPage.objects.create(
                profile=profile,
                page_label=projects_data.get("page_label", "Portfolio"),
                page_title=projects_data.get("page_title", "Projects"),
                page_sub=projects_data.get("page_sub", ""),
                featured_heading=projects_data.get("featured", {}).get("heading", "⭐ Featured AI Projects")
            )

            # Featured Projects
            for idx, entry in enumerate(projects_data.get("featured", {}).get("entries", [])):
                Project.objects.create(
                    project_page=proj_page,
                    emoji=entry.get("emoji", "🧠"),
                    title=entry.get("title", ""),
                    description=entry.get("description", ""),
                    tags=", ".join(entry.get("tags", [])),
                    github_url=entry.get("github_url", "#"),
                    demo_url=entry.get("demo_url", "#"),
                    featured=True,
                    order=idx
                )

            # Categorized Projects
            for c_idx, cat_data in enumerate(projects_data.get("categories", [])):
                cat = ProjectCategory.objects.create(
                    project_page=proj_page,
                    heading=cat_data.get("heading", ""),
                    order=c_idx
                )
                for idx, entry in enumerate(cat_data.get("entries", [])):
                    Project.objects.create(
                        project_page=proj_page,
                        category=cat,
                        emoji="🔮" if "GenAI" in cat.heading else "📊" if "Machine" in cat.heading else "🔬",
                        title=entry.get("name", ""),
                        description=entry.get("desc", ""),
                        tags="",
                        github_url=entry.get("url", "#"),
                        demo_url="#",
                        featured=False,
                        order=idx
                    )
            self.stdout.write(self.style.SUCCESS("Projects imported successfully."))

        # 5. Experience
        experience_data = load_json("experience.json")
        if experience_data:
            exp_page = ExperiencePage.objects.create(
                profile=profile,
                page_label=experience_data.get("page_label", "Career History"),
                page_title=experience_data.get("page_title", "Experience"),
                page_sub=experience_data.get("page_sub", "")
            )
            for s_idx, sec in enumerate(experience_data.get("sections", [])):
                section = ExperienceSection.objects.create(
                    experience_page=exp_page,
                    heading=sec.get("heading", ""),
                    order=s_idx
                )
                for idx, job_data in enumerate(sec.get("jobs", [])):
                    Job.objects.create(
                        section=section,
                        title=job_data.get("title", ""),
                        company=job_data.get("company", ""),
                        period=job_data.get("period", ""),
                        description=job_data.get("description", ""),
                        tags=", ".join(job_data.get("tags", [])),
                        order=idx
                    )
            self.stdout.write(self.style.SUCCESS("Experiences imported successfully."))

        # 6. Education
        education_data = load_json("education.json")
        if education_data:
            edu_page = EducationPage.objects.create(
                profile=profile,
                page_label=education_data.get("page_label", "Academic Background"),
                page_title=education_data.get("page_title", "Education & Certifications"),
                page_sub=education_data.get("page_sub", "")
            )
            for idx, degree_data in enumerate(education_data.get("degrees", [])):
                Degree.objects.create(
                    education_page=edu_page,
                    icon=degree_data.get("icon", "🎓"),
                    degree=degree_data.get("degree", ""),
                    school=degree_data.get("school", ""),
                    year=degree_data.get("year", ""),
                    detail=degree_data.get("detail", ""),
                    order=idx
                )
            for idx, cert_data in enumerate(education_data.get("certifications", [])):
                Certification.objects.create(
                    education_page=edu_page,
                    badge=cert_data.get("badge", "🎖"),
                    name=cert_data.get("name", ""),
                    detail=cert_data.get("detail", ""),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Education imported successfully."))

        # 7. Publications
        publications_data = load_json("publications.json")
        if publications_data:
            pub_page = PublicationsPage.objects.create(
                profile=profile,
                page_label=publications_data.get("page_label", "Research Output"),
                page_title=publications_data.get("page_title", "Publications & Achievements"),
                page_sub=publications_data.get("page_sub", "")
            )
            for idx, chapter in enumerate(publications_data.get("book_chapters", [])):
                BookChapter.objects.create(
                    publications_page=pub_page,
                    title=chapter.get("title", ""),
                    meta=chapter.get("meta", ""),
                    order=idx
                )
            for idx, article in enumerate(publications_data.get("research_articles", [])):
                ResearchArticle.objects.create(
                    publications_page=pub_page,
                    title=article.get("title", ""),
                    meta=article.get("meta", ""),
                    order=idx
                )
            for idx, ach in enumerate(publications_data.get("achievements", [])):
                Achievement.objects.create(
                    publications_page=pub_page,
                    icon=ach.get("icon", "🎖"),
                    title=ach.get("title", ""),
                    description=ach.get("description", ""),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Publications & Achievements imported successfully."))

        # 8. Workshops
        workshops_data = load_json("workshops.json")
        if workshops_data:
            ws_page = WorkshopsPage.objects.create(
                profile=profile,
                page_label=workshops_data.get("page_label", "Speaking & Training"),
                page_title=workshops_data.get("page_title", "Workshops & Talks"),
                page_sub=workshops_data.get("page_sub", "")
            )
            for idx, item in enumerate(workshops_data.get("workshops", [])):
                WorkshopItem.objects.create(
                    workshops_page=ws_page,
                    icon=item.get("icon", "⚙️"),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    order=idx
                )
            for idx, item in enumerate(workshops_data.get("seminars", [])):
                SeminarItem.objects.create(
                    workshops_page=ws_page,
                    icon=item.get("icon", "🤖"),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Workshops & Talks imported successfully."))

        # 9. Focus
        focus_data = load_json("focus.json")
        if focus_data:
            f_page = FocusPage.objects.create(
                profile=profile,
                page_label=focus_data.get("page_label", "Now"),
                page_title=focus_data.get("page_title", "Current Focus"),
                page_sub=focus_data.get("page_sub", ""),
                positioning_tagline=focus_data.get("positioning", {}).get("tagline", "")
            )
            for idx, card in enumerate(focus_data.get("cards", [])):
                FocusCard.objects.create(
                    focus_page=f_page,
                    icon=card.get("icon", "🤖"),
                    title=card.get("title", ""),
                    description=card.get("description", ""),
                    order=idx
                )
            for idx, entry in enumerate(focus_data.get("positioning", {}).get("entries", [])):
                FocusPositioningEntry.objects.create(
                    focus_page=f_page,
                    text=entry,
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Current Focus imported successfully."))

        # 10. Languages
        languages_data = load_json("languages.json")
        if languages_data:
            lang_page = LanguagePage.objects.create(
                profile=profile,
                page_label="Languages",
                page_title="Polyglot & Programmer",
                page_sub="Bridging biological complexity and computational intelligence through diverse languages."
            )
            for idx, lang in enumerate(languages_data.get("spoken", [])):
                SpokenLang.objects.create(
                    language_page=lang_page,
                    name=lang.get("name", ""),
                    proficiency=lang.get("proficiency", ""),
                    level=lang.get("level", 100),
                    order=idx
                )
            for idx, lang in enumerate(languages_data.get("programming", [])):
                ProgrammingLang.objects.create(
                    language_page=lang_page,
                    name=lang.get("name", ""),
                    proficiency=lang.get("proficiency", ""),
                    level=lang.get("level", 100),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Languages page imported successfully."))

        # 11. Gallery
        gallery_data = load_json("gallery.json")
        if gallery_data:
            feat = gallery_data.get("featured", {})
            gal_page = GalleryPage.objects.create(
                profile=profile,
                page_label=gallery_data.get("page_label", "Media"),
                page_title=gallery_data.get("page_title", "Gallery"),
                page_sub=gallery_data.get("page_sub", ""),
                featured_title=feat.get("title", ""),
                featured_description=feat.get("description", ""),
                featured_embed_url=feat.get("embed_url", ""),
                featured_category=feat.get("category", ""),
                featured_duration=feat.get("duration", "")
            )
            for idx, item in enumerate(gallery_data.get("reels", [])):
                ReelItem.objects.create(
                    gallery_page=gal_page,
                    title=item.get("title", ""),
                    reel_url=item.get("reel_url", ""),
                    reel_id=item.get("reel_id", ""),
                    order=idx
                )
            for idx, item in enumerate(gallery_data.get("videos", [])):
                VideoItem.objects.create(
                    gallery_page=gal_page,
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    embed_url=item.get("embed_url", ""),
                    category=item.get("category", ""),
                    duration=item.get("duration", ""),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Gallery items imported successfully."))

        # 12. Blogs
        blogs_data = load_json("blogs.json")
        if blogs_data:
            stats = blogs_data.get("stats", {})
            blog_page = BlogPage.objects.create(
                profile=profile,
                page_label=blogs_data.get("page_label", "Thoughts"),
                page_title=blogs_data.get("page_title", "Blog"),
                page_sub=blogs_data.get("page_sub", ""),
                stats_total_posts=stats.get("total_posts", ""),
                stats_platform=stats.get("platform", ""),
                stats_topics=stats.get("topics", "")
            )
            for idx, post in enumerate(blogs_data.get("posts", [])):
                BlogPost.objects.create(
                    blog_page=blog_page,
                    title=post.get("title", ""),
                    excerpt=post.get("excerpt", ""),
                    category=post.get("category", ""),
                    date=post.get("date", ""),
                    read_time=post.get("read_time", ""),
                    emoji=post.get("emoji", "📝"),
                    tags=", ".join(post.get("tags", [])),
                    medium_url=post.get("medium_url", ""),
                    order=idx
                )
            self.stdout.write(self.style.SUCCESS("Medium Blogs imported successfully."))

        # 13. D3 3D Graph Nodes
        graph_data = load_json("graph.json")
        if graph_data:
            def save_graph_node(node_dict, parent_node=None, order_val=0):
                node_id = node_dict.get("id", node_dict.get("name", ""))
                
                # Check for duplicates or generate unique id if empty
                if not node_id:
                    node_id = f"node_{GraphNode.objects.count()}"

                new_node = GraphNode.objects.create(
                    profile=profile,
                    node_id=node_id,
                    name=node_dict.get("name", ""),
                    node_type=node_dict.get("type", "leaf"),
                    navigate_to=node_dict.get("navigateTo", ""),
                    description=node_dict.get("description", ""),
                    parent=parent_node,
                    order=order_val
                )
                
                for c_idx, child in enumerate(node_dict.get("children", [])):
                    save_graph_node(child, new_node, c_idx)
                    
            save_graph_node(graph_data)
            self.stdout.write(self.style.SUCCESS("3D D3 force-graph nodes tree imported recursively."))

        self.stdout.write(self.style.SUCCESS("All data files successfully migrated to Django SQLite database!"))
