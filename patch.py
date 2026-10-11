import urllib.request, os, ssl, re

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# DIAGNOSTIC ONLY - live code is redeployed unchanged.
red = js
red = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "[REDACTED_GOOGLE_KEY]", red)
red = re.sub(r"\bre_[0-9A-Za-z_]{15,}", "[REDACTED_RESEND_KEY]", red)
red = re.sub(r"\b(sk|pk|rk)_(live|test)_[0-9A-Za-z]{10,}", "[REDACTED_STRIPE_KEY]", red)
red = re.sub(r"whsec_[0-9A-Za-z]{10,}", "[REDACTED_WEBHOOK_SECRET]", red)
red = re.sub(r"GOCSPX-[0-9A-Za-z_\-]{10,}", "[REDACTED_OAUTH_SECRET]", red)
with open("debug.txt", "w", encoding="utf-8") as f:
    f.write(red)
print("debug.txt written")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes (unchanged)" % len(js))
