#!/usr/bin/env python3
"""Odds boosts have to diminish and work for every fruit -- and the opening quotas are fixed.

"+N 더 등장" used to scale a share that was ALREADY a percentage, with the other fruit squeezed
into what was left. Three things were wrong with that and none of them were visible from the
card text:
  - it was linear. Every +1 added the same number of points, so stacking never got expensive.
  - it hit a wall. Once the others reached the 2% floor the boosted fruit stopped moving: for
    cherry, +5 and +6 did literally nothing. A relic you bought did not do anything.
  - it was upside down. The step scaled with the fruit's OWN base, so at maximum stack every
    fruit reached 88% except banana -- the rarest and most valuable one -- stuck at 36%.

Boosts are a flat step on the WEIGHT now, renormalised. This pins the properties, not the
numbers: ODDS_STEP and the base odds are read from the game, so retuning them is not a failure.
"""
import subprocess, os, re, json, sys

TEST = """<script>
window.addEventListener('load', () => setTimeout(() => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  F.start('rush');
  const n = F.activeColors();
  const at = (i, k) => { F.oddsMult = new Array(7).fill(0); F.oddsMult[i] = k;
                         return F.colorOdds()[i]; };

  chk('every colour is in play for this check', n, 7);
  chk('the step is a real number', F.ODDS_STEP > 0, true);

  const curves = {};
  for (let i = 0; i < n; i++) {
    const c = []; for (let k = 0; k <= 8; k++) c.push(at(i, k));
    curves[i] = c;
  }

  // 1) every step must still move the number -- no dead picks
  const dead = [];
  for (let i = 0; i < n; i++)
    for (let k = 1; k <= 8; k++)
      if (curves[i][k] - curves[i][k - 1] < 0.5) dead.push(`fruit${i} +${k}`);
  chk('no step is wasted', dead, []);

  // 2) and each step must be SMALLER than the one before it
  const notFalling = [];
  for (let i = 0; i < n; i++)
    for (let k = 2; k <= 8; k++) {
      const prev = curves[i][k - 1] - curves[i][k - 2];
      const now = curves[i][k] - curves[i][k - 1];
      if (now >= prev - 1e-9) notFalling.push(`fruit${i} +${k}: ${now.toFixed(2)} vs ${prev.toFixed(2)}`);
    }
  chk('each step gives less than the last', notFalling, []);

  // 3) a single step has to be worth taking, for every fruit
  const weak = [];
  for (let i = 0; i < n; i++) {
    const gain = curves[i][1] - curves[i][0];
    if (gain < 5) weak.push(`fruit${i} +${gain.toFixed(1)}`);
  }
  chk('one card is felt whatever the fruit', weak, []);

  // 4) the rare fruit must not be the hardest to build. Under the old formula banana topped
  //    out at 36% where everything else reached 88%.
  const top = [];
  for (let i = 0; i < n; i++) top.push(curves[i][6]);
  const spread = Math.max(...top) / Math.min(...top);
  chk('no fruit is locked out of its own build', spread < 1.6, true);
  const rare = F.BASE_ODDS.indexOf(Math.min(...F.BASE_ODDS));
  chk('the rarest fruit gains the most from one card',
      curves[rare][1] - curves[rare][0] === Math.max(...[...Array(n).keys()].map(i => curves[i][1] - curves[i][0])),
      true);

  // 5) it stays a probability distribution, and the floor still holds
  F.oddsMult = new Array(7).fill(0); F.oddsMult[0] = 8;
  const o = F.colorOdds();
  const sum = o.reduce((a, b) => a + b, 0);
  chk('the odds still sum to 100', Math.abs(sum - 100) < 0.01, true);
  chk('nothing falls under the floor', o.filter(v => v < F.MIN_ODDS - 0.01), []);

  // 6) no boost at all leaves the base odds untouched
  F.oddsMult = new Array(7).fill(0);
  const plain = F.colorOdds().map(v => +v.toFixed(2));
  chk('with no boosts the base odds are unchanged',
      plain, F.BASE_ODDS.map(v => +v.toFixed(2)));

  // ---- the hand-set opening quotas ----
  // They exist to be readable, so the check is that they ARE readable, and that fixing them
  // did not disturb the curve that follows.
  const E = F.EARLY_QUOTA;
  chk('the opening quotas are hand-set', E.length >= 3, true);
  const ugly = [];
  for (let i = 0; i < E.length; i++) {
    if (F.rushQuota(i + 1) !== E[i]) ugly.push(`stage ${i + 1} does not use the table`);
    if (E[i] % 50 !== 0) ugly.push(`${E[i]} is not a round number`);
    if (i && E[i] <= E[i - 1]) ugly.push(`${E[i]} does not rise`);
  }
  chk('every opening quota is round and rising', ugly, []);
  // the stage after the table has to come from the curve, untouched
  const after = E.length + 1;
  let q = F.RUSH_QUOTA_1;
  const r = Math.floor((after - 1) / F.STAGES_PER_ROUND);
  for (let k = 0; k < r; k++) q *= F.roundSpan(k);
  q = Math.round(q * Math.pow(F.RUSH_STAGE_MUL, (after - 1) % F.STAGES_PER_ROUND));
  chk('the curve resumes untouched after the table', F.rushQuota(after), q);
  // ...and the handover must not be a cliff
  const jump = F.rushQuota(after) / E[E.length - 1];
  chk('the handover is not a cliff', jump > 1 && jump < 2.2, true);

  document.title = 'RESULT ' + JSON.stringify({ fails, step: F.ODDS_STEP, early: E,
    sample: { banana: curves[6].map(v => +v.toFixed(1)), cherry: curves[0].map(v => +v.toFixed(1)) } });
 } catch (e) { document.title = 'THREW ' + (e && e.message) + ' | ' + String(e && e.stack || '').slice(0, 300); }
}, 700));
</script>"""

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open('_ot.html','w',encoding='utf-8').write(
    open('index.html',encoding='utf-8').read().replace('</body>', TEST + '</body>'))
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless','--disable-gpu','--no-first-run','--window-size=430,932',
        '--virtual-time-budget=30000','--dump-dom','http://localhost:8899/_ot.html?test=1'],
        capture_output=True, text=True, timeout=180).stdout
finally:
    os.remove('_ot.html')

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"  ODDS_STEP={d['step']}  바나나 {d['sample']['banana']}")
print(f"  고정 목표 {d.get('early')}")
print(f"  {'':<14}체리   {d['sample']['cherry']}")
print(f"odds: {len(d['fails'])} fail")
for f in d['fails'][:8]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
