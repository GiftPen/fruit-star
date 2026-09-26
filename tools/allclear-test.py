#!/usr/bin/env python3
"""ALL CLEAR: the board is empty, and that has to be a different EVENT, not a louder tier.

The three cluster tiers all scale the same three channels, so "clear the whole board" landed
as an ordinary tier-3 pop. The trouble is that a clear board exists for no time at all --
turnBody's very first act is spawnBuds, which refills it -- so the flourish has to be armed
in front of the turn body AND the body has to wait. That ordering is the thing most likely
to rot, so most of this is end-to-end: play a real turn that empties a real board.

Also checks the flourish only fires on an actually-empty board, that it drains, and that a
run ending mid-flourish does not carry it into the next one."""
import subprocess, os, re, json, sys
_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'

TEST = """<script>
window.addEventListener('load', () => setTimeout(async () => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const wipe = () => { for (let r = 0; r < F.ROWS; r++) for (let c = 0; c < F.COLS; c++) {
                         F.grid[r][c] = -1; F.special[r][c] = null; F.hp[r][c] = 0; F.appear[r][c] = 0; } };
  const cv = document.getElementById('game');
  const tap = (r, c) => { const b = cv.getBoundingClientRect();
    const x = b.left + (c + 0.5) * b.width / F.COLS, y = b.top + (r + 0.5) * b.height / F.ROWS;
    cv.dispatchEvent(new PointerEvent('pointerdown', { clientX: x, clientY: y, bubbles: true }));
    cv.dispatchEvent(new PointerEvent('pointerup',   { clientX: x, clientY: y, bubbles: true })); };
  // wait for a condition instead of guessing a delay: the turn's own settle time varies
  const until = async (f, ms) => { const end = Date.now() + ms;
    while (Date.now() < end) { if (f()) return true; await sleep(40); } return false; };

  chk('the hold is shorter than the flourish, or the board refills into silence',
      F.ALLCLEAR_HOLD < F.ALLCLEAR_MS, true);

  // ---- END TO END: a real turn that empties a real board ----
  // A bomb tap, not a placement. A placement big enough to clear a real board is over the
  // item thresholds, so it leaves a star or a bomb bud sitting in the cell and the board is
  // not empty at all -- which means the finisher is essentially always an item, and that is
  // the path worth testing.
  F.start('arcade');
  await sleep(200);
  wipe();
  let put = 0;
  for (let r = 2; r <= 6; r++) for (let c = 2; c <= 6; c++) { F.grid[r][c] = put % 3; put++; }
  F.grid[4][4] = 0; F.special[4][4] = 'bomb';      // a 5x5 blast covers exactly that block
  F.busy = false; F.allClear = null; F.dirty = true; F.draw();
  chk('the board really is full enough to count', F.filledCount() >= F.ALLCLEAR_MIN, true);
  tap(4, 4);
  const fired = await until(() => !!F.allClear, 4000);
  chk('emptying the board fires the flourish', fired, true);
  chk('and it starts from the cell that finished the job',
      F.allClear ? Math.floor((F.allClear.cx - F.pad) / F.cell) : -1, 4);
  chk('the board is still bare when it fires', F.filledCount(), 0);

  // The hold's whole job. An item tap spawns nothing, so the only thing it can be seen to do
  // is keep the turn from finishing under the flourish -- without this, deleting the hold
  // costs nothing that any check here would notice.
  chk('input is blocked the moment it fires', F.busy, true);
  await sleep(Math.max(0, F.ALLCLEAR_HOLD - 400));
  chk('and stays blocked while it plays', F.busy, true);
  chk('the board is still bare that whole time', F.filledCount(), 0);

  // ...and the turn must still finish afterwards, or the hold is a soft lock. An item tap is
  // a FREE turn -- it spawns nothing -- so what has to come back is the input, not the fruit.
  const resumed = await until(() => !F.busy, 3000);
  chk('the hold ends instead of locking the game', resumed, true);

  // and the game is genuinely playable again: the next placement runs a normal turn
  F.nextColor = 0;
  const before2 = F.touchCount;
  tap(0, 0);
  const played = await until(() => F.touchCount > before2 && F.filledCount() > 0, 3000);
  chk('the next placement plays a normal turn', played, true);

  // ---- clearing a nearly-bare board is not an achievement ----
  // Round 1 opens with ten fruit and stays sparse, so without a floor this would fire for
  // popping three within a minute of starting and the rare thing would stop feeling rare.
  F.start('arcade');
  await sleep(200);
  wipe(); F.grid[4][3] = 0; F.grid[4][5] = 0; F.nextColor = 0;   // three, counting the one placed
  F.allClear = null;
  tap(4, 4);
  await sleep(1600);
  chk('the board did empty', true, true);
  chk('but three fruit is not an all clear', !!F.allClear, false);

  // ---- a big clear that leaves ANYTHING standing is not an all clear ----
  // Same blast as the real case, over the threshold on its own, with one fruit parked outside
  // it. If the empty-board test is ever dropped, only this notices.
  F.start('arcade');
  await sleep(200);
  wipe();
  let put2 = 0;
  for (let r = 2; r <= 6; r++) for (let c = 2; c <= 6; c++) { F.grid[r][c] = put2 % 3; put2++; }
  F.grid[4][4] = 0; F.special[4][4] = 'bomb';
  F.grid[0][0] = 1;                                  // outside the 5x5: a survivor
  F.busy = false; F.allClear = null;
  tap(4, 4);
  await sleep(2200);
  chk('the blast was big enough to qualify', F.filledCount(), 1);
  chk('but one fruit left standing is not an all clear', !!F.allClear, false);

  // ---- the flourish animates, and drains ----
  F.start('arcade'); F.resetEffects();
  F.allClear = { cx: 100, cy: 100, t: 0 };
  F.draw(); F.draw(); F.draw();
  chk('its clock advances while it is up', F.allClear && F.allClear.t > 0, true);
  for (let i = 0; i < 400; i++) F.draw();          // hand-pumped 60Hz frames
  chk('it ends instead of hanging on the plate', F.allClear, null);

  // it has to keep DRAWING on its own: the board is empty and nothing else is moving, so
  // without it in the liveness test draw() early-returns and the wave freezes half way.
  F.resetEffects();
  F.allClear = { cx: 100, cy: 100, t: 0.2 };
  F.dirty = false;
  const before = F.allClear.t;
  F.draw();
  chk('an empty settled board keeps drawing so the wave can travel',
      F.allClear && F.allClear.t > before, true);

  // ---- the word actually reaches the canvas ----
  // every check above passes with the text never drawn, so read what fillText receives
  F.resetEffects();
  F.allClear = { cx: 100, cy: 100, t: 0.3 };
  const proto = CanvasRenderingContext2D.prototype, realFill = proto.fillText;
  const said = [];
  proto.fillText = function (t, ...a) { said.push(String(t)); return realFill.call(this, t, ...a); };
  F.dirty = true; F.draw();
  proto.fillText = realFill;
  chk('the plate says the word', said.includes(F.d('allClear')), true);
  chk('and the word is not empty in this language', (F.d('allClear') || '').length > 0, true);

  // ---- a run that ends mid-flourish must not carry it into the next one ----
  F.allClear = { cx: 1, cy: 1, t: 0.4 };
  F.resetEffects();
  chk('reset clears it', F.allClear, null);

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
        '--autoplay-policy=no-user-gesture-required',
        '--virtual-time-budget=40000','--dump-dom',f'http://localhost:8899/{_PAGE}?test=1'],
        capture_output=True, text=True, timeout=240).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"allclear: {len(d['fails'])} fail")
for f in d['fails'][:10]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
