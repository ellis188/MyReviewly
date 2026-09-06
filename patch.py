import urllib.request, os, ssl, sys, re

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

print("Downloading worker...")
url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
print(f"Downloaded {len(raw)} bytes")

js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print(f"Cleaned: {len(js)} bytes")

# 1. REMOVE old hamburger injections
while "<style>.hamburger" in js:
    start = js.find("<style>.hamburger")
    end = js.find("</script>", start)
    if end > 0:
        js = js[:start] + js[end + len("</script>"):]
        print("Removed old hamburger injection")
    else:
        break

# 2. Replace "Google Maps" with "Google Business Profile" everywhere in the dashboard/SPA
replacements = [
    ("Connect your Google Maps page", "Connect your Google Business Profile"),
    ("Google Maps page", "Google Business Profile"),
    ("Google Maps link", "Google Business Profile link"),
    ("your Google Maps", "your Google Business Profile"),
    ("on Google Maps", "on Google"),
    ("google.com/maps", "business.google.com"),
    ("Paste your Google Maps link here", "Search for your business or paste your Google Business Profile link"),
    ("copy the link from the address bar or Share button", "or search for your business name below"),
    ("Search for your business at google.com/maps, open your listing, and copy the link from the address bar or Share button.", "Enter your business name and town below, or paste your Google Business Profile link directly."),
    ("Connect your Google Maps link saved", "Google Business Profile connected"),
    ("Google Maps link saved", "Google Business Profile connected"),
]

for old, new in replacements:
    count = js.count(old)
    if count > 0:
        js = js.replace(old, new)
        print(f"Replaced '{old[:40]}...' ({count}x)")

# 3. Add fresh hamburger with How it works
hamburger_injection = """<style>.hamburger{display:none;background:none;border:none;cursor:pointer;padding:8px;position:absolute;right:16px;top:50%;transform:translateY(-50%)}.hamburger svg{width:28px;height:28px;stroke:#1a1a2e}@media(max-width:768px){.hamburger{display:block}nav{position:relative}nav>a:not(.logo),nav>div.nav-links>a{display:none}nav .nav-links{display:none}nav .nav-links.open{display:flex;position:absolute;top:100%;left:0;right:0;background:rgba(255,255,255,0.98);backdrop-filter:blur(8px);flex-direction:column;padding:16px 24px;border-bottom:1px solid #e2e2ef;box-shadow:0 4px 12px rgba(0,0,0,0.08);gap:12px;z-index:200}nav .nav-links.open a{display:block;margin:0!important;font-size:1rem;padding:8px 0;color:#4f46e5;font-weight:500;text-decoration:none}nav .nav-links.open a.cta-nav{width:100%;text-align:center;padding:12px}}</style><script>document.addEventListener("DOMContentLoaded",function(){var n=document.querySelector("nav");if(n){var links=[];var a=n.querySelectorAll("a:not(.logo)");a.forEach(function(el){links.push(el)});var wrap=document.createElement("div");wrap.className="nav-links";var hiw=document.createElement("a");hiw.href="#how-it-works";hiw.style.cssText="color:#4f46e5;font-weight:500;text-decoration:none;";hiw.textContent="How it works";wrap.appendChild(hiw);links.forEach(function(el){wrap.appendChild(el)});var old=n.querySelector(".hamburger");if(old)old.remove();var oldWrap=n.querySelector(".nav-links");if(oldWrap)oldWrap.remove();n.appendChild(wrap);var btn=document.createElement("button");btn.className="hamburger";btn.setAttribute("aria-label","Menu");btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>';btn.onclick=function(){wrap.classList.toggle("open")};n.insertBefore(btn,wrap);wrap.addEventListener("click",function(e){if(e.target.tagName==="A"){wrap.classList.remove("open")}});var sections=document.querySelectorAll("section");sections.forEach(function(s){if(s.textContent.indexOf("How it works")>-1&&s.textContent.indexOf("Sign up in 60")>-1){s.id="how-it-works"}})}})</script>"""

for bp in ["</body>", "<\\/body>"]:
    if bp in js:
        js = js.replace(bp, hamburger_injection + bp, 1)
        print("Hamburger menu injected")
        break

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Saved: {len(js)} bytes")
