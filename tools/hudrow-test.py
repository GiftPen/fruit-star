#!/usr/bin/env python3
"""The arcade HUD at every phone width, with the widest numbers the game can reach.

Reported from the phone: the chip row had wrapped and the purse was sitting alone on a
second line. Measured, it was not a small-screen problem at all -- five chips wanted 372px
and the row had 284 at 320px and 360 at 360px, so it wrapped on EVERY common phone up to
390 and only fitted on a 412px Pixel. It had never been measured: hud-fit covers 스타 러시
and hides #stats on its way in, so the arcade row was untested at any width.

Two fixes, both checked here. 확률 is a button and goes back up top with 일시정지, where
arcade has nothing else -- that alone is 74px off the strip. And under 380px the strip
scales down together, which is the knob to reach for when another chip is added.

Also pins the three faults reported before this one, in the same row:
  - the ➕ chip sat 4px low with a green glow: the global `button` rule leaking into a chip
    built on a <button>, patched twice elsewhere before .chip-btn cut it off at the source
  - "⚠️ 위험!" overlapped the purse at three digits. A label pinned into a row it shares with
    growing numbers always collides eventually; the plate takes a red rim instead, which has
    nothing to lay out and so cannot collide with anything.
"""
import subprocess, os, re, sys, json

_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'
# 320 is the floor a phone browser reports; 360 is a Galaxy S24, 390 an iPhone 12-15,
# 412 a Pixel. 430 is the largest phone. Wrapping was happening at every one of these but 412.
WIDTHS = [320, 360, 375, 390, 412, 430]
MIN_FONT = 11          # below this the strip stops being readable at arm's length

HOST = """<!doctype html><meta charset=utf-8><body style="margin:0;background:#000">
<script>
const WIDTHS = %s, MIN_FONT = %s;
const fails = [];
const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                  fails.push({ case: c, got, want }); };
const open1 = w => new Promise(res => {
  const f = document.createElement('iframe');
  f.style.cssText = 'width:' + w + 'px;height:820px;border:0;position:absolute;left:0;top:0';
  f.src = 'index.html?test=1';
  f.onload = () => setTimeout(() => res(f), 550);
  document.body.appendChild(f);
});
// the widest the HUD can ever be: difficulty capped so MAX shows, four digits of touches,
// four of coins, and a score in the billions
const worstCase = F => { F.start('arcade'); F.score = 1626000000; F.best = 1626000000;
                         F.coins = 9999; F.touchCount = 9999;
                         // the purse ANIMATES up to its value, so for the first moments its
                         // chip holds one digit, not four. Measuring then is measuring the
                         // easy case -- which is how 360px/en passed while it overflowed.
                         F.coinsShown = 9999;
                         F.updateHUD(); };

(async () => {
 try {
  const CHIPS = ['st-lvl-chip', 'st-touch-chip', 'st-spawn-chip', 'st-coin'];

  for (const w of WIDTHS) {
    const f = await open1(w);
    const D = f.contentDocument, W = f.contentWindow, F = W.__fs;
    worstCase(F);
    await new Promise(r => setTimeout(r, 250));
    const R = id => D.getElementById(id).getBoundingClientRect();

    // The game ships in four languages and the labels are not the same length -- English
    // "Touches" and "Per turn" are far longer than 터치 and 매턴. Checking only Korean means
    // the strip can be one line here and two for everyone else, which is the same bug again.
    // Switching language in place is cheap; a second page per language is not.
    for (const lang of ['ko', 'en', 'ja', 'zh']) {
      F.setLang(lang); F.coinsShown = F.coins; F.updateHUD();
      const t = CHIPS.map(id => Math.round(R(id).top));
      chk(w + 'px/' + lang + ': the chip strip is one line', [...new Set(t)].length, 1);
      chk(w + 'px/' + lang + ': the page fits the screen',
          D.documentElement.scrollWidth <= w, true);
    }
    F.setLang('ko'); F.coinsShown = F.coins; F.updateHUD();
    await new Promise(r => setTimeout(r, 120));

    const tops = CHIPS.map(id => Math.round(R(id).top));
    chk(w + 'px: the chip strip is one line', [...new Set(tops)].length, 1);

    // The check that matters most, and the one that was missing. Chasing the chip row on its
    // own, 확률 was moved up top -- which fixed the strip and pushed #top's min-content from
    // 312 to 368, so on a 320px phone the whole UI, board included, hung 24px off each side.
    // A per-element scan did not see it: every element was inside a body that was itself too
    // wide. Ask the page.
    chk(w + 'px: the page fits the screen', D.documentElement.scrollWidth <= w, true);
    // ...and say WHICH element refuses to shrink, or the line above is a riddle
    const stuck = [];
    for (const e of D.querySelectorAll('body > *')) {
      if (W.getComputedStyle(e).display === 'none') continue;
      const p = e.cloneNode(true);
      p.style.cssText += ';position:absolute;left:-9999px;top:0;width:min-content;max-width:none';
      D.body.appendChild(p);
      const m = p.getBoundingClientRect().width; p.remove();
      if (m > w + 0.5) stuck.push((e.id ? '#' + e.id : e.tagName) + ' needs ' + Math.round(m));
    }
    chk(w + 'px: nothing refuses to shrink to the screen', stuck, []);

    const out = [];
    for (const e of D.querySelectorAll('#top *, #stats > *')) {
      const b = e.getBoundingClientRect();
      if (b.width && (b.right > w + 0.5 || b.left < -0.5))
        out.push((e.id || e.className || e.tagName) + '@' + Math.round(b.right));
    }
    chk(w + 'px: nothing hangs off the screen', [...new Set(out)], []);

    // the three blocks of the top row must not run into each other
    const left = D.querySelector('.top-left').getBoundingClientRect();
    const score = R('arcade-box'), next = R('next-wrap');
    chk(w + 'px: the buttons clear the score', left.right <= score.left + 0.5, true);
    chk(w + 'px: the score clears NEXT', score.right <= next.left + 0.5, true);

    // THE REPORT THAT PROMPTED THE REBUILD: "숫자 커지면 버튼 꿈틀거리는것도 별로". Four
    // pills sized themselves to their text, so every extra digit re-laid the row under the
    // thumb -- the purse jumped a whole chip width the first time coins passed 999. Fixed
    // cells cannot be moved by what is written in them; this is that promise, measured.
    const geom = () => CHIPS.map(id => { const b = R(id);
      return [Math.round(b.left), Math.round(b.width)]; });
    F.coins = 0; F.coinsShown = 0; F.touchCount = 0; F.score = 0; F.updateHUD();
    const small = geom();
    F.coins = 9999; F.coinsShown = 9999; F.touchCount = 9999; F.score = 1626000000; F.updateHUD();
    const big = geom();
    chk(w + 'px: the cells do not move when the numbers grow', small, big);
    // ...because they are fixed shares of the bar, not shrink-to-fit boxes
    chk(w + 'px: the cells are equal shares',
        [...new Set(big.map(g => g[1]))].length, 1);

    // 확률 only ever got its row layout from `#stats #info-btn`, so moving it back up top
    // dropped it to display:block and stacked its fruit above its word -- at every width.
    const ic = D.getElementById('odds-ic').getBoundingClientRect();
    const wd = D.querySelector('.odds-word').getBoundingClientRect();
    chk(w + 'px: 확률 keeps its fruit and its word on one line',
        Math.abs(ic.top - wd.top) < 3, true);
    const ob = D.getElementById('info-btn').getBoundingClientRect();
    const pb = D.getElementById('pause-btn').getBoundingClientRect();
    chk(w + 'px: 확률 lines up with 일시정지',
        [Math.round(ob.top), Math.round(ob.height)], [Math.round(pb.top), Math.round(pb.height)]);

    // scaling the strip must not scale it into illegibility
    const fonts = CHIPS.map(id => parseFloat(W.getComputedStyle(D.getElementById(id)).fontSize));
    chk(w + 'px: the strip stays readable', fonts.filter(x => x < MIN_FONT), []);
    chk(w + 'px: the chips keep a tappable height',
        CHIPS.filter(id => R(id).height < 24), []);
    f.remove();
  }

  // ---- everything below is at one width; it is about the row, not about fitting ----
  const f = await open1(390);
  const D = f.contentDocument, W = f.contentWindow, F = W.__fs;
  worstCase(F);
  await new Promise(r => setTimeout(r, 250));

  // 확률 is a button. Putting it on the chip strip is what made the strip too wide, so this
  // is the fix itself: it belongs with 일시정지, and arcade's top-left has room for it.
  const odds = D.getElementById('info-btn');
  chk('확률 sits with the buttons, not on the chip strip',
      !!odds.closest('.top-left'), true);
  chk('...and not inside the strip', odds.closest('#stats'), null);

  // one line, one height -- the ➕ chip used to sit 4px low
  const box = CHIPS.map(id => D.getElementById(id).getBoundingClientRect());
  chk('the chips share a top', [...new Set(box.map(b => Math.round(b.top)))].length, 1);
  chk('the chips share a height', [...new Set(box.map(b => Math.round(b.height)))].length, 1);

  // the global `button` rule must not reach a chip built on a <button>
  const cs = W.getComputedStyle(D.getElementById('st-spawn-chip'));
  chk('a chip that is a button has no button margin', cs.marginTop, '0px');
  chk('...and no button shadow', cs.boxShadow, 'none');

  // the danger label is gone for good: a word in this row collides the moment a number grows
  chk('no danger label survives anywhere',
      [...D.querySelectorAll('[id^=danger-label]')].length, 0);

  // ...and what replaced it has to keep the frame alive, or the rim freezes mid-pulse
  const proto = W.CanvasRenderingContext2D.prototype, real = proto.drawImage;
  let blits = 0;
  proto.drawImage = function (...a) { blits++; return real.apply(this, a); };
  F.resetEffects();
  F.wasDanger = false;
  let idle = -1;
  for (let i = 0; i < 400; i++) { F.dirty = false; blits = 0; F.draw();
                                  if (blits === 0) { idle = 0; break; } }
  F.wasDanger = true; F.dirty = false; blits = 0; F.draw();
  const danger = blits;
  proto.drawImage = real;
  chk('the board does settle, so this comparison means something', idle, 0);
  chk('a nearly-full board keeps drawing so the rim can breathe', danger > 0, true);

  document.title = 'RESULT ' + JSON.stringify({ fails });
 } catch (e) { document.title = 'THREW ' + (e && e.message) + '|' + String(e && e.stack || '').slice(0, 300); }
})();
</script>""" % (json.dumps(WIDTHS), MIN_FONT)

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open(_PAGE, 'w', encoding='utf-8').write(HOST)
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless', '--disable-gpu', '--no-first-run', '--window-size=500,900',
        '--virtual-time-budget=60000', '--dump-dom', f'http://localhost:8899/{_PAGE}'],
        capture_output=True, text=True, timeout=300).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"hudrow: {len(WIDTHS)}개 폭 · {len(d['fails'])} fail")
for f in d['fails'][:12]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
