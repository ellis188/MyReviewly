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

# Instead of modifying the nav HTML, inject a script that adds the hamburger dynamically
# This avoids all escaping issues - we just find </body> and insert before it

hamburger_injection = """<style>.hamburger{display:none;background:none;border:none;cursor:pointer;padding:8px;position:absolute;right:16px;top:50%;transform:translateY(-50%)}.hamburger svg{width:28px;height:28px;stroke:#1a1a2e}@media(max-width:768px){.hamburger{display:block}nav{position:relative}nav>a:not(.logo),nav>div.nav-links>a{display:none}nav .nav-links{display:none}nav .nav-links.open{display:flex;position:absolute;top:100%;left:0;right:0;background:rgba(255,255,255,0.98);backdrop-filter:blur(8px);flex-direction:column;padding:16px 24px;border-bottom:1px solid #e2e2ef;box-shadow:0 4px 12px rgba(0,0,0,0.08);gap:12px;z-index:200}nav .nav-links.open a{display:block;margin:0!important;font-size:1rem;padding:8px 0}nav .nav-links.open a.cta-nav{width:100%;text-align:center;padding:12px}}</style><script>document.addEventListener("DOMContentLoaded",function(){var n=document.querySelector("nav");if(n&&!n.querySelector(".hamburger")){var links=[];var a=n.querySelectorAll("a:not(.logo)");a.forEach(function(el){links.push(el)});var wrap=document.createElement("div");wrap.className="nav-links";links.forEach(function(el){wrap.appendChild(el)});n.appendChild(wrap);var btn=document.createElement("button");btn.className="hamburger";btn.setAttribute("aria-label","Menu");btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>';btn.onclick=function(){wrap.classList.toggle("open")};n.insertBefore(btn,wrap)}})</script>"""

# Find </body> in the LANDING_HTML and insert before it
# The </body> could be escaped as </body> or as <\\/body> depending on context
body_patterns = ["</body>", "<\\\\/body>"]
inserted = False

for bp in body_patterns:
    if bp in js:
        js = js.replace(bp, hamburger_injection + bp, 1)
        print(f"OK: hamburger injected before {bp}")
        inserted = True
        break

if not inserted:
    # Try finding it with regex
    m = re.search(r'<\\?/?body>', js)
    if m:
        js = js[:m.start()] + hamburger_injection + js[m.start():]
        print(f"OK: hamburger injected via regex at {m.start()}")
        inserted = True
    else:
        print("ERROR: could not find </body> tag anywhere")
        # Last resort: show what tags exist
        tags = re.findall(r'</?\w+>', js[-500:])
        print(f"Last 500 chars tags: {tags}")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Saved: {len(js)} bytes, injection: {'YES' if inserted else 'NO'}")
