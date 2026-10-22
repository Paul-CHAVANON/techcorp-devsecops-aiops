"""Capture horodatée d'une page web pour le dossier evidence/ (Playwright headless + Pillow).

Ajoute en haut de l'image un bandeau avec l'URL et l'heure de capture (Europe/Paris).
Prérequis (hors requirements-dev, inutiles en CI) :
  pip install playwright pillow && python -m playwright install chromium
Usage :
  python scripts/capture.py URL evidence/B1-prometheus-targets.png --legend "Cible techcorp-api UP"
  python scripts/capture.py URL out.png --wait 10 --height 1100 --full-page --click "Firing"
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

TZ = ZoneInfo("Europe/Paris")
FONT = "/System/Library/Fonts/Menlo.ttc"


def _font(size: int):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def add_banner(path: Path, url: str, when: datetime, legend: str) -> None:
    img = Image.open(path).convert("RGB")
    scale = max(1, img.width // 1600)
    h = 64 * scale
    out = Image.new("RGB", (img.width, img.height + h), "#111827")
    out.paste(img, (0, h))
    d = ImageDraw.Draw(out)
    stamp = when.strftime("%d/%m/%Y %H:%M:%S") + f" (Europe/Paris, UTC{when.strftime('%z')[:3]}:{when.strftime('%z')[3:]})"
    d.text((14 * scale, 8 * scale), url, fill="#f9fafb", font=_font(18 * scale))
    d.text((14 * scale, 36 * scale), f"Capturé le {stamp}" + (f"  —  {legend}" if legend else ""),
           fill="#fbbf24", font=_font(16 * scale))
    out.save(path, optimize=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url")
    p.add_argument("out")
    p.add_argument("--legend", default="")
    p.add_argument("--wait", type=float, default=8, help="secondes d'attente après chargement (min. 6)")
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=1000)
    p.add_argument("--full-page", action="store_true")
    p.add_argument("--click", action="append", default=[], help="texte d'un élément à cliquer avant la capture")
    p.add_argument("--wait-for", help="sélecteur CSS à attendre avant la capture")
    a = p.parse_args()

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": a.width, "height": a.height},
                                locale="fr-FR", timezone_id="Europe/Paris", color_scheme="light")
        page.goto(a.url, wait_until="load", timeout=60_000)
        if a.wait_for:
            page.wait_for_selector(a.wait_for, timeout=60_000)
        page.wait_for_timeout(max(a.wait, 6) * 1000)
        for text in a.click:
            page.get_by_text(text, exact=False).first.click()
            page.wait_for_timeout(1500)
        # Grafana : attendre la fin des chargements de panneaux s'il en reste
        for _ in range(20):
            if page.locator('[aria-label="Panel loading bar"]').count() == 0:
                break
            page.wait_for_timeout(500)
        when = datetime.now(TZ)
        page.screenshot(path=str(out), full_page=a.full_page)
        final_url = page.url  # URL réellement affichée (un clic peut avoir changé de page)
        browser.close()
    add_banner(out, final_url, when, a.legend)
    print(f"{out} ({when.isoformat(timespec='seconds')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
