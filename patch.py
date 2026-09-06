import urllib.request, os, ssl, re, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print(f"Worker in: {len(js)} bytes")

ENDTAG = "<" + chr(92) + "/script>"   # <\/script> as it appears inside the template literal

# 1. Strip EVERY leftover hamburger injection. They start at a <style> containing
#    hamburger CSS and end at the next <\/script>.
removed = 0
for marker in ["<style>.hamburger", "<style>#mr-hamburger", "<style>#mrh{", "<!--MRNAV-START-->"]:
    while marker in js:
        s = js.find(marker)
        e = js.find(ENDTAG, s)
        if e < 0:
            print(f"  !! no {ENDTAG} after {marker}, aborting that marker")
            break
        js = js[:s] + js[e + len(ENDTAG):]
        removed += 1
print(f"Removed {removed} stacked injection(s)")

# 2. Desktop spacing on the baked-in nav CSS
if ".nav-links { display: flex; align-items: center; gap: 0; }" in js:
    js = js.replace(".nav-links { display: flex; align-items: center; gap: 0; }",
                    ".nav-links { display: flex; align-items: center; gap: 18px; }")
    print("Nav spacing set to 18px")

# 3. Make sure the mobile menu links are readable (colour + CTA button)
old_open = ".nav-links a { margin-right: 0 !important; font-size: 1rem; padding: 8px 0; }"
new_open = ".nav-links a { margin-right: 0 !important; font-size: 1rem; padding: 8px 0; color: #4f46e5; text-decoration: none; }"
if old_open in js:
    js = js.replace(old_open, new_open)
    print("Mobile link colour fixed")

old_cta = ".nav-links a.cta-nav { width: 100%; text-align: center; padding: 12px; }"
new_cta = ".nav-links a.cta-nav { width: 100%; text-align: center; padding: 12px; background: #2563eb; color: #fff; border-radius: 6px; }"
if old_cta in js:
    js = js.replace(old_cta, new_cta)
    print("Mobile CTA styling fixed")

# 4. Add "How it works" as the first link inside the existing nav div (static, no JS)
anchor = '<div class="nav-links"><a href="#pricing"'
hiw = '<div class="nav-links"><a href="#how-it-works" style="margin-right:12px;color:#4f46e5;font-weight:500;text-decoration:none;">How it works</a><a href="#pricing"'
if 'href="#how-it-works"' in js:
    print("How it works link already present")
elif anchor in js:
    js = js.replace(anchor, hiw, 1)
    print("Added How it works link to nav")
else:
    print("!! nav div anchor not found")

# 5. Give the How it works section a real id so the link scrolls there
sec = '<section style="max-width:900px;margin:0 auto;padding:60px 16px;">\n  <h2 style="text-align:center;font-size:1.8rem;margin-bottom:40px;">How it works</h2>'
sec_new = '<section id="how-it-works" style="max-width:900px;margin:0 auto;padding:60px 16px;">\n  <h2 style="text-align:center;font-size:1.8rem;margin-bottom:40px;">How it works</h2>'
if 'id="how-it-works"' in js:
    print("Section id already present")
elif sec in js:
    js = js.replace(sec, sec_new, 1)
    print("Added id to How it works section")
else:
    m = re.search(r'<section style="max-width:900px;margin:0 auto;padding:60px 16px;">', js)
    if m:
        js = js[:m.start()] + '<section id="how-it-works" style="max-width:900px;margin:0 auto;padding:60px 16px;">' + js[m.end():]
        print("Added id to How it works section (regex)")
    else:
        print("!! How it works section not found")

# 6. Sanity checks before writing
assert js.count('class="hamburger"') == 1, f"hamburger buttons: {js.count(chr(34)+'hamburger'+chr(34))}"
assert js.count('class="nav-links"') == 1, "nav-links div count wrong"
assert js.count('>How it works</a>') == 1, "How it works link count wrong"
print("Sanity checks passed")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Worker out: {len(js)} bytes")
