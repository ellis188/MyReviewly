import urllib.request, os, ssl, sys, re

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

print("Downloading worker...")
url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")

js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print(f"Worker: {len(js)} bytes")

# Remove ALL old hamburger injections
while "<style>.hamburger" in js:
    start = js.find("<style>.hamburger")
    end = js.find("</script>", start)
    if end > 0:
        js = js[:start] + js[end + len("</script>"):]
        print("Removed old injection")
    else:
        break

# GBP wording
for old, new in [
    ("Send Myself a Demo", "Start Free Trial"),
    ("send Myself a Demo", "Start Free Trial"),
    ("No card required", "No credit card required"),
    ("Connect your Google Maps page", "Connect your Google Business Profile"),
    ("Google Maps page", "Google Business Profile"),
    ("Google Maps link", "Google Business Profile link"),
    ("Paste your Google Maps link here", "Search for your business or paste your Google Business Profile link"),
    ("Google Maps link saved", "Google Business Profile connected"),
]:
    if old in js:
        js = js.replace(old, new)

# HAMBURGER - completely rewritten, robust version
# CSS: on desktop, show nav links inline with spacing. On mobile, hide links and show hamburger.
# JS: add How it works link, wrap existing links, add hamburger button
hamburger = (
    '<style>'
    '#mr-hamburger{display:none;background:none;border:none;cursor:pointer;padding:8px}'
    '#mr-hamburger svg{width:28px;height:28px;stroke:#1a1a2e}'
    '#mr-nav-links{display:flex;align-items:center;gap:12px}'
    '#mr-nav-links a{white-space:nowrap}'
    '@media(max-width:768px){'
    '#mr-hamburger{display:block}'
    'nav{position:relative}'
    '#mr-nav-links{display:none;position:absolute;top:100%;left:0;right:0;'
    'background:rgba(255,255,255,0.98);backdrop-filter:blur(8px);'
    'flex-direction:column;padding:16px 24px;border-bottom:1px solid #e2e2ef;'
    'box-shadow:0 4px 12px rgba(0,0,0,0.08);gap:12px;z-index:200}'
    '#mr-nav-links.open{display:flex}'
    '#mr-nav-links a{display:block;margin:0!important;font-size:1rem;padding:8px 0;'
    'color:#4f46e5;font-weight:500;text-decoration:none}'
    '#mr-nav-links a.cta-nav{width:100%;text-align:center;padding:12px;'
    'background:#2563eb;color:#fff!important;border-radius:6px}'
    '}'
    '</style>'
    '<script>'
    'document.addEventListener("DOMContentLoaded",function(){'
    'var nav=document.querySelector("nav");'
    'if(!nav)return;'
    # Create wrapper
    'var wrap=document.createElement("div");'
    'wrap.id="mr-nav-links";'
    # Add How it works as first link
    'var hiw=document.createElement("a");'
    'hiw.href="#how-it-works";'
    'hiw.textContent="How it works";'
    'wrap.appendChild(hiw);'
    # Move existing nav links into wrapper
    'var links=nav.querySelectorAll("a:not(.logo)");'
    'for(var i=0;i<links.length;i++){wrap.appendChild(links[i]);}'
    # Create hamburger button
    'var btn=document.createElement("button");'
    'btn.id="mr-hamburger";'
    'btn.innerHTML='
    "'<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"2\" stroke-linecap=\"round\">"
    '<line x1=\"3\" y1=\"6\" x2=\"21\" y2=\"6\"/>'
    '<line x1=\"3\" y1=\"12\" x2=\"21\" y2=\"12\"/>'
    '<line x1=\"3\" y1=\"18\" x2=\"21\" y2=\"18\"/>'
    "</svg>';"
    'btn.onclick=function(){wrap.classList.toggle("open");};'
    # Add to nav
    'nav.appendChild(btn);'
    'nav.appendChild(wrap);'
    # Close menu on link click
    'wrap.onclick=function(e){if(e.target.tagName==="A")wrap.classList.remove("open");};'
    # Add id to How it works section
    'var secs=document.querySelectorAll("section");'
    'for(var j=0;j<secs.length;j++){'
    'if(secs[j].textContent.indexOf("Sign up in 60")>-1)secs[j].id="how-it-works";'
    '}'
    '});'
    '</script>'
)

for bp in ["</body>", "<\\/body>"]:
    if bp in js:
        js = js.replace(bp, hamburger + bp, 1)
        print("Hamburger injected")
        break

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Saved: {len(js)} bytes")
