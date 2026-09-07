import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# Fix GBP picker quote escaping
js = js.replace('onclick="navigate(' + "'" + '/dashboard' + "'" + ')">Back to dashboard</button>',
                'onclick="navigate(&quot;/dashboard&quot;)">Back to dashboard</button>')

# 1. Change the hero demo button from "Start Free Trial" to "Send Me a Test Email"
old_hero_btn = '>Start Free Trial</button>'
# Only change the one in the hero (the one after sendDemo onclick), not others
old_demo = 'onclick="sendDemo()" class="btn-primary" style="width:100%;cursor:pointer;">Start Free Trial</button>'
new_demo = 'onclick="sendDemo()" class="btn-primary" style="width:100%;cursor:pointer;">Send Me a Test Email</button>'
if old_demo in js:
    js = js.replace(old_demo, new_demo, 1)
    print("OK: hero button changed to Send Me a Test Email")

# 2. Add a "Start Free Trial" signup button below the demo section
# Find the cta-sub span and add a signup button after the cta-group div
old_sub = 'No credit card required'
# Add a signup button after the subtext
old_cta_end = '</span>\n        </div>\n    </div>'
new_cta_end = '</span>\n            <a href="/signup" style="display:inline-block;margin-top:16px;padding:14px 32px;background:#1a1a2e;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:1rem;">Start Free Trial</a>\n        </div>\n    </div>'
if old_cta_end in js:
    js = js.replace(old_cta_end, new_cta_end, 1)
    print("OK: added Start Free Trial signup button to hero")
else:
    print("SKIP: cta end pattern not found, trying alt")
    # Try without exact newlines
    if "No credit card required" in js and "</span>" in js:
        # Find the cta-sub span closing and add after it
        idx = js.find("No credit card required")
        if idx > 0:
            span_end = js.find("</span>", idx)
            if span_end > 0:
                insert_point = span_end + len("</span>")
                signup_btn = '\n            <a href="/signup" style="display:inline-block;margin-top:16px;padding:14px 32px;background:#1a1a2e;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:1rem;">Start Free Trial</a>'
                js = js[:insert_point] + signup_btn + js[insert_point:]
                print("OK: added Start Free Trial button (alt method)")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes" % len(js))
