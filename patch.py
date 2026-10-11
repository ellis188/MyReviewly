import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# FIX 1: broken JS - &quot; inside real JavaScript killed the whole dashboard script
n = js.count("{ navigate(&quot;/dashboard&quot;); }")
js = js.replace("{ navigate(&quot;/dashboard&quot;); }", "{ navigate('/dashboard'); }")
print("Fix 1 navigate: %d" % n)

# FIX 2: unescaped apostrophe in a single-quoted JS string
bad = "Can't find it? Paste your review link manually"
print("Fix 2 apostrophe: %d" % js.count(bad))
js = js.replace(bad, "Can&#39;t find it? Paste your review link manually")

# FIX 3: landing page buttons vanish on hover - --accent-dark was never defined
old = "            --accent: #2563eb;\n"
if "--accent-dark: #1d4ed8" not in js and old in js:
    js = js.replace(old, old + "            --accent-dark: #1d4ed8;\n", 1)
    print("Fix 3 accent-dark: added")
else:
    print("Fix 3 accent-dark: skipped")

if "&quot;/dashboard&quot;); }" in js:
    print("FAIL: broken navigate still present"); sys.exit(1)

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
if os.path.exists("debug.txt"):
    os.remove("debug.txt")
print("Worker out: %d bytes" % len(js))
