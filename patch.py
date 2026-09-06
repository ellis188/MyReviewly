import urllib.request, json, os, ssl, sys, traceback

try:
    ctx = ssl.create_default_context()
    CF_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    CF_ACCOUNT = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")

    if not CF_TOKEN or not CF_ACCOUNT:
        print("ERROR: Missing secrets"); sys.exit(1)

    print(f"Account ID: {CF_ACCOUNT[:4]}...{CF_ACCOUNT[-4:]}")

    # Try the correct Cloudflare API endpoint for worker script content
    urls_to_try = [
        f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site",
        f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site/content/v2",
    ]

    raw = None
    for url in urls_to_try:
        print(f"Trying: {url.split('/workers/')[1]}")
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {CF_TOKEN}",
                "Accept": "application/javascript"
            })
            resp = urllib.request.urlopen(req, context=ctx)
            raw = resp.read().decode("utf-8")
            print(f"OK: downloaded {len(raw)} bytes")
            break
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.reason}")
            continue

    if not raw:
        print("FATAL: Could not download worker from any endpoint")
        sys.exit(1)

    # The response might be JSON-wrapped or raw JS
    js = raw
    if raw.strip().startswith("{"):
        try:
            data = json.loads(raw)
            if "result" in data:
                js = data["result"]
                print("Unwrapped from JSON response")
        except:
            pass

    # If multipart, strip boundaries
    if "--" in js[:100] and "Content-Disposition" in js[:200]:
        lines = js.split("\n")
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
        print(f"Stripped multipart: {len(js)} bytes")

    # Add hamburger CSS
    if ".hamburger" in js:
        print("Hamburger CSS already present")
    elif "/* HERO */" in js:
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
        js = js.replace("/* HERO */", css + "        /* HERO */")
        print("OK: hamburger CSS added")
    else:
        print("WARNING: /* HERO */ not found")

    # Add hamburger button
    old_nav = '<a href=\\"#pricing\\" style=\\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\\">Pricing</a><a href=\\"/login\\" style=\\"margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;\\">Log In</a><a href=\\"/signup\\" class=\\"cta-nav\\">Start Free Trial</a>'

    nav_before_close = js[:js.find("</nav>")] if "</nav>" in js else ""
    if "nav-links" in nav_before_close:
        print("Hamburger button already present")
    elif old_nav in js:
        btn = '<button class=\\"hamburger\\" onclick=\\"this.nextElementSibling.classList.toggle('
        btn += "\\'"
        btn += "open"
        btn += "\\'"
        btn += ')\\" aria-label=\\"Menu\\"><svg viewBox=\\"0 0 24 24\\" fill=\\"none\\" stroke-width=\\"2\\" stroke-linecap=\\"round\\"><line x1=\\"3\\" y1=\\"6\\" x2=\\"21\\" y2=\\"6\\"/><line x1=\\"3\\" y1=\\"12\\" x2=\\"21\\" y2=\\"12\\"/><line x1=\\"3\\" y1=\\"18\\" x2=\\"21\\" y2=\\"18\\"/></svg></button><div class=\\"nav-links\\">'
        js = js.replace(old_nav, btn + old_nav + "</div>", 1)
        print("OK: hamburger button added")
    else:
        print("WARNING: nav pattern not found")

    with open("worker.js", "w", encoding="utf-8") as f:
        f.write(js)
    print(f"worker.js written: {len(js)} bytes")

except Exception as e:
    print(f"FATAL ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
