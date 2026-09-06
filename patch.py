import urllib.request, os, ssl, sys, re

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

print("Downloading worker...")
url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
print(f"Downloaded {len(raw)} bytes")

# Strip multipart
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print(f"Cleaned: {len(js)} bytes")

# Detect quote style by looking at what's actually in the nav
m = re.search(r'href=(.?)#pricing', js)
if m:
    q_char = m.group(1)
    print(f"Quote char around href: {repr(q_char)}")
else:
    print("Could not find #pricing in content!")
    q_char = ''

# CSS - use regex to find the HERO comment and insert before it
if ".hamburger" not in js:
    # Detect the newline style
    hero_match = re.search(r'(/\* HERO \*/)', js)
    if hero_match:
        # Check what comes before HERO to understand the line format
        before_hero = js[max(0,hero_match.start()-20):hero_match.start()]
        print(f"Before HERO: {repr(before_hero)}")
        
        # Use whatever newline style is in the file
        if "\\n" in before_hero:
            nl = "\\n"
        else:
            nl = "\n"
        
        css = f"        /* HAMBURGER MENU */{nl}"
        css += f"        .nav-links {{ display: flex; align-items: center; gap: 0; }}{nl}"
        css += f"        .hamburger {{ display: none; background: none; border: none; cursor: pointer; padding: 8px; }}{nl}"
        css += f"        .hamburger svg {{ width: 28px; height: 28px; stroke: var(--ink, #1a1a2e); }}{nl}"
        css += f"        @media (max-width: 768px) {{{nl}"
        css += f"            .hamburger {{ display: block; }}{nl}"
        css += f"            .nav-links {{{nl}"
        css += f"                display: none;{nl}"
        css += f"                position: absolute; top: 100%; right: 0; left: 0;{nl}"
        css += f"                background: rgba(255,255,255,0.98);{nl}"
        css += f"                backdrop-filter: blur(8px);{nl}"
        css += f"                flex-direction: column; padding: 16px 24px;{nl}"
        css += f"                border-bottom: 1px solid var(--border);{nl}"
        css += f"                box-shadow: 0 4px 12px rgba(0,0,0,0.08);{nl}"
        css += f"                gap: 12px;{nl}"
        css += f"            }}{nl}"
        css += f"            .nav-links.open {{ display: flex; }}{nl}"
        css += f"            .nav-links a {{ margin-right: 0 !important; font-size: 1rem; padding: 8px 0; }}{nl}"
        css += f"            .nav-links a.cta-nav {{ width: 100%; text-align: center; padding: 12px; }}{nl}"
        css += f"        }}{nl}{nl}"
        
        js = js[:hero_match.start()] + css + "        " + js[hero_match.start():]
        print("OK: CSS added")
    else:
        print("HERO not found")

# NAV - use regex to find the pricing/login/signup links regardless of quote style
nav_pattern = re.compile(r'(<a\s+href=[\\"]?#pricing[\\"]?[^>]*>Pricing</a>\s*<a\s+href=[\\"]?/login[\\"]?[^>]*>Log In</a>\s*<a\s+href=[\\"]?/signup[\\"]?[^>]*>Start Free Trial</a>)')
nav_match = nav_pattern.search(js)

if nav_match and "nav-links" not in js[max(0,nav_match.start()-200):nav_match.start()]:
    old = nav_match.group(1)
    print(f"Found nav ({len(old)} chars): {old[:80]}...")
    
    # Build button with same quote style
    q = q_char  # whatever quote char is used
    if q == '\\':
        # It's backslash-quote style (\")
        q = '\\"'
        sq = "\\'"
    elif q == '"':
        q = '"'
        sq = "'"
    else:
        q = '"'
        sq = "'"
    
    btn = f'<button class={q}hamburger{q} onclick={q}this.nextElementSibling.classList.toggle({sq}open{sq}){q} aria-label={q}Menu{q}>'
    btn += f'<svg viewBox={q}0 0 24 24{q} fill={q}none{q} stroke-width={q}2{q} stroke-linecap={q}round{q}>'
    btn += f'<line x1={q}3{q} y1={q}6{q} x2={q}21{q} y2={q}6{q}/>'
    btn += f'<line x1={q}3{q} y1={q}12{q} x2={q}21{q} y2={q}12{q}/>'
    btn += f'<line x1={q}3{q} y1={q}18{q} x2={q}21{q} y2={q}18{q}/>'
    btn += f'</svg></button><div class={q}nav-links{q}>'
    
    new = btn + old + "</div>"
    js = js.replace(old, new, 1)
    print("OK: hamburger button added")
elif nav_match:
    print("nav-links already present")
else:
    print("NAV PATTERN NOT FOUND via regex")
    # Emergency debug: show what's around Pricing
    pidx = js.find("Pricing")
    if pidx >= 0:
        print(f"Content around Pricing: {repr(js[max(0,pidx-80):pidx+30])}")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Saved: {len(js)} bytes")
