import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# Fix the unescaped quotes in renderGbpSelect that break the SPA
# navigate('/dashboard') needs to be navigate(\'/dashboard\')
fixes = 0

# Fix onclick="navigate('/dashboard')" inside single-quoted JS strings
js = js.replace("""onclick="navigate('/dashboard')">Back to dashboard</button>""",
                """onclick="navigate(&quot;/dashboard&quot;)">Back to dashboard</button>""")
fixes += 1

# Also fix navigate('/login') if present in single-quoted strings  
js = js.replace("""onclick="navigate('/login')">""",
                """onclick="navigate(&quot;/login&quot;)">""")

# Also fix navigate('/signup') if present
js = js.replace("""onclick="navigate('/signup')">""",
                """onclick="navigate(&quot;/signup&quot;)">""")

print("Applied %d quote fixes" % fixes)

# Verify SPA has key functions
for fn in ['renderLogin', 'renderSignup', 'renderDashboard', 'renderGbpSelect']:
    if fn in js:
        print("OK: %s present" % fn)
    else:
        print("MISSING: %s" % fn)

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes" % len(js))
