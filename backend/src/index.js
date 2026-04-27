'use strict';

const express = require('express');
const { mountAiDashboard } = require('./aiDashboardRoutes');

// TODO: add request logging middleware when traffic grows
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
mountAiDashboard(app);

app.get('/health', (_req, res) => {
  res.status(200).json({ status: 'ok', service: 'test-ai-backend' });
});

const items = [];

app.get('/api/items', (_req, res) => {
  res.json({ items });
});

app.post('/api/items', (req, res) => {
  const { name } = req.body || {};
  if (!name || typeof name !== 'string') {
    return res.status(400).json({ error: 'name is required' });
  }
  const id = String(items.length + 1);
  const item = { id, name };
  items.push(item);
  res.status(201).json(item);
});

app.get('/api/items/:id', (req, res) => {
  const item = items.find((i) => i.id === req.params.id);
  if (!item) {
    return res.status(404).json({ error: 'not found' });
  }
  res.json(item);
});

if (require.main === module) {
  app.listen(PORT, () => {
    // eslint-disable-next-line no-console
    console.log(`Server listening on port ${PORT}`);
  });
}

module.exports = { app };
