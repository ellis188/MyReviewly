import urllib.request, json, os, ssl, sys, traceback

try:
    ctx = ssl.create_default_context()
    CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
    CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

    print("Downloading worker...")
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
    resp = urllib.request.urlopen(req, context=ctx)
    raw = resp.read().decode("utf-8")
    print(f"Downloaded {len(raw)} bytes")

    # Strip multipart
    lines = raw.split("\n")
    js_lines = []
    for line in lines:
        s = line.strip()
        if s.startswith("--") and len(s) > 20:
            continue
        if s.startswith("Content-Disposition:") or s.startswith("Content-Type:"):
            continue
        js_lines.append(line)
    js = "\n".join(js_lines).strip()
    print(f"JS: {len(js)} bytes")

    # DEBUG: Show what the nav area looks like
    nav_idx = js.find("<nav")
    if nav_idx < 0:
        nav_idx = js.find("<nav")
    if nav_idx >= 0:
        nav_end = js.find("</nav>", nav_idx)
        if nav_end > 0:
            nav_content = js[nav_idx:nav_end+6]
            print(f"NAV CONTENT ({len(nav_content)} chars):")
            print(nav_content[:300])
            print("...")

    # DEBUG: Check what kind of quotes are in the nav
    if 'href=\\"' in js:
        print("ESCAPING: double-backslash-quote (JS string literal)")
        quote = '\\"'
    elif 'href="' in js:
        print("ESCAPING: plain quotes (raw HTML)")
        quote = '"'
    else:
        print("ESCAPING: unknown")
        quote = '"'

    # Hamburger CSS
    if ".hamburger" in js:
        print("Hamburger CSS already present")
    else:
        # Build CSS with the right escaping
        nl = "\\n" if "\\n" in js[:500] else "\n"
        css_lines = [
            "        /* HAMBURGER MENU */" + nl,
            "        .nav-links { display: flex; align-items: center; gap: 0; }" + nl,
            "        .hamburger { display: none; background: none; border: none; cursor: pointer; padding: 8px; }" + nl,
            "        .hamburger svg { width: 28px; height: 28px; stroke: var(--ink, #1a1a2e); }" + nl,
            "        @media (max-width: 768px) {" + nl,
            "            .hamburger { display: block; }" + nl,
            "            .nav-links {" + nl,
            "                display: none;" + nl,
            "                position: absolute; top: 100%; right: 0; left: 0;" + nl,
            "                background: rgba(255,255,255,0.98);" + nl,
            "                backdrop-filter: blur(8px);" + nl,
            "                flex-direction: column; padding: 16px 24px;" + nl,
            "                border-bottom: 1px solid var(--border);" + nl,
            "                box-shadow: 0 4px 12px rgba(0,0,0,0.08);" + nl,
            "                gap: 12px;" + nl,
            "            }" + nl,
            "            .nav-links.open { display: flex; }" + nl,
            "            .nav-links a { margin-right: 0 !important; font-size: 1rem; padding: 8px 0; }" + nl,
            "            .nav-links a.cta-nav { width: 100%; text-align: center; padding: 12px; }" + nl,
            "        }" + nl + nl,
        ]
        css = "".join(css_lines)
        if "/* HERO */" in js:
            js = js.replace("/* HERO */", css + "        /* HERO */")
            print("OK: hamburger CSS added")
        else:
            print("ERROR: /* HERO */ not found")

    # Hamburger button - try both escaping styles
    q = quote  # either \" or "
    old_nav = f'<a href={q}#pricing{q} style={q}margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;{q}>Pricing</a><a href={q}/login{q} style={q}margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;{q}>Log In</a><a href={q}/signup{q} class={q}cta-nav{q}>Start Free Trial</a>'

    print(f"Looking for nav pattern ({len(old_nav)} chars)...")
    print(f"Pattern start: {old_nav[:60]}")

    nav_area = js[:js.find("</nav>")] if "</nav>" in js else ""
    if "nav-links" in nav_area:
        print("Hamburger button already in nav")
    elif old_nav in js:
        sq = "'" if quote == '"' else "\\'"
        btn = f'<button class={q}hamburger{q} onclick={q}this.nextElementSibling.classList.toggle({sq}open{sq}){q} aria-label={q}Menu{q}><svg viewBox={q}0 0 24 24{q} fill={q}none{q} stroke-width={q}2{q} stroke-linecap={q}round{q}><line x1={q}3{q} y1={q}6{q} x2={q}21{q} y2={q}6{q}/><line x1={q}3{q} y1={q}12{q} x2={q}21{q} y2={q}12{q}/><line x1={q}3{q} y1={q}18{q} x2={q}21{q} y2={q}18{q}/></svg></button><div class={q}nav-links{q}>'
        js = js.replace(old_nav, btn + old_nav + "</div>", 1)
        print("OK: hamburger button added")
    else:
        print("ERROR: nav pattern NOT FOUND")
        # Show what's actually around the nav for debugging
        if "<nav" in js:
            idx = js.find("<nav")
            chunk = js[idx:idx+500]
            print(f"Actual nav area: {repr(chunk[:200])}")

    with open("worker.js", "w", encoding="utf-8") as f:
        f.write(js)
    print(f"worker.js saved: {len(js)} bytes")

except Exception as e:
    print(f"FATAL: {e}")
    traceback.print_exc()
    sys.exit(1)
