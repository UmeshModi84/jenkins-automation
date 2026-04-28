'use strict';

const $ = (sel) => document.querySelector(sel);

function pill(text, kind) {
  const span = document.createElement('span');
  span.className = `pill ${kind}`;
  span.textContent = text;
  return span;
}

function card(title, body) {
  const el = document.createElement('article');
  el.className = 'card';
  const h = document.createElement('h2');
  h.textContent = title;
  el.appendChild(h);
  if (typeof body === 'string') {
    const p = document.createElement('p');
    p.textContent = body;
    p.style.color = 'var(--muted)';
    p.style.margin = '0';
    el.appendChild(p);
  } else {
    el.appendChild(body);
  }
  return el;
}

function metrics(rows) {
  const dl = document.createElement('dl');
  dl.className = 'metrics';
  for (const [k, v] of rows) {
    const dt = document.createElement('dt');
    dt.textContent = k;
    const dd = document.createElement('dd');
    dd.textContent = v;
    dl.appendChild(dt);
    dl.appendChild(dd);
  }
  return dl;
}

function renderDeploy(dec) {
  const wrap = document.createElement('div');
  const d = dec && dec.data;
  if (!d || dec.missing) {
    wrap.appendChild(pill('no report', 'muted'));
    wrap.appendChild(
      document.createTextNode(' Run the pipeline or set AI_REPORTS_DIR.')
    );
    return wrap;
  }
  const decision = d.decision || 'unknown';
  const kind =
    decision === 'DEPLOY_OK' ? 'ok' : decision === 'NO_DEPLOY' ? 'bad' : 'warn';
  wrap.appendChild(pill(decision, kind));
  if (d.confidence != null) {
    const p = document.createElement('p');
    p.style.margin = '0.35rem 0 0';
    p.style.fontSize = '0.85rem';
    p.style.color = 'var(--muted)';
    p.textContent = `Confidence: ${d.confidence}`;
    wrap.appendChild(p);
  }
  if (d.blockers && d.blockers.length) {
    const pre = document.createElement('pre');
    pre.className = 'snippet';
    pre.textContent = d.blockers.join('\n');
    wrap.appendChild(pre);
  }
  if (d.metrics) {
    wrap.appendChild(
      metrics(
        Object.entries(d.metrics).map(([k, v]) => [k, String(v)])
      )
    );
  }
  return wrap;
}

function renderCodeReview(cr) {
  const wrap = document.createElement('div');
  const d = cr && cr.data;
  if (!d || cr.missing) {
    wrap.appendChild(pill('no report', 'muted'));
    return wrap;
  }
  const s = d.summary || {};
  wrap.appendChild(
    metrics([
      ['Secret patterns', String(s.hardcoded_secret_pattern_hits ?? '—')],
      ['console.log', String(s.console_log_hits ?? '—')],
      ['TODO markers', String(s.todo_hits ?? '—')],
    ])
  );
  const oa = d.openai_review;
  if (oa && oa.enabled && oa.markdown) {
    const h = document.createElement('h3');
    h.style.margin = '0.75rem 0 0.35rem';
    h.style.fontSize = '0.95rem';
    h.textContent = 'OpenAI summary';
    wrap.appendChild(h);
    const pre = document.createElement('pre');
    pre.className = 'snippet';
    pre.textContent = oa.markdown;
    wrap.appendChild(pre);
  } else if (oa && oa.enabled && oa.error) {
    wrap.appendChild(pill(`OpenAI error: ${oa.error}`, 'warn'));
  }
  return wrap;
}

function renderSecurity(sec) {
  const wrap = document.createElement('div');
  const d = sec && sec.data;
  if (!d || sec.missing) {
    wrap.appendChild(pill('no report', 'muted'));
    return wrap;
  }
  const n = d.summary && d.summary.finding_count;
  wrap.appendChild(
    pill(n === 0 ? 'clean' : `${n} finding(s)`, n === 0 ? 'ok' : 'warn')
  );
  const findings = (d.findings || []).slice(0, 5);
  if (findings.length) {
    const pre = document.createElement('pre');
    pre.className = 'snippet';
    pre.textContent = JSON.stringify(findings, null, 2);
    wrap.appendChild(pre);
  }
  return wrap;
}

function renderBugPredictor(bp) {
  const wrap = document.createElement('div');
  const d = bp && bp.data;
  if (!d || bp.missing) {
    wrap.appendChild(pill('no report', 'muted'));
    return wrap;
  }
  const top = (d.top_risk_files || [])[0];
  if (top) {
    wrap.appendChild(
      metrics([
        ['Top file', top.path || '—'],
        ['Score', String(top.score ?? '—')],
      ])
    );
  } else {
    wrap.appendChild(pill('no scored files', 'muted'));
  }
  return wrap;
}

function renderDockerLog(dl) {
  const wrap = document.createElement('div');
  if (!dl || dl.missing) {
    wrap.appendChild(pill('no log', 'muted'));
    return wrap;
  }
  wrap.appendChild(
    metrics([
      ['Lines', String(dl.lineCount ?? 0)],
      ['Error samples', String((dl.sampleErrors || []).length)],
    ])
  );
  if ((dl.sampleErrors || []).length) {
    const pre = document.createElement('pre');
    pre.className = 'snippet';
    pre.textContent = dl.sampleErrors.join('\n');
    wrap.appendChild(pre);
  }
  return wrap;
}

async function load() {
  const meta = $('#meta');
  const cards = $('#cards');
  const raw = $('#raw');
  const errBox = document.querySelector('.err');

  meta.textContent = 'Loading…';
  cards.innerHTML = '';
  raw.innerHTML = '';
  if (errBox) {
    errBox.remove();
  }

  let payload;
  try {
    const res = await fetch('/api/ai/reports');
    payload = await res.json();
    if (!res.ok) {
      throw new Error(payload.error || res.statusText);
    }
  } catch (e) {
    meta.textContent = '';
    const p = document.createElement('p');
    p.className = 'err';
    p.textContent = `Failed to load: ${e.message}`;
    document.body.appendChild(p);
    return;
  }

  meta.textContent = `Loaded ${payload.loadedAt} · searched: ${(
    payload.sourcesTried || []
  ).join(' | ')}`;

  cards.appendChild(card('Deploy decision', renderDeploy(payload.reports.deployDecision)));
  cards.appendChild(card('Code review', renderCodeReview(payload.reports.codeReview)));
  cards.appendChild(card('Security scan', renderSecurity(payload.reports.security)));
  cards.appendChild(card('Bug risk', renderBugPredictor(payload.reports.bugPredictor)));
  cards.appendChild(card('Docker log (sample)', renderDockerLog(payload.reports.dockerLog)));

  const h = document.createElement('h2');
  h.textContent = 'Raw downloads';
  const links = document.createElement('div');
  links.className = 'raw-links';
  const names = [
    'ai_report.txt',
    'security_report.txt',
    'bug_predictor_report.txt',
    'deploy_decision.json',
    'docker_app.log',
  ];
  for (const n of names) {
    const a = document.createElement('a');
    a.href = `/api/ai/reports/raw/${encodeURIComponent(n)}`;
    a.textContent = n;
    a.target = '_blank';
    a.rel = 'noopener';
    links.appendChild(a);
  }
  raw.appendChild(h);
  raw.appendChild(links);
}

$('#refresh').addEventListener('click', load);
load();
