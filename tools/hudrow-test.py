#!/usr/bin/env python3
"""The arcade chip row: one line, no collisions, no stray button chrome.

Three faults reported from the phone at once, all in the same row:
  - the ➕ chip sat 4px below its neighbours
  - it had a green glow under it
  - "⚠️ 위험!" overlapped the coin chip once the touch count reached three digits

The first two are the global `button` rule leaking into a chip built on a <button>: it gives
every button `margin-top: 8px` and the green brand box-shadow. That had already been patched
twice elsewhere -- the purse in the desktop rail, then the arcade row -- so .chip-btn cuts it
off at the source and this pins it.

The third is gone entirely: a label pinned into a row it shares with growing numbers will
always collide eventually. The plate takes a red rim instead, which has nothing to lay out.
"""
import subprocess, os, re, sys, json

_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'

TEST = """<script>
window.addEventListener('load', () => setTimeout(() => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  F.start('arcade');
  // three digits of touches and four of coins: the widest the row ever gets
  F.touchCount = 128; F.coins = 1450; F.score = 98765; F.updateHUD();

  const ids = ['info-btn', 'st-lvl-chip', 'st-touch-chip', 'st-spawn-chip', 'st-coin'];
  const box = {}; for (const id of ids) {
    const e = document.getElementById(id);
    box[id] = e ? e.getBoundingClientRect() : null;
  }
  chk('every chip is present', ids.filter(id => !box[id]), []);

  // 1) one line: same top, same height
  const tops = ids.map(id => Math.round(box[id].top));
  chk('the chips sit on one line', [...new Set(tops)].length, 1);
  const hs = ids.map(id => Math.round(box[id].height));
  chk('and they are the same height', [...new Set(hs)].length, 1);

  // 2) no button chrome leaking in
  const dirty = [];
  for (const id of ids) {
    const c = getComputedStyle(document.getElementById(id));
    if (c.boxShadow !== 'none') dirty.push(`${id} shadow ${c.boxShadow.slice(0, 30)}`);
    if (parseFloat(c.marginTop) !== 0) dirty.push(`${id} margin-top ${c.marginTop}`);
  }
  chk('no button shadow or margin leaks into a chip', dirty, []);

  // 3) nothing overlaps anything, at the widest the row gets
  const overlaps = [];
  for (let i = 0; i < ids.length; i++)
    for (let j = i + 1; j < ids.length; j++) {
      const a = box[ids[i]], b = box[ids[j]];
      if (a.right > b.left + 1 && b.right > a.left + 1 &&
          a.bottom > b.top + 1 && b.bottom > a.top + 1)
        overlaps.push(`${ids[i]} x ${ids[j]}`);
    }
  chk('no two chips overlap', overlaps, []);

  // and the whole row stays on screen
  const off = ids.filter(id => box[id].left < -1 || box[id].right > window.innerWidth + 1);
  chk('the row fits the screen', off, []);

  // 4) the danger label is gone for good -- it is the thing that collided
  chk('there is no danger label left to collide with',
      [...document.querySelectorAll('[id^="danger-label"]')].length, 0);

  // 5) ...and the board says it instead. wasDanger drives a rim drawn on the plate, so the
  //    frame has to stay live while it is up or the rim would freeze mid-pulse.
  // Count what the frame actually DOES. Asserting on F.dirty proved nothing -- it reads
  // false either way -- and the check passed with the liveness flag removed.
  const proto = Object.getPrototypeOf(F.ctx);
  const real = proto.drawImage;
  let blits = 0;
  proto.drawImage = function (...a) { blits++; return real.apply(this, a); };
  // let the board settle first: coins counting up and pop-ins keep the frame live on their
  // own, and measuring before they finish compares nothing
  F.resetEffects();
  F.wasDanger = false;
  let idle = -1;
  for (let i = 0; i < 400; i++) {
    F.dirty = false; blits = 0; F.draw();
    if (blits === 0) { idle = 0; break; }
  }
  F.wasDanger = true; F.dirty = false; blits = 0; F.draw();
  const danger = blits;
  proto.drawImage = real;
  chk('the board does settle, so this comparison means something', idle, 0);
  chk('a nearly-full board keeps drawing so the rim can breathe', danger > 0, true);

  document.title = 'RESULT ' + JSON.stringify({ fails, tops, hs });
 } catch (e) { document.title = 'THREW ' + (e && e.message) + ' | ' + String(e && e.stack || '').slice(0, 300); }
}, 700));
</script>"""

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open(_PAGE, 'w', encoding='utf-8').write(
    open('index.html', encoding='utf-8').read().replace('</body>', TEST + '</body>'))
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless', '--disable-gpu', '--no-first-run', '--window-size=390,844',
        '--virtual-time-budget=30000', '--dump-dom',
        f'http://localhost:8899/{_PAGE}?test=1'],
        capture_output=True, text=True, timeout=180).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"  칩 윗변 {d.get('tops')}  높이 {d.get('hs')}")
print(f"hudrow: {len(d['fails'])} fail")
for f in d['fails'][:8]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
