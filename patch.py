import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# Check if the SPA is already broken
if 'renderSignup' not in js:
    print("CRITICAL: renderSignup missing - SPA is broken")
    print("Deploying as-is to restore from Cloudflare's current state")
else:
    spacheck = js.find('id=\\"app\\"')
    if spacheck < 0:
        spacheck = js.find("id='app'")
    if spacheck < 0:
        spacheck = js.find('id="app"')
    print("SPA app div at position: %d" % spacheck)
    
    # Don't modify the SPA at all - just add GBP routes if missing
    if '/api/auth/google/start' not in js:
        print("GBP routes not present - need to add them")
    else:
        print("GBP routes already present")

# Just write the worker as-is from Cloudflare - no modifications
# This restores the dashboard to working state
with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes (restored from Cloudflare)" % len(js))
