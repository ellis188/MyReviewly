import urllib.request, json, os, ssl, sys, traceback, base64

try:
    ctx = ssl.create_default_context()
    CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
    CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")

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

    # Save debug info
    debug = f"Total JS length: {len(js)}\n\n"
    debug += f"First 200 chars:\n{repr(js[:200])}\n\n"

    nav_idx = js.find("Pricing")
    if nav_idx >= 0:
        debug += f"Around 'Pricing' (idx {nav_idx}):\n{repr(js[max(0,nav_idx-100):nav_idx+200])}\n\n"

    hero_idx = js.find("HERO")
    if hero_idx >= 0:
        debug += f"Around 'HERO' (idx {hero_idx}):\n{repr(js[max(0,hero_idx-50):hero_idx+50])}\n\n"

    debug += f"Contains backslash-quote: {'yes' if chr(92)+chr(34) in js else 'no'}\n"
    debug += f"Contains backslash-n: {'yes' if chr(92)+chr(110) in js else 'no'}\n"
    debug += f"Contains literal newline in first 500: {'yes' if chr(10) in js[:500] else 'no'}\n"

    with open("debug.txt", "w") as f:
        f.write(debug)
    print(debug)

    # Now do the actual modifications
    has_bs = chr(92) + chr(34) in js  # backslash-quote present?
    q = chr(92) + chr(34) if has_bs else chr(34)  # \" or "
    nl = chr(92) + "n" if chr(92) + "n" in js[:500] else "\n"

    # CSS
    if ".hamburger" not in js and "HERO" in js:
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

        hero_marker = "/* HERO */"
        if hero_marker in js:
            js = js.replace(hero_marker, css + "        " + hero_marker, 1)
            print("OK: CSS added")
        else:
            print("HERO marker not found")

    # Nav button
    old_nav = f'<a href={q}#pricing{q} style={q}margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;{q}>Pricing</a><a href={q}/login{q} style={q}margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;{q}>Log In</a><a href={q}/signup{q} class={q}cta-nav{q}>Start Free Trial</a>'

    if old_nav in js:
        sq = "'" if not has_bs else chr(92) + "'"
        btn = f'<button class={q}hamburger{q} onclick={q}this.nextElementSibling.classList.toggle({sq}open{sq}){q} aria-label={q}Menu{q}><svg viewBox={q}0 0 24 24{q} fill={q}none{q} stroke-width={q}2{q} stroke-linecap={q}round{q}><line x1={q}3{q} y1={q}6{q} x2={q}21{q} y2={q}6{q}/><line x1={q}3{q} y1={q}12{q} x2={q}21{q} y2={q}12{q}/><line x1={q}3{q} y1={q}18{q} x2={q}21{q} y2={q}18{q}/></svg></button><div class={q}nav-links{q}>'
        js = js.replace(old_nav, btn + old_nav + "</div>", 1)
        print("OK: nav button added")
    else:
        print(f"NAV PATTERN NOT FOUND. Pattern length: {len(old_nav)}")

    with open("worker.js", "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Saved worker.js: {len(js)} bytes")

except Exception as e:
    print(f"FATAL: {e}")
    traceback.print_exc()
    sys.exit(1)
