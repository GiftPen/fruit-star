#!/usr/bin/env python3
"""The arcade ladder's knobs are only real if the GAME reads them.

The arcade ladder cycles cracker -> +1 colour -> +1 spawn. When crackers were flattened to
"unlocked, one hit, always", the cracker rung stopped changing anything and Lv.5 and Lv.8
became identical to the level below -- the chip counted up and nothing got harder. The rung
is held by FREQUENCY now: 5 touches, then 4 at Lv.5, 3 at Lv.8.

rules-test checks the formulas. This checks the game obeys them, which is a different
question: the turn loop happily kept using the CRACKER_EVERY constant while
MODES.arcade.crackerGap returned a perfectly correct number that nothing read. spawnCracker
is called by name inside the module, so it cannot be stubbed from outside -- the only honest
observation is to play turns and watch the board.

Also covers the one knob that pays the player back for climbing: the coin-fruit chance, +2
points a level. Arcade's ladder had only ever made things worse, so a deep run was attrition
with no upside."""
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
    F.score = F.LEVEL_AT[lv - 1];
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
      if (now > had) seen.push({ at: F.touchCount, by: now - had });
      had = now;
    }
    return seen;
  };
  const touchesOf = s => s.map(x => x.at);

  // Lv.8 is the third cracker rung: every 3 touches
  const fast8 = await paceAt(8, 9), fast = touchesOf(fast8);
  chk('Lv.8 spawns a cracker every 3 touches', fast, [3, 6, 9]);
  chk('...one at a time', fast8.map(x => x.by), [1, 1, 1]);
  // ...and Lv.2, the first rung, is the base pace. If the loop is reading the constant
  // instead of the knob, these two come out the same.
  const slow2 = await paceAt(2, 10), slow = touchesOf(slow2);
  chk('Lv.2 spawns a cracker every 5 touches', slow, [5, 10]);
  chk('the ladder actually changed the pace', fast.length > slow.length, true);

  // The fourth cycle has no colour left to give, so its rung pays in a SECOND cracker per
  // drop. The turn loop calls spawnCracker in a loop now, and a loop that runs once looks
  // exactly like the old single call -- so count what lands, not what the rule returns.
  const pair = await paceAt(F.CRACKER_PAIR_LEVEL, 6);
  chk('the pair rung drops two at a time', pair.map(x => x.by), [2, 2, 2]);
  chk('...on the tightened 2-touch pace', touchesOf(pair), [2, 4, 6]);
  const single = await paceAt(F.CRACKER_PAIR_LEVEL - 1, 6);
  chk('the level below still drops one', single.map(x => x.by), [1, 1, 1]);

  // ---- the coin-fruit chance climbs with the ladder, at the SPAWN SITE ----
  // Math.random decides both where a bud lands and whether it carries a coin, so pinning it
  // turns the coin decision into a pure threshold: a roll of 0.10 is above Lv.1's 6% and
  // below Lv.4's 12%. Reading rules().coinFruit back would prove nothing -- spawnBuds was
  // adding the constant to the relic bonus and never consulting the mode at all.
  const coinAt = (lv, roll) => {
    F.start('arcade');
    F.score = F.LEVEL_AT[lv - 1];
    for (let r = 0; r < F.ROWS; r++) for (let c = 0; c < F.COLS; c++) {
      F.grid[r][c] = -1; F.special[r][c] = null; F.coinCell[r][c] = 0; F.appear[r][c] = 0; }
    const real = Math.random; Math.random = () => roll;
    try { F.spawnBuds(1); } finally { Math.random = real; }
    let n = 0;
    for (let r = 0; r < F.ROWS; r++) for (let c = 0; c < F.COLS; c++)
      if (F.coinCell[r][c] && F.grid[r][c] >= 0) n++;
    return n;
  };
  chk('the rate really does climb', [F.coinFruitChance(0), F.coinFruitChance(3)], [0.06, 0.12]);
  chk('a 10% roll carries no coin at Lv.1', coinAt(1, 0.10), 0);
  chk('...and does at Lv.4, because the rate passed it', coinAt(4, 0.10), 1);
  // and it stops climbing where the ladder does, instead of riding an uncapped milestone
  chk('the rate is clamped at the top level',
      Math.round(F.coinFruitChance(500) * 100),
      Math.round((F.COIN_FRUIT_CHANCE + F.COIN_FRUIT_STEP * (F.MAX_LEVEL - 1)) * 100));
  chk('rush does not get the arcade climb', F.MODES.rush.coinFruit(30), F.COIN_FRUIT_CHANCE);

  // ---- and the odds table has to say the pace you are PLAYING at ----
  // It was printing the CRACKER_EVERY constant, so at Lv.8 the panel said "5터치마다" while
  // the board was handing out a cracker every 3. A wrong number in the one place a player
  // goes to check is worse than no number.
  F.start('arcade');
  await sleep(200);
  F.score = F.LEVEL_AT[7];                   // Lv.8 -> gap 3
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
  // Its own row, not the panel as a whole -- "6" appears all over a table of numbers, so a
  // substring search on the base rate passes happily while the row shows nothing but the base.
  const coinRow = [...document.querySelectorAll('#info-body .st-row')]
    .find(e => e.textContent.includes(F.d('statCoinFruit')));
  const coinTxt = coinRow ? coinRow.textContent : '(없음)';
  const nowPct = `${Math.round(F.coinFruitChance() * 1000) / 10}%`;
  chk('the sanity of this check: Lv.8 is not the base rate',
      nowPct === `${Math.round(F.COIN_FRUIT_CHANCE * 1000) / 10}%`, false);
  chk('the coin-fruit row shows the rate in play', coinTxt.includes(nowPct), true);
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
print(f"ladder: 크래커 Lv.8 {d['fast']} / Lv.2 {d['slow']} · {len(d['fails'])} fail")
for f in d['fails'][:6]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
