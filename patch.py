import urllib.request, os, ssl, re

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()

report = []
report.append(f"WORKER SIZE: {len(js)}")

# Leftover injections?
for m in ["<!--MRNAV-START-->", "<style>.hamburger", "<style>#mr-hamburger", "<style>#mrh{"]:
    report.append(f"leftover {m!r}: {js.count(m)}")

# Every <nav ...> ... </nav> block
for i, m in enumerate(re.finditer(r'<nav[^>]*>.*?</nav>', js, re.S)):
    report.append(f"--- NAV BLOCK {i} (len {len(m.group(0))}) ---")
    report.append(m.group(0)[:900])

# Where are the section ids / how it works headings
for i, m in enumerate(re.finditer(r'id=\\?"[^"\\]{0,40}\\?"', js)):
    pass
ids = re.findall(r'id=\\?"([a-z0-9\-]{2,40})\\?"', js)
report.append(f"IDS PRESENT: {sorted(set(ids))[:40]}")

# How it works section headings
for i, m in enumerate(re.finditer(r'How it works', js)):
    s = max(0, m.start()-200)
    report.append(f"--- 'How it works' #{i} context ---")
    report.append(js[s:m.start()+80].replace("\n", " ")[-280:])

out = "\n".join(report)
with open("navreport.txt", "w", encoding="utf-8") as f:
    f.write(out)
print(out[:6000])

# Do not modify the worker this run - diagnostic only
with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
