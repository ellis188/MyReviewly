import urllib.request, json, os, ssl, sys, traceback

try:
    ctx = ssl.create_default_context()
    
    CF_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    CF_ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    
    if not CF_TOKEN:
        print("ERROR: CLOUDFLARE_API_TOKEN not set")
        sys.exit(1)
    if not CF_ACCOUNT:
        print("ERROR: CLOUDFLARE_ACCOUNT_ID not set")
        sys.exit(1)
    
    print(f"Account ID length: {len(CF_ACCOUNT)}")
    print(f"API Token length: {len(CF_TOKEN)}")
    
    print("Downloading current worker from Cloudflare...")
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site/content"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}"})
    resp = urllib.request.urlopen(req, context=ctx)
    raw = resp.read().decode("utf-8")
    print(f"Downloaded {len(raw)} bytes")
    
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
    
    if ".hamburger" in js:
        print("Hamburger CSS already present")
    else:
        css = "        /* HAMBURGER MENU */\\n"
        css += "        .nav-links { display: flex; align-items: center; gap: 0; }\\n"
        css += "        .hamburger { display: none; background: none; border: none; cursor: pointer; padding: 8px; }\\n"
        css += "        .hamburger svg { width: 28px; height: 28px; stroke: var(--ink, #1a1a2e); }\\n"
        css += "        @media (max-width: 768px) {\\n"
        css += "            .hamburger { display: block; }\\n"
        css += "            .nav-links {\\n"
        css += "                display: none;\\n"
        css += "                position: absolute; top: 100%; right: 0; left: 0;\\n"
        css += "                background: rgba(255,255,255,0.98);\\n"
        css += "                backdrop-filter: blur(8px);\\n"
        css += "                flex-direction: column; padding: 16px 24px;\\n"
        css += "                border-bottom: 1px solid var(--border);\\n"
        css += "                box-shadow: 0 4px 12px rgba(0,0,0,0.08);\\n"
        css += "                gap: 12px;\\n"
        css += "            }\\n"
        css += "            .nav-links.open { display: flex; }\\n"
        css += "            .nav-links a { margin-right: 0 !important; font-size: 1rem; padding: 8px 0; }\\n"
        css += "            .nav-links a.cta-nav { width: 100%; text-align: center; padding: 12px; }\\n"
        css += "        }\\n\\n"
        
        if "/* HERO */" in js:
            js = js.replace("/* HERO */", css + "        /* HERO */")
            print("OK: hamburger CSS added")
        else:
            print("WARNING: /* HERO */ marker not found")
    
    old_nav = '<a href=\\"#pricing\\" style=\\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\\">Pricing</a><a href=\\"/login\\" style=\\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\\">Log In</a><a href=\\"/signup\\" class=\\"cta-nav\\">Start Free Trial</a>'
    
    nav_section = js[:js.find("</nav>")] if "</nav>" in js else ""
    
    if "nav-links" in nav_section:
        print("Hamburger button already present")
    elif old_nav in js:
        btn = '<button class=\\"hamburger\\" onclick=\\"this.nextElementSibling.classList.toggle('
        btn += "\\'"
        btn += "open"
        btn += "\\'"
        btn += ')\\" aria-label=\\"Menu\\"><svg viewBox=\\"0 0 24 24\\" fill=\\"none\\" stroke-width=\\"2\\" stroke-linecap=\\"round\\"><line x1=\\"3\\" y1=\\"6\\" x2=\\"21\\" y2=\\"6\\"/><line x1=\\"3\\" y1=\\"12\\" x2=\\"21\\" y2=\\"12\\"/><line x1=\\"3\\" y1=\\"18\\" x2=\\"21\\" y2=\\"18\\"/></svg></button><div class=\\"nav-links\\">'
        new_nav = btn + old_nav + "</div>"
        js = js.replace(old_nav, new_nav, 1)
        print("OK: hamburger button added")
    else:
        print("WARNING: nav pattern not found")
        print("Looking for nav content...")
        if "<nav>" in js or "<nav " in js:
            nav_start = js.find("<nav")
            nav_end = js.find("</nav>", nav_start)
            if nav_start > 0 and nav_end > 0:
                print(f"Nav found at positions {nav_start}-{nav_end}")
                nav_content = js[nav_start:nav_end+6]
                print(f"Nav length: {len(nav_content)} chars")
    
    with open("worker.js", "w", encoding="utf-8") as f:
        f.write(js)
    
    print(f"worker.js written: {len(js)} bytes")

except Exception as e:
    print(f"FATAL ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
