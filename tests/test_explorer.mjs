import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {prepareCurve, rankPool, henryBound} from '../docs/explorer/numerics.mjs';

const fixture = JSON.parse(readFileSync(new URL('../docs/media/query-replay-data.json', import.meta.url)));
const curves = fixture.corpus.curves.map(prepareCurve);

test('browser full solve reproduces the six archived native queries', () => {
  for (const state of fixture.queries) {
    const rows = rankPool(curves, fixture.corpus.pairs, state.pressure, state.feed);
    assert.equal(rows.length, state.supported_candidates);
    assert.deepEqual(rows.slice(0, 5).map(row => row.id), state.winner_ids);
    state.scores.forEach((value, index) => {
      assert.ok(Math.abs(rows[index].score - value) <= 1e-8 * Math.max(1, value));
    });
  }
});

test('unsupported pressure returns an empty ranking', () => {
  assert.deepEqual(rankPool(curves, fixture.corpus.pairs, 201, .5), []);
});

test('displayed Henry bounds agree with the analytic example and handle equality', () => {
  const b = henryBound(1.1, 1);
  assert.ok(Math.abs(b.low - 4/15) < 1e-14);
  assert.ok(Math.abs(b.high - 11/30) < 1e-14);
  assert.ok(Math.abs(b.scoreUpper - 11/19) < 1e-14);
  assert.ok(b.excluded);
  assert.equal(henryBound(1.5, 1).excluded, false);
});
