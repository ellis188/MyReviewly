import urllib.request, os, ssl

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print(f"Worker: {len(js)} bytes")

# ROLLBACK: strip every nav/hamburger injection ever added. Touch nothing else.
n = 0
START, END = "<!--MRNAV-START-->", "<!--MRNAV-END-->"
while START in js and END in js:
    s = js.find(START); e = js.find(END, s)
    js = js[:s] + js[e+len(END):]; n += 1
for marker in ["<style>.hamburger", "<style>#mr-hamburger", "<style>#mrh{"]:
    while marker in js:
        s = js.find(marker); e = js.find("</script>", s)
        if e < 0: break
        js = js[:s] + js[e+len("</script>"):]; n += 1
print(f"Removed {n} nav injection(s) - nav restored to original")

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"Saved: {len(js)} bytes")
