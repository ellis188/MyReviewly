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

# ---- Unsubscribed customers fix ----
def rep(old, new, label):
    global js
    if new in js:
        print("SKIP (done):", label); return
    n = js.count(old)
    if n != 1:
        print("FAIL:", label, n); sys.exit(1)
    js = js.replace(old, new); print("OK:", label)

# A. stats: don't count unsubscribed customers as pending
rep('const pc = await env.DB.prepare("SELECT COUNT(*) as c FROM customers WHERE user_id=? AND id NOT IN (SELECT customer_id FROM review_requests WHERE user_id=?)")',
    'const pc = await env.DB.prepare("SELECT COUNT(*) as c FROM customers WHERE user_id=? AND id NOT IN (SELECT customer_id FROM review_requests WHERE user_id=?) AND LOWER(email) NOT IN (SELECT email FROM unsubscribes)")',
    "stats pending excludes unsubscribed")

# B. customers list: flag unsubscribed
rep('as archived FROM customers c WHERE c.user_id=? ORDER BY c.added_at DESC',
    'as archived,(SELECT COUNT(*) FROM unsubscribes un WHERE un.email=LOWER(c.email)) as unsub FROM customers c WHERE c.user_id=? ORDER BY c.added_at DESC',
    "customers unsub flag")

# C. delete route
DEL = '''    if (path === "/api/customers/delete" && method === "POST") {
      const u = await getUser(request, env);
      if (!u)
        return json({ error: "Not logged in." }, 401);
      try {
        const { id } = await request.json();
        await env.DB.prepare("DELETE FROM customers WHERE id=? AND user_id=? AND id NOT IN (SELECT customer_id FROM review_requests WHERE user_id=?)").bind(id, u.id, u.id).run();
        return json({ ok: true });
      } catch (e) {
        return json({ error: "Failed: " + e.message }, 500);
      }
    }
'''
anchor = '    if (path === "/api/send-reviews" && method === "POST") {'
if '/api/customers/delete' not in js:
    assert js.count(anchor) == 1
    js = js.replace(anchor, DEL + anchor); print("OK: delete route")

# D. dashboard: split out unsubscribed, add remove buttons
rep("var pendingCust = customers.filter(function(c) { return !c.sent; });",
    "var pendingCust = customers.filter(function(c) { return !c.sent && !c.unsub; });\n      var unsubCust = customers.filter(function(c) { return !c.sent && c.unsub; });",
    "pending filter")
rep('''pendingCust.forEach(function(c) { h += '<div class="customer-item"><span>'+c.email+'</span><span class="badge badge-pending">Pending</span></div>'; });''',
    '''pendingCust.forEach(function(c) { h += '<div class="customer-item"><span>'+c.email+'</span><span><span class="badge badge-pending">Pending</span> <button data-id="'+c.id+'" onclick="removeCustomer(this.dataset.id)" style="background:none;border:none;color:#94a3b8;font-size:1.1rem;cursor:pointer;padding:0 4px;" aria-label="Remove">&times;</button></span></div>'; });''',
    "pending remove button")
rep('''      if (sentCust.length > 0) {
        h += '<details''',
    '''      if (unsubCust.length > 0) {
        h += '<div style="margin-top:16px;"><p style="font-weight:600;font-size:0.85rem;color:var(--muted);margin-bottom:8px;">UNSUBSCRIBED (' + unsubCust.length + ') - won&#39;t be emailed</p>';
        unsubCust.forEach(function(c) { h += '<div class="customer-item"><span style="color:var(--muted);">'+c.email+'</span><span><span class="badge" style="background:#fee2e2;color:#991b1b;">Unsubscribed</span> <button data-id="'+c.id+'" onclick="removeCustomer(this.dataset.id)" style="background:none;border:none;color:#94a3b8;font-size:1.1rem;cursor:pointer;padding:0 4px;" aria-label="Remove">&times;</button></span></div>'; });
        h += '</div>';
      }
      if (sentCust.length > 0) {
        h += '<details''',
    "unsubscribed section")

# E. removeCustomer function
FN = '''
async function removeCustomer(id) {
  var res = await api('/api/customers/delete', {method:'POST', body:{id:id}});
  if (res.ok) { renderDashboard(document.getElementById('app')); }
}

'''
a2 = "async function saveMaps() {"
if "async function removeCustomer" not in js:
    assert js.count(a2) == 1
    js = js.replace(a2, FN + a2); print("OK: removeCustomer fn")


# F. business search: show Google's real error instead of hiding it as "No businesses found"
rep('''        const pd = await pr.json();
        if (!pd.places || !pd.places.length)
          return json({ error: "No businesses found. Try adding your town." }, 400);''',
    '''        const pd = await pr.json();
        if (pd.error)
          return json({ error: "Google search error (" + (pd.error.status || pd.error.code || "unknown") + "): " + (pd.error.message || "no message") }, 400);
        if (!pd.places || !pd.places.length)
          return json({ error: "No businesses found. Try adding your town." }, 400);''',
    "search shows google error")


# G. manual link: accept a pasted Google review link directly when Places lookup fails
rep('''        await env.DB.prepare("UPDATE users SET google_maps_url=?,review_link=? WHERE id=?").bind(google_maps_url, rl, u.id).run();''',
    '''        if (!rl && google_maps_url && /writereview|g\\.page\\/r\\/|\\/review/i.test(google_maps_url))
          rl = google_maps_url;
        await env.DB.prepare("UPDATE users SET google_maps_url=?,review_link=? WHERE id=?").bind(google_maps_url, rl, u.id).run();''',
    "manual review link accepted")


if "&quot;/dashboard&quot;); }" in js:
    print("FAIL: broken navigate still present"); sys.exit(1)

with open("worker.js", "w", encoding="utf-8") as f:
    f.write(js)
if os.path.exists("debug.txt"):
    os.remove("debug.txt")
print("Worker out: %d bytes" % len(js))
