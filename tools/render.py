"""Render a Design canvas .dc.html poster (static, no {{holes}}) to a 1080x1350 JPEG.

Usage: python3 render.py <poster.dc.html> <out.jpg> <blob_dir>
Always output .jpg: TikTok (Business) rejects PNG photos ("image/png not allowed").
blob_dir holds the logo files named <blob_id>.png; /_blob/<id> references are
rewritten to those local files. Inter and Noto Color Emoji must be installed.
"""
import re, sys, pathlib
from playwright.sync_api import sync_playwright

src, out, blob_dir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]).resolve()
outp = pathlib.Path(out)
if outp.suffix.lower() not in (".jpg", ".jpeg"):
    outp = outp.with_suffix(".jpg")
html = pathlib.Path(src).read_text(encoding="utf-8")

body = re.search(r"<x-dc>(.*)</x-dc>", html, re.S).group(1)
styles = "".join(re.findall(r"<style>(.*?)</style>", body, re.S))
body = re.sub(r"<helmet>.*?</helmet>", "", body, flags=re.S)
body = re.sub(r"/_blob/([0-9a-f]{32})", lambda m: (blob_dir / f"{m.group(1)}.png").as_uri(), body)
# Web fonts (e.g. Google Fonts) may be loaded with @import inside the poster's
# <style>; @import only works at the top of a stylesheet, so move it there.
# (Google Fonts URLs contain ';' inside url(...), so match the url() as a whole.)
IMPORT_RE = r"""@import\s+(?:url\(\s*(?:'[^']*'|"[^"]*"|[^)]*)\s*\)|'[^']*'|"[^"]*")[^;]*;"""
imports = "".join(re.findall(IMPORT_RE, styles))
styles = re.sub(IMPORT_RE, "", styles)
page = f"""<!doctype html><html><head><meta charset="utf-8">
<style>{imports} html,body{{margin:0;padding:0;background:#fff}} {styles}
body{{font-family:'Inter','Noto Color Emoji',sans-serif}}</style></head>
<body>{body}</body></html>"""
outp.parent.mkdir(parents=True, exist_ok=True)
tmp = outp.with_suffix(".tmp.html")
tmp.write_text(page, encoding="utf-8")

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
    pg.goto(tmp.resolve().as_uri())
    # Wait for web fonts and remote images (free stock photos) to finish loading.
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    try:
        pg.evaluate("document.fonts.ready.then(() => true)")
    except Exception:
        pass
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(outp), type="jpeg", quality=92,
                  clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
    b.close()
tmp.unlink()
print("rendered", outp)
