"""Page templates, kept in one module so the app is a single small package with no data files."""

BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}ScopeGuard{% endblock %}</title>
<style>
:root{--bg:#f4f1ea;--card:#fff;--ink:#1f2a2e;--muted:#5b676c;--line:#d9d4c7;--accent:#0f5c52;--warn:#9a3b1d;--ok:#2d6a3e;--amber:#8a6612;--mark:#ffe58a;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,"Cascadia Code",Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 var(--sans)}
a{color:var(--accent)}header{background:#fff;border-bottom:1px solid var(--line);padding:.8rem clamp(1rem,4vw,2.5rem);display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap}
header .brand{font-weight:700;font-size:1.15rem;text-decoration:none;color:var(--ink);margin-right:auto}header nav a{margin-left:1rem;text-decoration:none;font-weight:500}
main{max-width:62rem;margin:0 auto;padding:1.5rem clamp(1rem,4vw,2.5rem) 4rem}h1{font-size:1.9rem;line-height:1.2;margin:.3rem 0 .5rem}h2{font-size:1.2rem;margin:0 0 .5rem}
.lede{color:var(--muted);max-width:42rem;margin:0 0 1.5rem}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:1.1rem 1.3rem;margin:0 0 1.1rem}
label{display:block;font-weight:600;font-size:.85rem;color:var(--muted);margin:.8rem 0 .25rem}input,textarea{width:100%;font:inherit;padding:.55rem .7rem;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink)}
textarea{min-height:9rem;font-size:.95rem}.row{display:flex;gap:.8rem;flex-wrap:wrap}.row>div{flex:1 1 9rem}
.btn{font:600 .95rem var(--sans);border:0;border-radius:6px;padding:.6rem 1.1rem;background:var(--accent);color:#fff;cursor:pointer;text-decoration:none;display:inline-block}
.btn.quiet{background:transparent;color:var(--accent);box-shadow:inset 0 0 0 1.5px var(--accent)}.btn.small{padding:.4rem .8rem;font-size:.88rem}
.error{background:#fbeae4;border-left:4px solid var(--warn);padding:.6rem .9rem;margin:0 0 1rem;border-radius:4px}.hint{color:var(--muted);font-size:.9rem}
.pill{display:inline-block;font:700 .75rem var(--sans);padding:.15rem .55rem;border-radius:1rem;color:#fff;vertical-align:middle}
.p-covered{background:var(--ok)}.p-excluded{background:var(--warn)}.p-not_mentioned{background:var(--amber)}.p-unverified{background:#5b676c}
.stats{display:flex;gap:1.5rem;flex-wrap:wrap;margin:0 0 1.2rem}.stat b{display:block;font-size:1.5rem}.stat span{color:var(--muted);font-size:.85rem}
blockquote{margin:.5rem 0;padding:.4rem .9rem;border-left:4px solid var(--mark);background:#fffbe9;font-family:var(--mono);font-size:.88rem}
pre.contract{white-space:pre-wrap;font:.88rem/1.55 var(--mono);margin:0}mark{background:var(--mark);padding:0 .1rem}
pre.reply{white-space:pre-wrap;font:.92rem/1.55 var(--mono);background:#f7f9f8;padding:.9rem;border-radius:6px;margin:0}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:.45rem .5rem;border-bottom:1px solid var(--line);font-size:.92rem}
.done{color:var(--ok);font-weight:600}.waive{color:var(--amber);font-weight:600}.actions{display:flex;gap:.5rem;flex-wrap:wrap;align-items:flex-end;margin-top:.6rem}
.actions input{width:6rem}details summary{cursor:pointer;font-weight:600}footer{color:var(--muted);font-size:.85rem;padding:1rem clamp(1rem,4vw,2.5rem);max-width:62rem;margin:0 auto}
</style></head><body>
<header><a class="brand" href="/">ScopeGuard</a><nav><a href="/">Clients</a><a href="/ledger">Ledger</a></nav></header>
<main>{% block content %}{% endblock %}</main>
<footer>Everything stays on this computer: your contracts, your clients' messages and the answers. Read by {{ model_label }}, running locally.</footer>
<script>document.addEventListener('submit',function(e){var b=e.target.querySelector('[data-wait]');if(b){b.disabled=true;b.textContent=b.dataset.wait;}});</script>
</body></html>"""

INDEX = """{% extends "base.html" %}{% block content %}
<h1>Stop doing free work by accident</h1>
<p class="lede">Paste a client's message. ScopeGuard checks it against your signed agreement, shows what is not covered and what it is worth, and drafts the change order. It runs on an open model on this computer, so contracts under NDA never leave it.</p>
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
{% if t.quoted or t.waived %}<div class="stats"><div class="stat"><b>{{ money(t.quoted_amount) }}</b><span>quoted for out-of-scope work</span></div>
<div class="stat"><b>{{ money(t.waived_amount) }}</b><span>given away as goodwill</span></div></div>{% endif %}
{% for r in rows %}<div class="card"><h2><a href="/clients/{{ r.c.id }}">{{ r.c.name }}</a></h2>
<span class="hint">{{ r.c.currency }} {{ money(r.c.rate) }}/h &middot; quoted {{ money(r.t.quoted_amount) }} &middot; waived {{ money(r.t.waived_amount) }}</span></div>{% endfor %}
<div class="card"><h2>Add a client</h2><form method="post" action="/clients">
<label for="name">Client or project</label><input id="name" name="name" required>
<div class="row"><div><label for="rate">Your hourly rate</label><input id="rate" name="rate" type="number" step="any" min="0.01" value="50"></div>
<div><label for="cur">Currency</label><input id="cur" name="currency" value="USD"></div>
<div><label for="gw">Goodwill threshold (hours)</label><input id="gw" name="goodwill" type="number" step="any" min="0" value="0.5"></div></div>
<label for="contract">The agreement (paste the text)</label><textarea id="contract" name="contract" required placeholder="Paste the signed scope of work, contract or proposal."></textarea>
<p class="hint">Requests at or under the goodwill threshold are flagged as small, so you can choose to be generous on purpose.</p>
<button class="btn" type="submit">Add client</button></form></div>
{% endblock %}"""

CLIENT = """{% extends "base.html" %}{% block title %}{{ c.name }} &middot; ScopeGuard{% endblock %}{% block content %}
<h1>{{ c.name }}</h1><p class="lede">{{ c.currency }} {{ money(c.rate) }}/h. Paste the client's latest message below.</p>
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
{% if long %}<p class="error">This agreement is longer than {{ 24000 }} characters. Only the start is sent to the model.</p>{% endif %}
<div class="card"><form method="post" action="/clients/{{ c.id }}/check"><label for="msg">Client's message</label>
<textarea id="msg" name="message" required placeholder="Paste the email or chat message here."></textarea>
<p><button class="btn" type="submit" data-wait="Reading it against the agreement&hellip;">Check against the agreement</button></p></form></div>
{% if t.quoted or t.waived %}<div class="stats"><div class="stat"><b>{{ money(t.quoted_amount) }}</b><span>quoted</span></div><div class="stat"><b>{{ money(t.waived_amount) }}</b><span>waived</span></div></div>{% endif %}
{% if checks %}<h2>Past checks</h2>{% for k in checks %}<div class="card"><a href="/checks/{{ k.id }}">{{ k.at[:10] }}</a>: {{ k.message[:140] }}{% if k.message|length > 140 %}&hellip;{% endif %}<br>
{% for i in k['items'] %}<span class="pill p-{{ i.relation }}">{{ i.relation|replace('_',' ') }}</span> {% endfor %}</div>{% endfor %}{% endif %}
<details class="card"><summary>The agreement on file</summary><pre class="contract">{{ c.contract }}</pre></details>
{% endblock %}"""

CHECK = """{% extends "base.html" %}{% block title %}Check &middot; {{ c.name }}{% endblock %}{% block content %}
<p><a href="/clients/{{ c.id }}">&larr; {{ c.name }}</a></p><h1>What it found</h1>
<div class="card"><span class="hint">Client wrote ({{ k.at[:10] }}):</span><br>{{ k.message }}</div>
{% if not k['items'] %}<p class="card">No requests for work found in that message.</p>{% endif %}
{% for i in k['items'] %}{% set d = done.get(loop.index0) %}
<div class="card" id="item-{{ loop.index0 }}"><h2>{{ i.summary }} <span class="pill p-{{ i.relation }}">{{ i.verdict }}</span></h2>
{% if i.why %}<p>{{ i.why }}</p>{% endif %}
{% if i.quote %}<blockquote>{{ i.quote }}</blockquote><span class="hint">Verified: this text is in your agreement (highlighted below).</span>{% endif %}
{% if i.note %}<p class="hint">{{ i.note }}</p>{% endif %}
{% if i.billable %}<p><b>Estimate: {{ '%g'|format(i.hours_low) }}&ndash;{{ '%g'|format(i.hours_high) }} h = {{ c.currency }} {{ money(i.price_low) }}&ndash;{{ money(i.price_high) }}</b>
<span class="hint"> (the hours are the model's estimate; the price is hours &times; your rate)</span>{% if i.small %}<br><span class="waive">Small: you may want to just do this one.</span>{% endif %}</p>
{% if d %}<p class="{{ 'done' if d.decision == 'quoted' else 'waive' }}">{{ 'Quoted' if d.decision == 'quoted' else 'Waived as goodwill' }}: {{ '%g'|format(d.hours) }} h = {{ c.currency }} {{ money(d.amount) }}</p>{% endif %}
<form class="actions" method="post" action="/checks/{{ k.id }}/decide"><input type="hidden" name="idx" value="{{ loop.index0 }}">
<div><label for="h{{ loop.index0 }}">Hours</label><input id="h{{ loop.index0 }}" name="hours" type="number" step="0.25" min="0" value="{{ '%g'|format((i.hours_low + i.hours_high) / 2) }}"></div>
<button class="btn small" name="decision" value="quoted">Quote it</button><button class="btn small quiet" name="decision" value="waived">Waive (goodwill)</button></form>{% endif %}</div>
{% endfor %}
{% if reply %}<div class="card"><h2>Draft reply to send</h2><p class="hint">Built from the verified findings. Every number is computed from your rate; the model wrote none of them.</p>
<pre class="reply" id="reply">{{ reply }}</pre><p><button class="btn small" type="button" onclick="navigator.clipboard.writeText(document.getElementById('reply').innerText)">Copy</button></p></div>{% endif %}
<details class="card" open><summary>Your agreement, with the cited clauses marked</summary><pre class="contract">{{ contract }}</pre></details>
{% endblock %}"""

LEDGER = """{% extends "base.html" %}{% block title %}Ledger &middot; ScopeGuard{% endblock %}{% block content %}
<h1>Ledger</h1><div class="stats"><div class="stat"><b>{{ money(t.quoted_amount) }}</b><span>quoted ({{ t.quoted }})</span></div>
<div class="stat"><b>{{ money(t.waived_amount) }}</b><span>waived ({{ t.waived }})</span></div></div>
<p><a class="btn small quiet" href="/ledger.csv">Download CSV</a></p>
{% if entries %}<div class="card"><table><tr><th>Date</th><th>Client</th><th>Request</th><th>What you did</th><th>Hours</th><th>Value</th></tr>
{% for e in entries %}<tr><td>{{ e.at[:10] }}</td><td>{{ clients[e.client_id].name if e.client_id in clients else '' }}</td><td>{{ e.summary }}</td>
<td>{{ 'Quoted' if e.decision == 'quoted' else 'Waived' }}</td><td>{{ '%g'|format(e.hours) }}</td><td>{{ money(e.amount) }}</td></tr>{% endfor %}</table></div>
{% else %}<p class="hint">Nothing yet. Quote or waive a request from a check and it appears here.</p>{% endif %}
{% endblock %}"""

TEMPLATES = {"base.html": BASE, "index.html": INDEX, "client.html": CLIENT, "check.html": CHECK, "ledger.html": LEDGER}
