import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# Find the SPA_HTML string and check its health
spa_start = js.find('const SPA_HTML')
if spa_start < 0:
    print("CRITICAL: SPA_HTML not found at all")
    sys.exit(1)

# Find where the SPA script tag is
print("SPA_HTML starts at: %d" % spa_start)

# Check for broken function injections inside SPA_HTML
# The GBP picker functions I injected may have broken escaping
# Remove them: renderGbpSelect, pickGbp, connectGBP
# Also remove the gbp-select route from the SPA router

# Find and remove the injected GBP picker code
gbp_picker_start = js.find("async function renderGbpSelect")
if gbp_picker_start > 0:
    # Find where connectGBP function ends
    connect_end = js.find("function renderSignup(el) {", gbp_picker_start)
    if connect_end > 0:
        injected = js[gbp_picker_start:connect_end]
        print("Found injected GBP picker code: %d bytes" % len(injected))
        js = js[:gbp_picker_start] + js[connect_end:]
        print("Removed GBP picker from SPA")

# Remove the gbp-select route line from SPA router
gbp_route = "  else if (p === '/gbp-select') renderGbpSelect(el);\n"
if gbp_route in js:
    js = js.replace(gbp_route, "")
    print("Removed /gbp-select route from SPA router")

# Undo town field removal - restore it
# Check if town was already removed
if "var town = '';" in js:
    js = js.replace("var town = '';", "var town = document.getElementById('s-town').value.trim();")
    print("Restored town variable read")

if "if (!name || !email || !pass) {" in js and "s-town" in js:
    js = js.replace("if (!name || !email || !pass) {", "if (!name || !email || !pass || !town) {")
    print("Restored town validation")

# Check the SPA renders by looking for key functions
for fn in ['renderLogin', 'renderSignup', 'renderDashboard']:
    if fn in js:
        print("SPA check OK: %s found" % fn)
    else:
        print("SPA check FAIL: %s MISSING" % fn)

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes" % len(js))
