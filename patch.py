import urllib.request, os, ssl, sys, re

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print(f"Worker: {len(js)} bytes")

START = "<!--MRNAV-START-->"
END = "<!--MRNAV-END-->"

# 1. Remove ALL previous injections (marker-based AND legacy style-based)
n = 0
while START in js and END in js:
    s = js.find(START); e = js.find(END, s)
    js = js[:s] + js[e+len(END):]
    n += 1
while "<style>.hamburger" in js:
    s = js.find("<style>.hamburger"); e = js.find("</script>", s)
    if e < 0: break
    js = js[:s] + js[e+len("</script>"):]
    n += 1
while "<style>#mr-hamburger" in js:
    s = js.find("<style>#mr-hamburger"); e = js.find("</script>", s)
    if e < 0: break
    js = js[:s] + js[e+len("</script>"):]
    n += 1
print(f"Removed {n} old injection(s)")

# 2. Wording
for old, new in [
    ("Send Myself a Demo", "Start Free Trial"),
    ("No card required", "No credit card required"),
    ("Connect your Google Maps page", "Connect your Google Business Profile"),
    ("Google Maps page", "Google Business Profile"),
    ("Google Maps link", "Google Business Profile link"),
    ("Google Maps link saved", "Google Business Profile connected"),
]:
    if old in js:
        js = js.replace(old, new)

# 3. Fresh injection: nav spacing + hamburger, remove town field, split subline
inj = START + (
 '<style>'
 '#mrh{display:none;background:none;border:none;cursor:pointer;padding:8px}'
 '#mrh svg{width:28px;height:28px;stroke:#1a1a2e}'
 '#mrn{display:flex;align-items:center;gap:18px}'
 '#mrn a{white-space:nowrap;margin-right:0!important}'
 '@media(max-width:768px){'
 '#mrh{display:block}nav{position:relative}'
 '#mrn{display:none;position:absolute;top:100%;left:0;right:0;background:#fff;'
 'flex-direction:column;padding:16px 24px;border-bottom:1px solid #e2e2ef;'
 'box-shadow:0 4px 12px rgba(0,0,0,.08);gap:14px;z-index:200;align-items:stretch}'
 '#mrn.open{display:flex}'
 '#mrn a{display:block;font-size:1rem;padding:6px 0;color:#4f46e5;font-weight:500;text-decoration:none}'
 '#mrn a.cta-nav{text-align:center;padding:12px;background:#2563eb;color:#fff!important;border-radius:6px}'
 '}'
 '</style>'
 '<script>(function(){function go(){'
 'var nav=document.querySelector("nav");if(!nav)return;'
 'if(document.getElementById("mrn"))return;'
 'var wrap=document.createElement("div");wrap.id="mrn";'
 'var hiw=document.createElement("a");hiw.href="#how-it-works";hiw.textContent="How it works";'
 'wrap.appendChild(hiw);'
 'var ls=nav.querySelectorAll("a:not(.logo)");'
 'for(var i=0;i<ls.length;i++){if(ls[i].textContent.trim()!=="How it works")wrap.appendChild(ls[i]);}'
 'var b=document.createElement("button");b.id="mrh";b.setAttribute("aria-label","Menu");'
 'b.innerHTML=\'<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round">'
 '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/>'
 '<line x1="3" y1="18" x2="21" y2="18"/></svg>\';'
 'b.onclick=function(){wrap.classList.toggle("open");};'
 'nav.appendChild(b);nav.appendChild(wrap);'
 'wrap.onclick=function(e){if(e.target.tagName==="A")wrap.classList.remove("open");};'
 'var ss=document.querySelectorAll("section");'
 'for(var j=0;j<ss.length;j++){if(ss[j].textContent.indexOf("Sign up in 60")>-1)ss[j].id="how-it-works";}'
 # subline onto its own line
 'var sp=document.querySelectorAll("span,p");'
 'for(var k=0;k<sp.length;k++){var t=sp[k].textContent;'
 'if(t.indexOf("No credit card required")>-1&&t.indexOf("First 25")>-1){'
 'sp[k].innerHTML="First 25 customers free<br>No credit card required";}}'
 # remove town/city field on signup
 'var ins=document.querySelectorAll("input");'
 'for(var m=0;m<ins.length;m++){var ph=(ins[m].placeholder||"").toLowerCase();'
 'if(ph.indexOf("town")>-1||ph.indexOf("city")>-1){'
 'var w=ins[m].closest("div")||ins[m].parentNode;'
 'var lb=w.querySelector?w.querySelector("label"):null;if(lb)lb.style.display="none";'
 'ins[m].style.display="none";ins[m].value="";}}'
 '}'
 'if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",go);}else{go();}'
 '})();</script>'
) + END

for bp in ["</body>", "<\\/body>"]:
    if bp in js:
        js = js.replace(bp, inj + bp, 1)
        print("Injected fresh nav")
        break

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Saved: {len(js)} bytes")
