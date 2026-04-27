'use strict';

const fs = require('fs/promises');
const path = require('path');
const express = require('express');

const PUBLIC_DIR = path.join(__dirname, '..', 'public', 'ai-dashboard');

function candidateReportDirs() {
  const dirs = [];
  if (process.env.AI_REPORTS_DIR) {
    dirs.push(path.resolve(process.env.AI_REPORTS_DIR));
  }
  dirs.push(path.join(process.cwd(), 'var', 'ai-reports'));
  if (process.env.NODE_ENV !== 'production') {
    dirs.push(path.join(__dirname, '..', '..'));
  }
  return [...new Set(dirs)];
}

async function readTextIfExists(filePath) {
  try {
    const buf = await fs.readFile(filePath, 'utf8');
    return { path: filePath, content: buf };
  } catch {
    return null;
  }
}

function tryParseJson(text) {
  const t = text.trim();
  if (!t.startsWith('{') && !t.startsWith('[')) {
    return { raw: text };
  }
  try {
    return JSON.parse(t);
  } catch {
    return { raw: text, parseError: true };
  }
}

async function pickFirstExistingFile(names) {
  for (const base of candidateReportDirs()) {
    for (const name of names) {
      const full = path.join(base, name);
      try {
        await fs.access(full);
        return full;
      } catch {
        /* try next */
      }
    }
  }
  return null;
}

async function loadAggregatedReports() {
  const sourcesTried = candidateReportDirs();
  const loadedAt = new Date().toISOString();
  const reports = {};
  const errors = [];

  const loadJsonFile = async (key, filenames) => {
    const found = await pickFirstExistingFile(filenames);
    if (!found) {
      reports[key] = { missing: true, filenames };
      return;
    }
    const data = await readTextIfExists(found);
    if (!data) {
      reports[key] = { missing: true };
      return;
    }
    try {
      reports[key] = {
        path: found,
        data: tryParseJson(data.content),
      };
    } catch (e) {
      errors.push(`${key}: ${e.message}`);
      reports[key] = { error: e.message };
    }
  };

  await loadJsonFile('codeReview', ['ai_report.txt']);
  await loadJsonFile('security', ['security_report.txt']);
  await loadJsonFile('bugPredictor', ['bug_predictor_report.txt']);
  await loadJsonFile('deployDecision', ['deploy_decision.json']);

  const logPath = await pickFirstExistingFile(['docker_app.log']);
  if (logPath) {
    const data = await readTextIfExists(logPath);
    if (data) {
      const lines = data.content.split('\n').filter(Boolean);
      const errLines = lines.filter((l) => /error/i.test(l)).slice(0, 20);
      const warnLines = lines.filter((l) => /warn/i.test(l)).slice(0, 10);
      reports.dockerLog = {
        path: logPath,
        lineCount: lines.length,
        sampleErrors: errLines,
        sampleWarnings: warnLines,
      };
    }
  } else {
    reports.dockerLog = { missing: true };
  }

  return { loadedAt, sourcesTried, reports, errors };
}

function createAiDashboardRouter() {
  const router = express.Router();

  router.get('/reports', async (_req, res) => {
    try {
      const body = await loadAggregatedReports();
      res.json(body);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  router.get('/reports/raw/:name', async (req, res) => {
    const allowed = new Set([
      'ai_report.txt',
      'security_report.txt',
      'bug_predictor_report.txt',
      'deploy_decision.json',
      'docker_app.log',
    ]);
    const name = String(req.params.name || '');
    if (!allowed.has(name)) {
      return res.status(400).json({ error: 'unknown report name' });
    }
    const found = await pickFirstExistingFile([name]);
    if (!found) {
      return res.status(404).json({ error: 'file not found', name });
    }
    const data = await readTextIfExists(found);
    if (!data) {
      return res.status(404).json({ error: 'unreadable', name });
    }
    res.type('text/plain; charset=utf-8').send(data.content);
  });

  return router;
}

function mountAiDashboard(app) {
  app.use('/api/ai', createAiDashboardRouter());
  app.use(
    '/ai-dashboard',
    express.static(PUBLIC_DIR, {
      index: 'index.html',
      extensions: ['html'],
    })
  );
}

module.exports = { mountAiDashboard, loadAggregatedReports, candidateReportDirs };
