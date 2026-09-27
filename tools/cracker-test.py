#!/usr/bin/env python3
"""The cracker pace is a difficulty knob, so the game has to actually read it.

The arcade ladder cycles cracker -> +1 colour -> +1 spawn. When crackers were flattened to
"unlocked, one hit, always", the cracker rung stopped changing anything and Lv.5 and Lv.8
became identical to the level below -- the chip counted up and nothing got harder. The rung
is held by FREQUENCY now: 5 touches, then 4 at Lv.5, 3 at Lv.8.

rules-test checks the formula. This checks the game obeys it, which is a different question:
the turn loop happily kept using the CRACKER_EVERY constant while MODES.arcade.crackerGap
returned a perfectly correct number that nothing read. spawnCracker is called by name inside
the module, so it cannot be stubbed from outside -- the only honest observation is to play
turns and watch the board."""
import subprocess, os, re, sys, json

_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'

TEST = """<script>
window.addEventListener('load', () => setTimeout(async () => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const cv = document.getElementById('game');
  const crackers = () => { let n = 0;
    for (let r = 0; r < F.ROWS; r++) for (let c = 0; c < F.COLS; c++)
      if (F.grid[r][c] === F.CRACKER) n++;
    return n; };
  // keep the board from filling up and ending the run, without touching the crackers --
  // they are what is being counted, and only an item can clear one anyway
  const clearFruit = () => { for (let r = 0; r < F.ROWS; r++) for (let c = 0; c < F.COLS; c++)
    if (F.grid[r][c] !== F.CRACKER) { F.grid[r][c] = -1; F.special[r][c] = null; F.appear[r][c] = 0; } };
  const tap = (r, c) => { const b = cv.getBoundingClientRect();
    cv.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true,
      clientX: b.left + (c + 0.5) * b.width / F.COLS, clientY: b.top + (r + 0.5) * b.height / F.ROWS }));
    cv.dispatchEvent(new PointerEvent('pointerup', { bubbles: true,
      clientX: b.left + (c + 0.5) * b.width / F.COLS, clientY: b.top + (r + 0.5) * b.height / F.ROWS })); };

  // Play `turns` placements at a score that puts the ladder on `lv`, and report which touch
  // numbers a cracker appeared on.
  const paceAt = async (lv, turns) => {
    F.start('arcade');
    await sleep(250);
    F.score = (lv - 1) * F.MILESTONE_STEP;
    F.touchCount = 0; F.updateHUD();
    clearFruit();
    const seen = [];
    let had = crackers();
    for (let i = 0; i < turns; i++) {
      // an empty board, so a placement never pops and always ends a turn
      clearFruit();
      let spot = null;
      for (let r = 0; r < F.ROWS && !spot; r++) for (let c = 0; c < F.COLS; c++)
        if (F.grid[r][c] === -1) { spot = [r, c]; break; }
      if (!spot) break;
      F.busy = false;
      tap(spot[0], spot[1]);
      for (let k = 0; k < 60 && F.busy; k++) await sleep(50);   // let the turn finish
      const now = crackers();
      if (now > had) seen.push(F.touchCount);
      had = now;
    }
    return seen;
  };

  // Lv.8 is the third cracker rung: every 3 touches
  const fast = await paceAt(8, 9);
  chk('Lv.8 spawns a cracker every 3 touches', fast, [3, 6, 9]);
  // ...and Lv.2, the first rung, is the base pace. If the loop is reading the constant
  // instead of the knob, these two come out the same.
  const slow = await paceAt(2, 10);
  chk('Lv.2 spawns a cracker every 5 touches', slow, [5, 10]);
  chk('the ladder actually changed the pace', fast.length > slow.length, true);

  // ---- and the odds table has to say the pace you are PLAYING at ----
  // It was printing the CRACKER_EVERY constant, so at Lv.8 the panel said "5터치마다" while
  // the board was handing out a cracker every 3. A wrong number in the one place a player
  // goes to check is worse than no number.
  F.start('arcade');
  await sleep(200);
  F.score = 7 * F.MILESTONE_STEP;            // Lv.8 -> gap 3
  F.updateHUD();
  document.getElementById('info-btn').click();
  await sleep(400);
  const panel = document.getElementById('info-body').textContent;
  const want3 = F.d('everyNTouch', F.crackerGap());
  const want5 = F.d('everyNTouch', F.CRACKER_EVERY);
  chk('the gap under test really did step down', [F.crackerGap(), F.CRACKER_EVERY], [3, 5]);
  // Read the cracker's OWN line in the fruit list, not the panel as a whole. The stat row
  // below prints "5터치마다 -> 3터치마다", so a whole-panel search finds the right number
  // even when the fruit line is showing the wrong one -- which is exactly the bug.
  const crRow = [...document.querySelectorAll('#info-body *')]
    .filter(e => e.querySelector && e.querySelector('.ft-odds'))
    .find(e => e.textContent.includes(F.d('cracker')));
  const crOdds = crRow ? crRow.querySelector('.ft-odds').textContent.trim() : '(없음)';
  chk('the cracker line shows the pace in play, not the starting one', crOdds, want3);
  chk('sanity: those two differ, so the line above can fail', want3 === want5, false);
  // the stat row still carries base -> now, which is where the change is legible
  chk('the stat table keeps both the base and the current pace',
      panel.includes(want5) && panel.includes(want3), true);
  chk('the coin-fruit chance is in the panel too',
      panel.includes(String(Math.round(F.COIN_FRUIT_CHANCE * 1000) / 10)), true);
  // arcade has no touch budget, so a stage-touch row there reads "0 -> NaN"
  chk('no NaN anywhere in the panel', panel.includes('NaN'), false);

  document.title = 'RESULT ' + JSON.stringify({ fails, fast, slow });
 } catch (e) { document.title = 'THREW ' + (e && e.message) + '|' + String(e && e.stack || '').slice(0, 300); }
}, 700));
</script>"""

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open(_PAGE, 'w', encoding='utf-8').write(
    open('index.html', encoding='utf-8').read().replace('</body>', TEST + '</body>'))
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless', '--disable-gpu', '--no-first-run', '--window-size=430,932',
        '--virtual-time-budget=60000', '--dump-dom', f'http://localhost:8899/{_PAGE}?test=1'],
        capture_output=True, text=True, timeout=300).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"cracker: Lv.8 {d['fast']} · Lv.2 {d['slow']} · {len(d['fails'])} fail")
for f in d['fails'][:6]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
