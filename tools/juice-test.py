#!/usr/bin/env python3
"""Cluster payoff: a bigger clear has to be a DIFFERENT event, not a louder one.

burst() was identical for every pop -- one ring, fourteen droplets -- so a 20-fruit clear was
a 3-fruit clear played twenty times. The only thing that scaled with the cluster was the
screen shake, and that capped at 17. A tester who plays Block Blast said the board was flat
and that nothing rewarded a big clear; this is the mechanism behind that.

Three tiers, each ADDING a kind of event: juice splats on the plate, then hitstop plus a
shockwave that shoves the cells, then a full-screen colour wash. This checks each one fires
at its own threshold and NOT below it, that they stack, that the pop sound climbs the scale
across the wave instead of repeating one note, and that every channel drains rather than
leaking. Thresholds are read from the game so retuning them is not a failure."""
import subprocess, os, re, json, sys
_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'   # per-process: two runs of the suite were deleting each other's page

TEST = """<script>
window.addEventListener('load', () => setTimeout(async () => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  const T1 = F.TIER_SPLAT, T2 = F.TIER_SHOCK, T3 = F.TIER_WASH;
  chk('tiers are ordered and distinct', T1 < T2 && T2 < T3, true);

  // ---- clusterTier maps sizes to tiers, with nothing below the first threshold
  chk('below the first threshold there is no tier', F.clusterTier(T1 - 1), 0);
  chk('first threshold', F.clusterTier(T1), 1);
  chk('second threshold', F.clusterTier(T2), 2);
  chk('third threshold', F.clusterTier(T3), 3);
  chk('past the top stays at the top', F.clusterTier(T3 * 5), 3);

  F.start('rush');
  const clear = () => { F.resetEffects(); };
  const fire = n => { clear(); F.clusterPayoff(4, 4, n, 0, 0); };

  // ---- each channel appears only at or above its own threshold
  fire(T1 - 1);
  chk('small clear leaves the plate alone', F.splats.length, 0);
  chk('small clear does not stop time', F.hitstop, 0);
  chk('small clear does not shove the board', !!F.shock, false);

  fire(T1);
  chk('tier 1 marks the plate', F.splats.length > 0, true);
  chk('tier 1 does not stop time', F.hitstop, 0);
  chk('tier 1 does not shove the board', !!F.shock, false);

  fire(T2);
  chk('tier 2 keeps the splats', F.splats.length > 0, true);
  chk('tier 2 stops time', F.hitstop, F.HITSTOP_MS);
  chk('tier 2 shoves the board', !!F.shock, true);
  chk('the shove has direction from the epicentre', F.shock ? typeof F.shock.cx : null, 'number');

  fire(T3);
  chk('tier 3 still stops time', F.hitstop > 0, true);
  chk('tier 3 still shoves', !!F.shock, true);
  // the wash is scheduled for when the wave lands
  const washAfter = await new Promise(res => setTimeout(() => res(!!F.wash), 60));
  chk('tier 3 washes the screen', washAfter, true);

  // the wash takes the FRUIT's colour, not white -- that is the whole point of it
  clear(); F.clusterPayoff(4, 4, T3, 3, 0);
  const lemonWash = await new Promise(res => setTimeout(() => res(F.wash), 60));
  chk('the wash is the fruit colour', lemonWash && lemonWash.color, F.COLORS[3]);

  // ---- a bigger clear splashes more of the board
  fire(T1); const few = F.splats.length;
  fire(T3 * 2); const many = F.splats.length;
  chk('a bigger clear splashes more', many > few, true);

  // ---- the channels drain instead of leaking
  clear(); F.clusterPayoff(4, 4, T3, 0, 0);
  for (let i = 0; i < 900; i++) F.draw();      // hand-pumped frames = one 60Hz frame each
  chk('splats drain', F.splats.length, 0);
  chk('the shove ends', !!F.shock, false);
  chk('hitstop runs out', F.hitstop <= 0, true);

  // ---- resetEffects clears every new channel: a run that ends mid-payoff must not carry it
  F.clusterPayoff(4, 4, T3, 0, 0);
  F.resetEffects();
  chk('reset clears the payoff', [F.splats.length, !!F.shock, !!F.wash, F.hitstop],
                                 [0, false, false, 0]);

  // ---- the fruit has to come apart into pieces of ITSELF ----
  // The burst used to be a flat wash of colour over the cell with a few specks on top, and
  // the fruit simply vanished underneath it: a nine-fruit clear laid a solid pink carpet
  // over a 5x5 area for half a second. What explodes has to be what you popped.
  F.start('rush');
  F.resetEffects();
  chk('the fruit is pre-cut into shards', (F.fruitShards[0] || []).length, F.SHARD_N);
  F.burst(3, 3, 0);
  const shardsOf = () => F.particles.filter(p => p.type === 'shard');
  chk('a pop throws pieces of the fruit', shardsOf().length, F.SHARD_N);
  chk('and they are drawn from its own sprite',
      shardsOf().every(p => p.img && p.img.width > 0), true);
  chk('they leave in different directions',
      new Set(shardsOf().map(p => Math.round(Math.atan2(p.vy, p.vx) * 10))).size > 1, true);
  chk('a pop still throws juice as well',
      F.particles.filter(p => !p.type).length > 0, true);

  // shards are a drawImage per frame each, so a huge clear must not keep adding them
  F.resetEffects();
  for (let i = 0; i < 40; i++) F.burst(3, 3, 0);
  chk('the number of pieces is capped', shardsOf().length <= F.SHARD_MAX + F.SHARD_N, true);
  // ...and the counter that enforces the cap must come back down, or the cap becomes permanent
  for (let i = 0; i < 2000; i++) F.draw();
  chk('the pieces all clear', shardsOf().length, 0);
  chk('and the cap is released again', F.liveShards <= 0, true);
  F.resetEffects();
  chk('resetEffects releases it too', F.liveShards, 0);

  // ---- the pop sound climbs across the wave instead of repeating one note.
  // Assert the FREQUENCY. An earlier version only checked that the caller passed a step
  // along, which still passed after the pitch term was deleted -- a vacuous test.
  const hzs = [0, 1, 2, 3].map(step => F.SFX.popHz(0, step));
  chk('each ring is higher than the last', hzs[0] < hzs[1] && hzs[1] < hzs[2], true);
  chk('the climb is audible, not a rounding error', hzs[1] / hzs[0] > 1.05, true);
  chk('it caps instead of shrieking', F.SFX.popHz(0, 99), F.SFX.popHz(0, 50));
  chk('different fruit still start on different notes',
      F.SFX.popHz(0, 0) !== F.SFX.popHz(4, 0), true);
  // The ladder is only worth anything if the whole chain carries the ring index, so stub the
  // thing that ACTUALLY makes the sound and read the frequency that reaches it. Stubbing
  // SFX.play instead proved nothing -- it replaced the forwarder under test, so a one-argument
  // forwarder that dropped the step still passed.
  F.SFX.unlock(); F.SFX.resume();
  chk('the audio context is actually running for this check', F.SFX.names.length > 0, true);
  const style = F.SFX.POP_STYLES[F.SFX.popStyle];
  const realStyle = style.play, heard = [];
  style.play = f => { heard.push(Math.round(f)); };
  F.SFX.play('pop', 0, 0);
  F.SFX.play('pop', 0, 3);
  style.play = realStyle;
  chk('the sound engine received two different pitches', heard.length === 2 && heard[0] !== heard[1],
      true);
  chk('and the later ring was the higher one', heard[1] > heard[0], true);

  // ---- end to end: a REAL cluster must climb. Everything above can pass while the game's own
  // pop loop still calls SFX.play("pop", colour) with no ring index at all.
  F.start('rush');
  for (let r = 0; r < F.ROWS; r++) for (let c = 0; c < F.COLS; c++) {
    F.grid[r][c] = -1; F.special[r][c] = null; F.hp[r][c] = 0;
  }
  const row = 4;
  for (let c = 0; c < F.COLS; c++) F.grid[row][c] = 0;   // a full row of one colour
  F.grid[row][3] = -1;                                   // the gap we drop into
  F.nextColor = 0;
  const live2 = [];
  style.play = f => { live2.push(Math.round(f)); };
  const cv = document.getElementById('game');
  const b2 = cv.getBoundingClientRect();
  const x = b2.left + (3 + 0.5) * b2.width / F.COLS;
  const y = b2.top + (row + 0.5) * b2.height / F.ROWS;
  cv.dispatchEvent(new PointerEvent('pointerdown', { clientX: x, clientY: y, bubbles: true }));
  cv.dispatchEvent(new PointerEvent('pointerup',   { clientX: x, clientY: y, bubbles: true }));
  await new Promise(res => setTimeout(res, 900));        // let the whole wave play out
  style.play = realStyle;
  const uniq = [...new Set(live2)];
  chk('a real cluster actually popped', live2.length >= 4, true);
  chk('a real cluster produced more than one pitch', uniq.length > 1, true);
  chk('the real cluster climbed', Math.max(...live2) > Math.min(...live2), true);

  document.title = 'RESULT ' + JSON.stringify({ fails });
 } catch (e) { document.title = 'THREW ' + (e && e.message) + ' | ' + String(e && e.stack || '').slice(0, 300); }
}, 700));
</script>"""

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open(_PAGE,'w',encoding='utf-8').write(
    open('index.html',encoding='utf-8').read().replace('</body>', TEST + '</body>'))
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless','--disable-gpu','--no-first-run','--window-size=430,932',
        # without this the audio context stays suspended, SFX.play() is a no-op, and the
        # pitch-ladder checks pass by never running
        '--autoplay-policy=no-user-gesture-required',
        '--virtual-time-budget=30000','--dump-dom',f'http://localhost:8899/{_PAGE}?test=1'],
        capture_output=True, text=True, timeout=180).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"juice: {len(d['fails'])} fail")
for f in d['fails'][:10]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
