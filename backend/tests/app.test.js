'use strict';

const assert = require('assert');
const request = require('supertest');
const { app } = require('../src/index.js');

describe('API', function () {
  it('GET /health returns 200', async function () {
    const res = await request(app).get('/health');
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.body.status, 'ok');
  });

  it('GET /api/items returns list', async function () {
    const res = await request(app).get('/api/items');
    assert.strictEqual(res.status, 200);
    assert.ok(Array.isArray(res.body.items));
  });

  it('POST /api/items creates item', async function () {
    const res = await request(app).post('/api/items').send({ name: 'demo' });
    assert.strictEqual(res.status, 201);
    assert.ok(res.body.id);
    assert.strictEqual(res.body.name, 'demo');
  });

  it('GET /api/ai/reports returns aggregate payload', async function () {
    const res = await request(app).get('/api/ai/reports');
    assert.strictEqual(res.status, 200);
    assert.ok(res.body.loadedAt);
    assert.ok(res.body.reports);
    assert.ok(Object.prototype.hasOwnProperty.call(res.body.reports, 'codeReview'));
  });

  it('GET /ai-dashboard/ serves dashboard HTML', async function () {
    const res = await request(app).get('/ai-dashboard/');
    assert.strictEqual(res.status, 200);
    assert.ok(/AI pipeline dashboard/i.test(res.text));
  });

  it('GET /api/ai/reports/raw rejects unknown name', async function () {
    const res = await request(app).get('/api/ai/reports/raw/nope.txt');
    assert.strictEqual(res.status, 400);
  });
});
