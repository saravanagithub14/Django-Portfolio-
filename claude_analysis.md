Yes. There's a portfolio tool connected here that covers Saravana Perumal R. Your git user is set to that name, so I'm guessing this is you. Here's what the portfolio says:

Current work
- Gen AI Engineer at Blackbox Learning, working in data science and AI since September 2023 (about 3 years).
- Before that: an internship at Edure, then just over two years at Dexpro Innovations Pvt Ltd.

Earlier career: about 5–7 years of life sciences research (2016–2023)
- SCTIMST: Senior Research Fellow working on biomaterials and tissue engineering, including 3D bioprinting of skin, an antimicrobial hydrogel and nanosilver.
- IISER Thiruvananthapuram: stem cell signaling.
- ICAR-CIBA, Chennai: a sea bass vaccine.
- Four publications: two book chapters (2019, 2022) and two research articles (both 2021).

Projects and skills: 51 projects, mostly in GenAI and LangChain. Two examples:
- A YouTube and website content summarizer (YouTube Transcript API, web scraping, LangChain loaders and splitters).
- A text summarizer that compares LangChain's Stuff, MapReduce and Refine strategies.

The portfolio also covers teaching (workshops, talks), education, certifications, blog posts, media, and an assistant called V.E.R.A.

Sources: saravanar.in, plus its experience, projects and skills pages.

✻ Brewed for 20s · done 2:41 PM

❯ what are the main issues of the website

  Listed 1 directory, ran 4 shell commands

I'm doing a few last checks now. The big one: the site's error page shows Django debug output.

  Ran 1 shell command

I checked the live site, www.saravanar.in. Every nav page loads (200), but there's one serious problem and a few smaller ones.

1. Critical: Django is running with DEBUG = True in production
- Any page that doesn't exist (for example /about.html) shows Django's debug 404 page instead of a normal "not found" page.
- That page lists your project name (portfolio_hub) and every URL route: admin/, login/, chatbot/, health and update_context.
- With DEBUG on, any server error would also show a full traceback: settings, file paths and local variables. That can leak secrets such as API keys for the V.E.R.A. chatbot.
- update_context sounds like it changes the chatbot's knowledge base. Make sure it requires login. I didn't call it, to avoid triggering a write.
- Fix: set DEBUG = False and ALLOWED_HOSTS in production, and add a custom 404.html. Then rotate any keys in case they were ever exposed through an error page.

2. Broken links to the old Vercel site
- All 11 content pages link to saravanaperumal.vercel.app/... (skills, projects, experience, publications, contact).
- Every one of those returns 404. Update or remove them.

3. Weak SEO on the homepage
- The homepage title is "Welcome to the Multiverse". Your name isn't in it, which is the main thing people search for.
- It has no meta description, no Open Graph tags and no <h1>. The other pages have all three, so the homepage is the odd one out.
- projects.html has a generic title ("Saravana Perumal R."); the other pages say which section they are.
- There's no robots.txt and no sitemap.xml (both 404).

4. Performance
- The favicon is 422 KB. It should be about 5 KB.
- The profile photo is 368 KB and could be compressed or switched to WebP.
- There's a snowfall animation on 11 pages, and a 3D graph that loads three.js from unpkg. Both are heavy on low-end phones.
- The display font comes from db.onlinewebfonts.com, a third-party host that's slow and not always reliable. Hosting the font yourself would fix that.
- My first homepage request took about 50 seconds, though later ones took about 1 second. That's probably a cold start on the server; check whether your host puts idle apps to sleep.

5. Homepage content
The homepage is only the 3D graph, so search engines and screen readers find almost no real text on the page.

The good parts: HTTPS redirects work, nosniff and X-Frame-Options: DENY are set, every image has alt text, and every subpage has its own description and social-sharing tags.

The site's source code isn't on this machine. If you point me to it, I can fix items 1–3 directly; they're quick changes.