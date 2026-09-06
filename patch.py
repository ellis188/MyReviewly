import urllib.request, json, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

print("Downloading current worker from Cloudflare...")
url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site/content"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}"})
resp = urllib.request.urlopen(req, context=ctx)
raw = resp.read().decode("utf-8")
print(f"Downloaded {len(raw)} bytes")

# Strip multipart boundaries
lines = raw.split("\n")
js_lines = []
started = False
for line in lines:
    if "const LANDING_HTML" in line:
        started = True
    if started:
        if line.startswith("--") and len(line) > 30 and line.endswith("--"):
            break
        js_lines.append(line)
js = "\n".join(js_lines)
print(f"Extracted {len(js)} bytes of JS")

# Check if hamburger already exists
if ".hamburger" in js:
    print("Hamburger CSS already present - skipping CSS injection")
else:
    css = '        /* HAMBURGER MENU */\\n'
    css += '        .nav-links { display: flex; align-items: center; gap: 0; }\\n'
    css += '        .hamburger { display: none; background: none; border: none; cursor: pointer; padding: 8px; }\\n'
    css += '        .hamburger svg { width: 28px; height: 28px; stroke: var(--ink, #1a1a2e); }\\n'
    css += '        @media (max-width: 768px) {\\n'
    css += '            .hamburger { display: block; }\\n'
    css += '            .nav-links {\\n'
    css += '                display: none;\\n'
    css += '                position: absolute; top: 100%; right: 0; left: 0;\\n'
    css += '                background: rgba(255,255,255,0.98);\\n'
    css += '                backdrop-filter: blur(8px);\\n'
    css += '                flex-direction: column; padding: 16px 24px;\\n'
    css += '                border-bottom: 1px solid var(--border);\\n'
    css += '                box-shadow: 0 4px 12px rgba(0,0,0,0.08);\\n'
    css += '                gap: 12px;\\n'
    css += '            }\\n'
    css += '            .nav-links.open { display: flex; }\\n'
    css += '            .nav-links a { margin-right: 0 !important; font-size: 1rem; padding: 8px 0; }\\n'
    css += '            .nav-links a.cta-nav { width: 100%; text-align: center; padding: 12px; }\\n'
    css += '        }\\n\\n'
    js = js.replace("/* HERO */", css + "        /* HERO */")
    print("OK: hamburger CSS added")

# Add hamburger button to nav
old_nav = '<a href=\\"#pricing\\" style=\\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\\">Pricing</a><a href=\\"/login\\" style=\\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\\">Log In</a><a href=\\"/signup\\" class=\\"cta-nav\\">Start Free Trial</a>'

if "nav-links" not in js.split("</nav>")[0]:
    btn = '<button class=\\"hamburger\\" onclick=\\"this.nextElementSibling.classList.toggle('
    btn += "'open'"
    btn += ')\\" aria-label=\\"Menu\\"><svg viewBox=\\"0 0 24 24\\" fill=\\"none\\" stroke-width=\\"2\\" stroke-linecap=\\"round\\"><line x1=\\"3\\" y1=\\"6\\" x2=\\"21\\" y2=\\"6\\"/><line x1=\\"3\\" y1=\\"12\\" x2=\\"21\\" y2=\\"12\\"/><line x1=\\"3\\" y1=\\"18\\" x2=\\"21\\" y2=\\"18\\"/></svg></button><div class=\\"nav-links\\">'
    new_nav = btn + old_nav + "</div>"
    if old_nav in js:
        js = js.replace(old_nav, new_nav, 1)
        print("OK: hamburger button added to nav")
    else:
        print("WARNING: could not find nav links pattern")
else:
    print("Hamburger button already present - skipping")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)

print(f"worker.js written: {len(js)} bytes")
