#!/usr/bin/env python3
"""The board's depth must follow the theme, and the cached cell must be rebuilt when it moves.

The empty cell was two flat fills -- 64 identical squares on a slightly darker rectangle --
which is what the "판이 밋밋하다" feedback was about. It is now a recess (shadowed top edge,
lit bottom lip, soft floor), pre-rendered once and blitted.

Two things can go wrong and neither is visible in a single screenshot:
  1. hardcoding the highlight. The four themes are dark navy, brown wood, teal and blue-grey;
     a highlight tuned on navy reads as dirt on wood. Every depth colour is derived from
     --board / --board-cell.
  2. caching it and forgetting to invalidate. Switching themes would keep the old colours,
     and resizing would keep an image built for the old size -- stretched and blurry.

The cache is the WHOLE board, not one cell. A per-cell version blitted 64+ times a frame was
catastrophically slower than the flat fill it replaced under software rasterisation: the item
suite went from 59s to not finishing in 25 minutes, with no error to show for it.
"""
import subprocess, os, re, json, sys
_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'   # per-process: two runs of the suite were deleting each other's page

TEST = """<script>
window.addEventListener('load', () => setTimeout(() => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  // BOTH forms: the plate colours come out of CSS as hex, the derived ones as rgb(). A
  // digit-scraping parser read '#262a3d' as [262, 3] and every comparison below was noise.
  const parse = s => {
    s = String(s).trim();
    if (s[0] === '#') {
      const h = s.slice(1);
      const n = h.length === 3 ? h.split('').map(x => x + x).join('') : h;
      return [0, 2, 4].map(i2 => parseInt(n.slice(i2, i2 + 2), 16));
    }
    return (s.match(/[0-9]+/g) || []).map(Number).slice(0, 3);
  };
  const lum = s => { const [r, g, b] = parse(s); return (r * 299 + g * 587 + b * 114) / 1000; };

  // mixHex must move toward white and toward black, and not invent a colour
  chk('mix to white is lighter', lum(F.mixHex('#404040', 'hi', 0.5)) > lum('rgb(64,64,64)'), true);
  chk('mix to black is darker',  lum(F.mixHex('#404040', 'lo', 0.5)) < lum('rgb(64,64,64)'), true);
  chk('mixing by 0 changes nothing', parse(F.mixHex('#123456', 'hi', 0)), [18, 52, 86]);
  chk('3-digit hex works too', parse(F.mixHex('#abc', 'hi', 0)), parse(F.mixHex('#aabbcc', 'hi', 0)));

  F.start('rush');
  const seen = {};
  for (const t of F.THEMES) {
    F.setTheme(t);
    F.readPlate();
    const P = F.PLATE;
    seen[t] = { cell: P.cell, hi: P.cellHi, lo: P.cellLo, edge: P.edge };
    // the depth has to bracket the cell colour, on every theme
    if (!(lum(P.cellHi) > lum(P.cell)))
      fails.push({ case: `${t}: the lit lip is not lighter than the floor`,
                   got: [P.cellHi, P.cell] });
    if (!(lum(P.cellLo) < lum(P.cell)))
      fails.push({ case: `${t}: the shadowed edge is not darker than the floor`,
                   got: [P.cellLo, P.cell] });
    if (!(lum(P.edge) < lum(P.bg)))
      fails.push({ case: `${t}: the vignette is not darker than the plate`,
                   got: [P.edge, P.bg] });
  }
  // ...and it must actually DIFFER per theme, or it is hardcoded
  const uniqHi = new Set(F.THEMES.map(t => seen[t].hi));
  chk('every theme gets its own highlight', uniqHi.size, F.THEMES.length);

  // ---- the cached cell must be invalidated when the theme changes
  F.setTheme(F.THEMES[0]); F.readPlate(); F.buildBoardArt();
  chk('the board was cached', !!F.boardArt, true);
  F.setTheme(F.THEMES[1]); F.readPlate();
  chk('changing theme drops the cached board', F.boardArt, null);

  // ---- and when the board is resized, or it is blitted at the wrong resolution
  F.buildBoardArt();
  const w1 = F.boardArt.width;
  F.ROWS = F.ROWS_BASE; F.layout();
  chk('layout drops the cached board', F.boardArt, null);
  F.buildBoardArt();
  chk('the cached board matches the board size',
      { w: F.boardArt.width, h: F.boardArt.height },
      { w: Math.max(1, Math.round(F.boardPx * F.dpr)),
        h: Math.max(1, Math.round(F.boardH * F.dpr)) });
  chk('the cached board has real pixels', w1 > 4, true);
  // ONE image for the whole plate, not one per cell: that is the difference between a blit
  // per frame and sixty-four of them
  chk('the cache covers the whole plate, not a single cell',
      F.boardArt.width >= Math.round(F.cell * F.dpr * 2), true);

  // ---- the thing that actually cost a day: how many blits a frame costs.
  // A cached CELL looks identical on screen and is 64x the draw calls; under software
  // rasterisation that took the item suite from 59s to not finishing in 25 minutes, with no
  // error and no failing assertion anywhere. Count the calls instead of trusting the picture.
  F.setTheme(F.THEMES[0]); F.readPlate(); F.layout();
  F.start('rush');
  const proto = Object.getPrototypeOf(F.ctx || document.createElement('canvas').getContext('2d'));
  const realDraw = proto.drawImage;
  let blits = 0;
  proto.drawImage = function (...a) { blits++; return realDraw.apply(this, a); };
  F.dirty = true; F.draw();
  proto.drawImage = realDraw;
  // the empty plate must cost ONE blit, whatever the board size. Fruit on the board add their
  // own sprite blits, so the bar is generous -- a per-cell plate would be 64+ on its own.
  chk('the empty plate costs one blit, not one per cell', blits < F.ROWS * F.COLS / 2, true);

  document.title = 'RESULT ' + JSON.stringify({ fails, seen, blits });
 } catch (e) { document.title = 'THREW ' + (e && e.message) + ' | ' + String(e && e.stack || '').slice(0, 300); }
}, 700));
</script>"""

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open(_PAGE,'w',encoding='utf-8').write(
    open('index.html',encoding='utf-8').read().replace('</body>', TEST + '</body>'))
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless','--disable-gpu','--no-first-run','--window-size=430,932',
        '--virtual-time-budget=30000','--dump-dom',f'http://localhost:8899/{_PAGE}?test=1'],
        capture_output=True, text=True, timeout=180).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
for t, v in d.get('seen', {}).items():
    print(f"  {t:<6} 바닥 {v['cell']:<18} 위{v['lo']:<18} 아래{v['hi']}")
print(f"  빈 판 1프레임 drawImage 호출: {d.get('blits')}")
print(f"plate: {len(d['fails'])} fail")
for f in d['fails'][:8]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
