import urllib.request, os, ssl, sys

ctx = ssl.create_default_context()
CF_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
CF_ACCOUNT = os.environ["CLOUDFLARE_ACCOUNT_ID"]

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/myreviewly-site"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {CF_TOKEN}", "Accept": "application/javascript"})
raw = urllib.request.urlopen(req, context=ctx).read().decode("utf-8")
js = "\n".join(l for l in raw.split("\n") if not (l.strip().startswith("--") and len(l.strip()) > 20) and not l.strip().startswith("Content-Disposition:") and not l.strip().startswith("Content-Type:")).strip()
print("Worker in: %d bytes" % len(js))

def rep(old, new, label, required=True):
    global js
    if new.split("<<<")[0] and old not in js:
        if required:
            print("FAIL: anchor not found -> " + label); sys.exit(1)
        print("skip: " + label); return
    js = js.replace(old, new, 1)
    print("ok: " + label)

# ---------- 1. REMOVE TOWN FROM SIGNUP ----------
rep("'<label>Town / City</label><input type=\"text\" id=\"s-town\" placeholder=\"e.g. Bournemouth\">' +\n    ",
    "", "signup: removed Town/City field")

rep("var town = document.getElementById('s-town').value.trim();",
    "var town = '';", "signup: removed town variable read")

rep("if (!name || !email || !pass || !town) {",
    "if (!name || !email || !pass) {", "signup: town no longer required")

# ---------- 2. GBP OAUTH ROUTES IN THE WORKER ----------
GBP_ROUTES = '''    var GBP_ID = env.GOOGLE_CLIENT_ID || "";
    var GBP_SECRET = env.GOOGLE_CLIENT_SECRET || "";
    var GBP_REDIRECT = "https://myreviewly.co.uk/api/auth/google/callback";
    var GBP_SCOPE = "https://www.googleapis.com/auth/business.manage";
    async function gbpAccessToken(env2, userId) {
      var row = await env2.DB.prepare("SELECT refresh_token FROM gbp_connections WHERE user_id=?").bind(userId).first();
      if (!row || !row.refresh_token) return null;
      var r = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: "client_id=" + encodeURIComponent(GBP_ID) + "&client_secret=" + encodeURIComponent(GBP_SECRET) + "&refresh_token=" + encodeURIComponent(row.refresh_token) + "&grant_type=refresh_token" });
      var d = await r.json();
      return d.access_token || null;
    }
    if (path === "/api/auth/google/start") {
      const gu = await getUser(request, env);
      if (!gu) return Response.redirect("https://myreviewly.co.uk/login", 302);
      if (!GBP_ID || !GBP_SECRET) return new Response("Google Business Profile connection is not configured yet. The GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET secrets need to be added in Cloudflare.", { status: 503, headers: { "Content-Type": "text/plain" } });
      var authUrl = "https://accounts.google.com/o/oauth2/v2/auth?client_id=" + encodeURIComponent(GBP_ID) + "&redirect_uri=" + encodeURIComponent(GBP_REDIRECT) + "&response_type=code&access_type=offline&prompt=consent&include_granted_scopes=true&scope=" + encodeURIComponent(GBP_SCOPE);
      return Response.redirect(authUrl, 302);
    }
    if (path === "/api/auth/google/callback") {
      const gu = await getUser(request, env);
      if (!gu) return Response.redirect("https://myreviewly.co.uk/login", 302);
      var code = url.searchParams.get("code");
      if (!code) return Response.redirect("https://myreviewly.co.uk/dashboard?gbp=denied", 302);
      try {
        await env.DB.prepare("CREATE TABLE IF NOT EXISTS gbp_connections (user_id INTEGER PRIMARY KEY, refresh_token TEXT, location_name TEXT, review_uri TEXT, connected_at TEXT DEFAULT (datetime('now')))").run();
        var tr = await fetch("https://oauth2.googleapis.com/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: "code=" + encodeURIComponent(code) + "&client_id=" + encodeURIComponent(GBP_ID) + "&client_secret=" + encodeURIComponent(GBP_SECRET) + "&redirect_uri=" + encodeURIComponent(GBP_REDIRECT) + "&grant_type=authorization_code" });
        var td = await tr.json();
        if (!td.refresh_token) return Response.redirect("https://myreviewly.co.uk/dashboard?gbp=tokenfail", 302);
        await env.DB.prepare("INSERT INTO gbp_connections (user_id,refresh_token) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET refresh_token=excluded.refresh_token").bind(gu.id, td.refresh_token).run();
        return Response.redirect("https://myreviewly.co.uk/gbp-select", 302);
      } catch (e) {
        return Response.redirect("https://myreviewly.co.uk/dashboard?gbp=error", 302);
      }
    }
    if (path === "/api/gbp/locations") {
      const gu = await getUser(request, env);
      if (!gu) return json({ error: "Not logged in." }, 401);
      var at = await gbpAccessToken(env, gu.id);
      if (!at) return json({ error: "Not connected to Google. Please connect again." }, 400);
      var ar = await fetch("https://mybusinessaccountmanagement.googleapis.com/v1/accounts", { headers: { Authorization: "Bearer " + at } });
      var ad = await ar.json();
      if (ad.error) return json({ error: "Google said: " + (ad.error.message || "access denied") + " (if this mentions quota, the Business Profile API access request has not been approved yet)" }, 400);
      if (!ad.accounts || !ad.accounts.length) return json({ error: "No Google Business Profile accounts found on that Google account." }, 400);
      var out = [];
      for (const acc of ad.accounts) {
        var lr = await fetch("https://mybusinessbusinessinformation.googleapis.com/v1/" + acc.name + "/locations?readMask=name,title,storefrontAddress,metadata", { headers: { Authorization: "Bearer " + at } });
        var ld = await lr.json();
        for (const loc of ld.locations || []) {
          var addr = "";
          if (loc.storefrontAddress && loc.storefrontAddress.addressLines) addr = loc.storefrontAddress.addressLines.join(", ");
          out.push({ name: loc.name, title: loc.title || "", address: addr, reviewUri: loc.metadata && loc.metadata.newReviewUri ? loc.metadata.newReviewUri : "" });
        }
      }
      if (!out.length) return json({ error: "That Google account has no verified business locations." }, 400);
      return json({ ok: true, locations: out });
    }
    if (path === "/api/gbp/select" && method === "POST") {
      const gu = await getUser(request, env);
      if (!gu) return json({ error: "Not logged in." }, 401);
      try {
        const sel = await request.json();
        await env.DB.prepare("UPDATE gbp_connections SET location_name=?,review_uri=? WHERE user_id=?").bind(sel.location_name || "", sel.review_uri || "", gu.id).run();
        if (sel.review_uri) await env.DB.prepare("UPDATE users SET review_link=? WHERE id=?").bind(sel.review_uri, gu.id).run();
        return json({ ok: true });
      } catch (e) {
        return json({ error: "Failed: " + e.message }, 500);
      }
    }
    if (path === "/api/gbp/disconnect" && method === "POST") {
      const gu = await getUser(request, env);
      if (!gu) return json({ error: "Not logged in." }, 401);
      try { await env.DB.prepare("DELETE FROM gbp_connections WHERE user_id=?").bind(gu.id).run(); } catch (e) {}
      return json({ ok: true });
    }
'''
rep('    if (path === "/pricing") {', GBP_ROUTES + '    if (path === "/pricing") {', "worker: added GBP OAuth routes")

# ---------- 3. SPA: ROUTE + PICKER SCREEN ----------
rep("  else if (p === '/reset-password') renderResetPassword(el);",
    "  else if (p === '/reset-password') renderResetPassword(el);\n  else if (p === '/gbp-select') renderGbpSelect(el);",
    "spa: added /gbp-select route")

PICKER = '''async function renderGbpSelect(el) {
  el.innerHTML = '<nav><div class="logo">My<span>Reviewly</span></div></nav><div class="wrap"><div class="card"><p>Loading your Google business locations...</p></div></div>';
  var res = await api('/api/gbp/locations');
  if (!res.ok) {
    el.innerHTML = '<nav><div class="logo">My<span>Reviewly</span></div></nav><div class="wrap"><div class="card">' +
      '<h2 style="margin-bottom:12px;">Could not load your locations</h2>' +
      '<div class="msg msg-err">' + (res.error || 'Unknown error') + '</div>' +
      '<button class="btn" onclick="navigate(\\'/dashboard\\')">Back to dashboard</button></div></div>';
    return;
  }
  var h = '<nav><div class="logo">My<span>Reviewly</span></div></nav><div class="wrap"><div class="card">' +
    '<h2 style="margin-bottom:4px;">Choose your business</h2>' +
    '<p style="color:var(--muted);margin-bottom:20px;font-size:0.9rem;">These are the locations on your Google Business Profile. Pick the one you want reviews for.</p>' +
    '<div id="g-msg"></div>';
  for (var i = 0; i < res.locations.length; i++) {
    var L = res.locations[i];
    h += '<div style="border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px;">' +
      '<div style="font-weight:600;">' + L.title + '</div>' +
      '<div style="color:var(--muted);font-size:0.85rem;margin-bottom:10px;">' + (L.address || '') + '</div>' +
      '<button class="btn btn-sm" onclick="pickGbp(' + i + ')">Use this business</button></div>';
  }
  h += '</div></div>';
  el.innerHTML = h;
  window.__gbpLocs = res.locations;
}

async function pickGbp(i) {
  var L = window.__gbpLocs[i];
  var msg = document.getElementById('g-msg');
  msg.innerHTML = '<div class="msg msg-ok">Connecting...</div>';
  var res = await api('/api/gbp/select', {method:'POST', body:{location_name:L.name, review_uri:L.reviewUri, title:L.title}});
  if (res.ok) { navigate('/dashboard'); }
  else { msg.innerHTML = '<div class="msg msg-err">' + (res.error || 'Failed.') + '</div>'; }
}

function connectGBP() { window.location.href = '/api/auth/google/start'; }

'''
rep("function renderSignup(el) {", PICKER + "function renderSignup(el) {", "spa: added GBP picker screen")

# ---------- 4. DASHBOARD STEP 1: CONNECT BUTTON ----------
rep("'<button class=\"btn\" onclick=\"saveMaps()\">Save &amp; Continue</button>'",
    "'<button class=\"btn\" onclick=\"connectGBP()\">Connect Google Business Profile</button>'"
    " + '<p style=\"text-align:center;margin:14px 0 8px;color:#94a3b8;font-size:0.85rem;\">or add your review link manually</p>'"
    " + '<button class=\"btn btn-outline btn-sm\" onclick=\"saveMaps()\">Save link</button>'",
    "dashboard: added Connect Google Business Profile button")

rep("We couldn\\'t auto-detect your business on Google. Search for your business at business.google.com, open your listing, and or search for your business name below.",
    "Connect your Google Business Profile so we can pull your official review link straight from Google.",
    "dashboard: rewrote step 1 copy", required=False)

# ---------- SANITY ----------
checks = [
    ('s-town', 0, "town field still present"),
    ('/api/auth/google/start', 3, "oauth start route"),
    ('mybusinessaccountmanagement.googleapis.com', 1, "accounts endpoint"),
    ('mybusinessbusinessinformation.googleapis.com', 1, "locations endpoint"),
    ('newReviewUri', 1, "review uri field"),
    ('renderGbpSelect', 2, "picker function"),
    ('connectGBP', 2, "connect button"),
]
for needle, expected, label in checks:
    got = js.count(needle)
    if expected == 0 and got != 0:
        print("FAIL check (%s): expected 0, got %d" % (label, got)); sys.exit(1)
    if expected > 0 and got < 1:
        print("FAIL check (%s): missing" % label); sys.exit(1)
    print("check ok: %s (%d)" % (label, got))

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Worker out: %d bytes" % len(js))
