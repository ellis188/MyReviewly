-e # Hamburger menu patch - v2
import urllib.request, json, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

# Download current worker code
url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site/content"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}"})
resp = urllib.request.urlopen(req, context=ctx)
raw = resp.read().decode("utf-8")

# Strip multipart boundaries
lines = raw.split("
")
js_lines = []
started = False
for line in lines:
    if "const LANDING_HTML" in line:
        started = True
    if started:
        if line.startswith("--") and len(line) > 30 and line.endswith("--"):
            break
        js_lines.append(line)
js = "
".join(js_lines)

# Check if hamburger already exists
if ".hamburger" in js:
    print("Hamburger menu already present - skipping CSS injection")
else:
    # Add hamburger CSS before /* HERO */
    hamburger_css = (
        "        /* HAMBURGER MENU */\n"
        "        .nav-links { display: flex; align-items: center; gap: 0; }\n"
        "        .hamburger { display: none; background: none; border: none; cursor: pointer; padding: 8px; }\n"
        "        .hamburger svg { width: 28px; height: 28px; stroke: var(--ink, #1a1a2e); }\n"
        "        @media (max-width: 768px) {\n"
        "            .hamburger { display: block; }\n"
        "            .nav-links {\n"
        "                display: none;\n"
        "                position: absolute; top: 100%; right: 0; left: 0;\n"
        "                background: rgba(255,255,255,0.98);\n"
        "                backdrop-filter: blur(8px);\n"
        "                flex-direction: column; padding: 16px 24px;\n"
        "                border-bottom: 1px solid var(--border);\n"
        "                box-shadow: 0 4px 12px rgba(0,0,0,0.08);\n"
        "                gap: 12px;\n"
        "            }\n"
        "            .nav-links.open { display: flex; }\n"
        "            .nav-links a { margin-right: 0 !important; font-size: 1rem; padding: 8px 0; }\n"
        "            .nav-links a.cta-nav { width: 100%; text-align: center; padding: 12px; }\n"
        "        }\n\n"
    )
    js = js.replace("/* HERO */", hamburger_css + "        /* HERO */")
    print("OK: hamburger CSS added")

# Add hamburger button to nav
old_nav = """<a href=\"#pricing\" style=\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\">Pricing</a><a href=\"/login\" style=\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\">Log In</a><a href=\"/signup\" class=\"cta-nav\">Start Free Trial</a>"""

if old_nav in js and "nav-links" not in js.split("</nav>")[0].split("<nav>")[-1].split(old_nav)[0][-50:]:
    hamburger_btn = """<button class=\"hamburger\" onclick=\"this.nextElementSibling.classList.toggle('open')\" aria-label=\"Menu\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"2\" stroke-linecap=\"round\"><line x1=\"3\" y1=\"6\" x2=\"21\" y2=\"6\"/><line x1=\"3\" y1=\"12\" x2=\"21\" y2=\"12\"/><line x1=\"3\" y1=\"18\" x2=\"21\" y2=\"18\"/></svg></button><div class=\"nav-links\">"""
    new_nav = hamburger_btn + old_nav + "</div>"
    js = js.replace(old_nav, new_nav, 1)
    print("OK: hamburger button added to nav")
else:
    if "nav-links" in js:
        print("Hamburger button already present - skipping nav modification")
    else:
        print("WARNING: nav pattern not found")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)

print(f"worker.js written: {len(js)} bytes")
