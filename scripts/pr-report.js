// Structured PR reports for the AnyUmbrelStore CI workflows.
//
// Both "app-store-check" and "upstream-watch" capture the stdout of their
// check script and post it as a *sticky* PR comment (an existing bot
// comment is updated in place instead of a new one being created on every
// push). Instead of dumping the raw log, this module parses the output and
// renders a structured report:
//
//   * headline with outcome + key numbers
//   * per-app result table with known-justification annotations
//     (app store check) / alert & info bullets (upstream watch)
//   * collapsible full log + links to commit and workflow run
//
// Configuration via environment variables:
//   REPORT_KIND   "app-store-check" or "upstream-watch"
//   REPORT_FILE   captured stdout of the check step
//   OUTCOME       outcome of the check step (success/failure/cancelled/...)
//
// Invoked via actions/github-script:
//   return require('./scripts/pr-report.js')({ github, context, core })

'use strict';

const fs = require('fs');

const REPORTS = {
  'app-store-check': {
    marker: '<!-- app-store-check-report -->',
    name: 'App Store Check',
    file: '/tmp/check-output.txt',
    blurb:
      'Prüft alle App-Pakete gegen die offiziellen Umbrel-Packaging-Regeln: ' +
      'Manifest-Schema, Versionen (kein bare "latest", Digest-Pinning beweglicher Tags), ' +
      'Port-Konflikte im eigenen Store und gegen den offiziellen Store, app_proxy-Wiring, ' +
      'Icon-Existenz und Security-Gates.',
  },
  'upstream-watch': {
    marker: '<!-- upstream-watch-report -->',
    name: 'Upstream Changelog Watch',
    file: '/tmp/upstream-output.txt',
    blurb:
      'Changelog-Radar für die Upstreams hinter den App-Paketen: neue stabile Releases, ' +
      'Breaking-Change-Stichworte in den Release Notes und verschwundene Quell-Repos. ' +
      'Version-/Digest-Bumps übernimmt Renovate – dieser Watch meldet, was dabei zu beachten wäre.',
  },
};

// Warnings that are expected for this store's packages: the manifest
// descriptions already justify them (VPN client needs NET_ADMIN + tun).
const KNOWN_JUSTIFICATIONS = [
  {
    test: /cap_add .*NET_ADMIN/i,
    note: 'für VPN-Clients erforderlich, über die Manifest-Beschreibung begründet',
  },
  {
    test: /device mounts .*\/dev\/net\/tun/i,
    note: 'für den VPN-Tunnel erforderlich, über die Manifest-Beschreibung begründet',
  },
];

function readRaw(file) {
  try {
    return fs.readFileSync(file, 'utf8').trim();
  } catch (e) {
    return '';
  }
}

function tagged(raw, tag) {
  const prefix = '[' + tag + ']';
  const out = [];
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (t.indexOf(prefix) === 0) out.push(t.slice(prefix.length).trim());
  }
  return out;
}

// "anyumbrelstore-gluetun/docker-compose.yml: service app: ..." ->
// { app: 'anyumbrelstore-gluetun', file: 'docker-compose.yml', msg: '...' }
function splitAppEntry(entry) {
  let m = entry.match(/^([a-z0-9][a-z0-9-]*)\/([^:]+):\s*(.*)$/i);
  if (m) return { app: m[1], file: m[2], msg: m[3] };
  m = entry.match(/^([a-z0-9][a-z0-9-]*):\s*(.*)$/i);
  if (m) return { app: m[1], file: '', msg: m[2] };
  return { app: '', file: '', msg: entry };
}

function groupByApp(entries) {
  const map = new Map();
  for (const entry of entries) {
    const s = splitAppEntry(entry);
    const key = s.app || '(allgemein)';
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(s);
  }
  return map;
}

function justificationFor(msg) {
  for (const j of KNOWN_JUSTIFICATIONS) {
    if (j.test.test(msg)) return j.note;
  }
  return null;
}

function stripJustificationTail(msg) {
  return msg.replace(/\s*\(requires justification[^)]*\)\s*$/i, '');
}

// All app packages in the checkout (the check always validates every app).
function storeApps() {
  try {
    return fs
      .readdirSync('.')
      .filter(function (d) {
        try {
          return (
            fs.statSync(d).isDirectory() &&
            fs.existsSync(d + '/umbrel-app.yml')
          );
        } catch (e) {
          return false;
        }
      })
      .sort();
  } catch (e) {
    return [];
  }
}

function indented(raw) {
  if (!raw) {
    return (
      '    (keine Ausgabe - der Checks-Schritt ist vermutlich vorher ' +
      'abgebrochen; Details im Workflow-Log)'
    );
  }
  return raw
    .split('\n')
    .map(function (l) {
      return '    ' + l;
    })
    .join('\n');
}

function footer() {
  const repo = process.env.GITHUB_REPOSITORY || '';
  const sha = process.env.GITHUB_SHA || '';
  const runId = process.env.GITHUB_RUN_ID || '';
  const server = process.env.GITHUB_SERVER_URL || 'https://github.com';
  const now = new Date().toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
  const bits = ['*Stand: ' + now];
  if (sha && repo) {
    bits.push(
      'Commit [' + sha.slice(0, 7) + '](' + server + '/' + repo + '/commit/' + sha + ')'
    );
  }
  if (runId && repo) {
    bits.push(
      '[Workflow-Run](' + server + '/' + repo + '/actions/runs/' + runId + ')'
    );
  }
  return bits.join(' · ') + '*';
}

// ---------------------------------------------------------------- app check

function appStoreParts(raw, outcome, cfg) {
  const errors = tagged(raw, 'ERROR');
  const warns = tagged(raw, 'WARN ');
  const sm = raw.match(/Summary:\s*(\d+)\s*error\(s\),\s*(\d+)\s*warning\(s\)/);
  const km = raw.match(
    /Checked\s*(\d+)\s*app package\(s\)\s*against\s*(\d+)\s*official store ports/
  );
  const cm = raw.match(/Apps changed in this PR:\s*(.*)$/m);
  const changed = cm
    ? cm[1]
        .split(',')
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean)
    : [];
  const parsedSummary = Boolean(sm);
  const errCount = parsedSummary ? parseInt(sm[1], 10) : errors.length;
  const warnCount = parsedSummary ? parseInt(sm[2], 10) : warns.length;

  const parts = [];
  if (outcome === 'success') parts.push('## ✅ ' + cfg.name + ': bestanden');
  else if (outcome === 'failure')
    parts.push('## ❌ ' + cfg.name + ': fehlgeschlagen');
  else parts.push('## ⚠️ ' + cfg.name + ': ' + (outcome || 'unbekannter Status'));
  parts.push('', '*' + cfg.blurb + '*', '');

  let scope = '**Geprüft:** alle App-Pakete des Stores';
  if (km)
    scope =
      '**Geprüft:** ' + km[1] + ' App-Paket(e) gegen ' + km[2] +
      ' offizielle Store-Ports';
  parts.push(
    scope + ' · **Fehler:** ' + errCount + ' · **Warnungen:** ' + warnCount,
    ''
  );

  if (!parsedSummary && (outcome !== 'success' || !raw)) {
    parts.push(
      '⚠️ Der Check-Schritt hat kein zusammengefasstes Ergebnis erzeugt ' +
        '(Status: ' + (outcome || 'unbekannt') +
        '). Details im einklappbaren Log bzw. im Workflow-Run.',
      ''
    );
  }

  if (parsedSummary || errors.length || warns.length) {
    const errByApp = groupByApp(errors);
    const warnByApp = groupByApp(warns);
    const seen = new Set();
    const rows = [];
    const addRow = function (app) {
      if (seen.has(app)) return;
      seen.add(app);
      const e = errByApp.get(app) || [];
      const w = warnByApp.get(app) || [];
      const name =
        changed.indexOf(app) !== -1
          ? '**' + app + '** *(in diesem PR geändert)*'
          : app;
      let status;
      let detail;
      if (e.length) {
        status = '❌ Fehler';
        detail = e.length + ' Fehler';
      } else if (w.length) {
        const unjustified = w.filter(function (x) {
          return !justificationFor(x.msg);
        }).length;
        status = unjustified === 0 ? '🟡 Warnungen (begründet)' : '🟡 Warnungen';
        detail =
          w.length + ' Warnung(en)' +
          (unjustified ? ', ' + unjustified + ' unbegründet' : '');
      } else {
        status = '✅ Bestanden';
        detail = '—';
      }
      rows.push('| ' + name + ' | ' + status + ' | ' + detail + ' |');
    };
    for (const app of storeApps()) addRow(app);
    for (const app of Array.from(errByApp.keys()).concat(Array.from(warnByApp.keys()))) {
      addRow(app);
    }
    parts.push('### Ergebnis pro App', '', '| App | Status | Befunde |', '|---|---|---|');
    Array.prototype.push.apply(parts, rows);
    parts.push('');
  }

  if (errors.length) {
    parts.push('### ❌ Fehler – blockieren den Merge', '');
    for (const s of errors.map(splitAppEntry)) {
      const loc = s.app + (s.file ? '/' + s.file : '');
      parts.push('- **' + loc + '**: ' + s.msg);
    }
    parts.push('');
  }

  if (warns.length) {
    parts.push(
      '### 🟡 Warnungen – blockieren den Merge nicht, brauchen aber eine Begründung im Manifest',
      ''
    );
    for (const s of warns.map(splitAppEntry)) {
      const loc = s.app + (s.file ? '/' + s.file : '');
      const msg = stripJustificationTail(s.msg);
      const j = justificationFor(s.msg);
      parts.push(
        '- **' + loc + '**: ' + msg +
          (j ? ' → ✅ ' + j : ' → ⚠️ bitte im Manifest begründen')
      );
    }
    parts.push('');
  }
  return parts;
}

// ----------------------------------------------------------- upstream watch

function upstreamParts(raw, outcome, cfg) {
  const alerts = tagged(raw, 'ALERT');
  const infos = tagged(raw, 'INFO ');
  const wm = raw.match(
    /Upstream watch:\s*(\d+)\s*watched,\s*(\d+)\s*alert\(s\),\s*(\d+)\s*info\(s\)/
  );
  const watched = wm ? parseInt(wm[1], 10) : null;
  const isPR = process.env.GITHUB_EVENT_NAME === 'pull_request';

  const parts = [];
  if (outcome === 'success')
    parts.push('## 🔭 ' + cfg.name + (isPR ? ' (PR-Testlauf)' : ''));
  else if (outcome === 'failure')
    parts.push('## ❌ ' + cfg.name + ': fehlgeschlagen');
  else parts.push('## ⚠️ ' + cfg.name + ': ' + (outcome || 'unbekannter Status'));
  parts.push('', '*' + cfg.blurb + '*', '');

  let scope =
    '**Beobachtet:** ' + (watched !== null ? watched + ' Upstream-Quellen' : 'Upstream-Quellen');
  if (wm)
    scope +=
      ' · **Alerts:** ' + parseInt(wm[2], 10) + ' · **Infos:** ' + parseInt(wm[3], 10);
  else scope += ' · **Alerts:** ' + alerts.length + ' · **Infos:** ' + infos.length;
  parts.push(scope, '');

  if (alerts.length) {
    parts.push('### ⚠️ Handlungsbedarf', '');
    for (const a of alerts) parts.push('- ' + a);
    parts.push('');
    if (isPR) {
      parts.push(
        '> Hinweis: Im PR-Testlauf landen Alerts nur in diesem Kommentar. ' +
          'Der montägliche Scheduled-Run veröffentlicht denselben Report als Issue.',
        ''
      );
    }
  } else if (outcome === 'success') {
    parts.push('✅ Kein Handlungsbedarf – alle überwachten Quellen sind ruhig.', '');
  } else {
    parts.push(
      '⚠️ Der Check-Schritt endete mit "' + (outcome || 'unbekannt') +
        '", ohne Alerts zu melden – Details im Workflow-Log.',
      ''
    );
  }

  if (infos.length) {
    parts.push('### ℹ️ Hinweise', '');
    for (const i of infos) parts.push('- ' + i);
    parts.push('');
  }
  return parts;
}

// ------------------------------------------------------------------- main

module.exports = async function prReport(args) {
  const github = args.github;
  const context = args.context;
  const core = args.core;

  const kind = process.env.REPORT_KIND || 'app-store-check';
  const cfg = REPORTS[kind];
  if (!cfg) throw new Error('Unbekannter REPORT_KIND: ' + kind);

  const raw = readRaw(process.env.REPORT_FILE || cfg.file);
  const outcome = process.env.OUTCOME || 'unknown';

  const parts =
    kind === 'upstream-watch'
      ? upstreamParts(raw, outcome, cfg)
      : appStoreParts(raw, outcome, cfg);

  const body = [cfg.marker, '']
    .concat(parts)
    .concat([
      '<details>',
      '<summary>📄 Vollständige Ausgabe des Checks</summary>',
      '',
      indented(raw),
      '',
      '</details>',
      '',
      '---',
      footer(),
    ])
    .join('\n');

  const { data: comments } = await github.rest.issues.listComments({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.issue.number,
    per_page: 100,
  });
  const existing = comments.find(function (c) {
    return (c.body || '').indexOf(cfg.marker) !== -1;
  });
  if (existing) {
    await github.rest.issues.updateComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      comment_id: existing.id,
      body: body,
    });
    core.info('Kommentar aktualisiert: ' + existing.html_url);
  } else {
    const { data: created } = await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: context.issue.number,
      body: body,
    });
    core.info('Kommentar erstellt: ' + created.html_url);
  }
};
