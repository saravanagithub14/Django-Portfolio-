import io
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from portfolio.models import ReelItem

# Instagram's embed draws its own play icon, which the gallery can't style, so each reel tile
# shows a saved cover instead and swaps in the embed on click. The covers are downloaded into
# static/ and committed, because Instagram's CDN links are signed and expire.
#
# The post's og:image has a play icon baked in; only the embed page's media image is clean, and
# the embed loads it with JavaScript, hence a headless browser (dev only: pip install playwright,
# then `playwright install chromium`).
THUMB_DIR = Path(settings.BASE_DIR) / 'static' / 'img' / 'reels'
THUMB_WIDTH = 360  # tiles are 180px wide; 2x for high-density screens


class Command(BaseCommand):
    help = "Downloads each Instagram reel's cover to static/img/reels/<reel_id>.jpg (skips existing ones)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Download covers that already exist too.")

    def handle(self, *args, force=False, **options):
        try:
            from playwright.sync_api import sync_playwright, Error as PlaywrightError
            from PIL import Image
        except ImportError:
            raise CommandError("Needs playwright and Pillow: pip install playwright pillow && playwright install chromium")

        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        reels = [r for r in ReelItem.objects.all() if force or not (THUMB_DIR / f'{r.reel_id}.jpg').exists()]
        if not reels:
            self.stdout.write("All reels already have covers.")
            return

        fetched = failed = 0
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            for reel in reels:
                try:
                    page.goto(f'https://www.instagram.com/p/{reel.reel_id}/embed/', wait_until='domcontentloaded')
                    src = page.wait_for_selector('img.EmbeddedMediaImage', timeout=15000).get_attribute('src')
                    response = page.request.get(src)
                    if not response.ok:
                        raise ValueError(f'image HTTP {response.status}')
                    image = Image.open(io.BytesIO(response.body())).convert('RGB')
                    if image.width > THUMB_WIDTH:
                        image = image.resize((THUMB_WIDTH, round(image.height * THUMB_WIDTH / image.width)), Image.LANCZOS)
                    path = THUMB_DIR / f'{reel.reel_id}.jpg'
                    image.save(path, 'JPEG', quality=82, optimize=True, progressive=True)
                    fetched += 1
                    self.stdout.write(f'{reel.reel_id}: saved ({path.stat().st_size // 1024} KB)')
                except (PlaywrightError, ValueError, OSError) as e:
                    failed += 1
                    self.stdout.write(self.style.WARNING(f'{reel.reel_id}: {e}'))
            browser.close()
        self.stdout.write(self.style.SUCCESS(f'{fetched} cover(s) saved, {failed} failed.'))
