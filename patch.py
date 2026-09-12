import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

# Fix GBP picker quote escaping (carry forward)
js = js.replace("navigate('/dashboard')", 'navigate(&quot;/dashboard&quot;)')

# 1. ADD /api/search-business route before /api/auth/google/start
SEARCH_ROUTE = '''    if (path === "/api/search-business" && method === "POST") {
      const u = await getUser(request, env);
      if (!u) return json({ error: "Not logged in." }, 401);
      try {
        const { query } = await request.json();
        if (!query || query.length < 2) return json({ error: "Please enter your business name." }, 400);
        const pr = await fetch("https://places.googleapis.com/v1/places:searchText", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Goog-Api-Key": PLACES_KEY, "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount" },
          body: JSON.stringify({ textQuery: query, languageCode: "en", regionCode: "GB" })
        });
        const pd = await pr.json();
        if (!pd.places || !pd.places.length) return json({ error: "No businesses found. Try adding your town." }, 400);
        var results = [];
        for (const p of pd.places.slice(0, 5)) {
          results.push({
            placeId: p.id,
            name: p.displayName ? p.displayName.text : "",
            address: p.formattedAddress || "",
            rating: p.rating || 0,
            reviewCount: p.userRatingCount || 0,
            reviewLink: "https://search.google.com/local/writereview?placeid=" + p.id
          });
        }
        return json({ ok: true, results: results });
      } catch (e) {
        return json({ error: "Search failed: " + e.message }, 500);
      }
    }
'''

if "/api/search-business" not in js:
    anchor = '    if (path === "/api/auth/google/start")'
    if anchor in js:
        js = js.replace(anchor, SEARCH_ROUTE + anchor)
        print("OK: added /api/search-business route")
    else:
        print("SKIP: auth route anchor not found")
else:
    print("SKIP: search-business route already exists")

# 2. ADD searchBusiness() and selectBusiness() functions to the SPA
# Insert before the renderSignup function
SEARCH_FUNCS = '''
async function searchBusiness() {
  var q = document.getElementById('biz-search').value.trim();
  var msg = document.getElementById('search-msg');
  if (!q || q.length < 2) { msg.innerHTML = '<div class="msg msg-err">Type your business name to search.</div>'; return; }
  msg.innerHTML = '<div class="msg msg-ok">Searching...</div>';
  var res = await api('/api/search-business', {method:'POST', body:{query:q}});
  if (!res.ok) { msg.innerHTML = '<div class="msg msg-err">' + (res.error || 'No results.') + '</div>'; return; }
  var h = '';
  for (var i = 0; i < res.results.length; i++) {
    var r = res.results[i];
    var stars = r.rating ? r.rating.toFixed(1) + ' stars (' + r.reviewCount + ' reviews)' : '';
    h += '<div style="border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px;">';
    h += '<div style="font-weight:600;">' + r.name + '</div>';
    h += '<div style="color:var(--muted);font-size:0.85rem;">' + r.address + '</div>';
    if (stars) h += '<div style="color:#f59e0b;font-size:0.85rem;margin-top:4px;">' + stars + '</div>';
    h += '<button class="btn btn-sm" style="margin-top:8px;" onclick="selectBusiness(' + i + ')">This is my business</button>';
    h += '</div>';
  }
  msg.innerHTML = h;
  window.__bizResults = res.results;
}

async function selectBusiness(i) {
  var biz = window.__bizResults[i];
  var msg = document.getElementById('search-msg');
  msg.innerHTML = '<div class="msg msg-ok">Connecting ' + biz.name + '...</div>';
  var res = await api('/api/settings', {method:'POST', body:{google_maps_url: 'https://www.google.com/maps/place/?q=place_id:' + biz.placeId}});
  if (res.ok) {
    msg.innerHTML = '<div class="msg msg-ok">Connected! Your review link is ready.</div>';
    setTimeout(function(){renderDashboard(document.getElementById('app'));}, 1000);
  } else {
    msg.innerHTML = '<div class="msg msg-err">' + (res.error || 'Failed to connect.') + '</div>';
  }
}

'''

if "async function searchBusiness" not in js:
    anchor2 = "function renderSignup(el) {"
    if anchor2 in js:
        js = js.replace(anchor2, SEARCH_FUNCS + anchor2)
        print("OK: added searchBusiness/selectBusiness functions")
    else:
        print("FAIL: renderSignup anchor not found")
        sys.exit(1)
else:
    print("SKIP: searchBusiness already exists")

# 3. REPLACE dashboard step 1 "not connected" section
# Find the current confusing paste-URL section and replace with search box
OLD_STEP1 = """h += '<p class="step-desc">We couldn\\\\'t auto-detect your business on Google. Search for your business at business.google.com, open your listing, and or search for your business name below.</p>' +
      '<div id="maps-msg"></div><input type="url" id="maps-url" placeholder="Paste your Google Business Profile link here">' +
      '<button class="btn" onclick="connectGBP()">Connect Google Business Profile</button>' + '<p style="text-align:center;margin:14px 0 8px;color:#94a3b8;font-size:0.85rem;">or add your review link manually</p>' + '<button class="btn btn-outline btn-sm" onclick="saveMaps()">Save link</button>';"""

NEW_STEP1 = """h += '<p class="step-desc">Search for your business below and select it from the results. This connects your Google review link automatically.</p>' +
      '<div style="display:flex;gap:8px;margin-bottom:14px;"><input type="text" id="biz-search" placeholder="e.g. Smith Barbershop Bournemouth" style="flex:1;margin-bottom:0;"><button class="btn btn-sm" onclick="searchBusiness()" style="white-space:nowrap;">Search</button></div>' +
      '<div id="search-msg"></div>' +
      '<details style="margin-top:16px;"><summary style="cursor:pointer;font-size:0.85rem;color:var(--accent);">Can\\'t find it? Paste your review link manually</summary>' +
      '<div style="margin-top:12px;"><p class="step-desc">Go to Google Maps, search for your business, copy the URL from the address bar, and paste it below.</p><div id="maps-msg"></div><input type="url" id="maps-url" placeholder="Paste Google Maps URL here">' +
      '<button class="btn btn-outline btn-sm" onclick="saveMaps()">Save Link</button></div></details>';"""

if OLD_STEP1 in js:
    js = js.replace(OLD_STEP1, NEW_STEP1)
    print("OK: replaced step 1 with search box")
else:
    print("WARN: exact step 1 pattern not found, trying flexible match")
    # Try to find the key parts
    if "Paste your Google Business Profile link here" in js:
        # Find from step-desc to the end of the paste section
        start_marker = "We couldn"
        start_idx = js.find(start_marker, js.find("hasMap"))
        if start_idx > 0:
            # Find the line start
            line_start = js.rfind("h += '", start_idx - 100, start_idx)
            if line_start < 0:
                line_start = js.rfind("h += '<", start_idx - 100, start_idx)
            end_marker = "Save link</button>';"
            end_idx = js.find(end_marker, start_idx)
            if line_start > 0 and end_idx > 0:
                old_block = js[line_start:end_idx + len(end_marker)]
                js = js[:line_start] + NEW_STEP1 + js[end_idx + len(end_marker):]
                print("OK: replaced step 1 (flexible match, %d bytes replaced)" % len(old_block))
            else:
                print("FAIL: could not find step 1 boundaries")
        else:
            print("FAIL: could not find step 1 start")
    else:
        print("FAIL: paste placeholder not found at all")

# Verify
for check in ['searchBusiness', 'selectBusiness', '/api/search-business', 'biz-search']:
    if check in js:
        print("CHECK OK: %s" % check)
    else:
        print("CHECK FAIL: %s" % check)

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes" % len(js))
