#!/usr/bin/env python3
"""Screenshots one screen per theme at phone width. The window size does not set innerWidth
in headless Chrome (it stays 500), so the game is loaded in a 390px iframe and the window is
sized to match it -- what comes out is what a phone shows, not a stretched desktop page."""
import subprocess, sys, os, json

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
import os as _os
W = int(_os.environ.get('SHOT_W', 390)); H = int(_os.environ.get('SHOT_H', 844))
SCREENS = {
  # name: what to run inside the frame once it has loaded
  'menu':  "",
  'game':  "D.getElementById('btn-challenge').click();",
  'arcade':"D.getElementById('btn-arcade').click();",
  # one fruit of each colour on the diagonal, and the same board empty, so the two can be
  # diffed to get each fruit's real ink on screen
  'diag':  ("D.getElementById('btn-challenge').click();"
            " for(let r=0;r<F.ROWS;r++)for(let c=0;c<F.COLS;c++){F.grid[r][c]=-1;"
            " F.special[r][c]=null;F.hp[r][c]=0;F.appear[r][c]=0;}"
            " for(let i=0;i<7;i++) F.grid[i][i]=i; F.dirty=true; F.draw();"),
  'diag0': ("D.getElementById('btn-challenge').click();"
            " for(let r=0;r<F.ROWS;r++)for(let c=0;c<F.COLS;c++){F.grid[r][c]=-1;"
            " F.special[r][c]=null;F.hp[r][c]=0;F.appear[r][c]=0;}"
            " F.dirty=true; F.draw();"),
  # the trait picker, with the seedling family on the shelf
  'traits': ("D.getElementById('btn-challenge').click(); F.openTraits();"
             " F.traitOffers=['cherry_seed','orange_seed','kiwi_seedling',"
             " 'lemon_seed','grape_seed','peach_seed']; F.renderTraits();"),
  'arcade2': ("D.getElementById('btn-arcade').click(); F.score = 8400; F.coins = 120;"
              " F.streak = 4; F.updateHUD();"),
  'met':   "D.getElementById('btn-challenge').click(); F.score = 1840; F.stageScore = 1840; F.updateHUD();",
  'shop':  "D.getElementById('btn-challenge').click(); F.coins = 40; F.openShop();",
  'set':   "D.getElementById('btn-settings').click();",
  # the +1 drawer: it hangs off a HUD chip, and a clipped/mispositioned drawer is invisible
  # to every test that only reads classes
  # the desktop rails with a live streak and coins, which is what they look like in play
  'rails': ("D.getElementById('btn-challenge').click(); F.coins = 1450; F.streak = 6;"
            " F.score = 54608; F.stage = 10; F.updateHUD();"),
  'spawn': ("D.getElementById('btn-challenge').click(); F.coins = 120;"
            " F.updateHUD(); D.getElementById('rs-spawn-chip').click();"),
  # the odds popup's stat table, scrolled to the item thresholds
  'odds':  ("D.getElementById('btn-challenge').click(); D.getElementById('info-btn').click();"
            " setTimeout(() => { const b = D.getElementById('info-body');"
            " b.scrollTop = b.scrollHeight; }, 200);"),
}

def shot(theme, screen, out):
    host = f"""<!doctype html><meta charset=utf-8><body style="margin:0;background:#000">
<script>
try {{ localStorage.setItem('fs_theme', {json.dumps(theme)}); }} catch (e) {{}}
const f = document.createElement('iframe');
f.style.cssText = 'width:{W}px;height:{H}px;border:0;position:absolute;left:0;top:0';
f.src = 'index.html?test=1'; document.body.appendChild(f);
f.onload = () => setTimeout(() => {{
  const D = f.contentDocument, F = f.contentWindow.__fs;
  {SCREENS[screen]}
  setTimeout(() => {{ document.title = 'READY'; }}, 500);
}}, 400);
</script>"""
    open('_shot.html','w',encoding='utf-8').write(host)
    try:
        subprocess.run([CHROME,'--headless','--disable-gpu','--no-first-run','--hide-scrollbars',
            f'--window-size={W},{H}','--virtual-time-budget=6000',
            f'--screenshot={out}','http://localhost:8899/_shot.html'],
            capture_output=True, timeout=120)
    finally:
        os.remove('_shot.html')
    print(out, os.path.getsize(out), 'bytes')

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
    themes = sys.argv[1].split(',') if len(sys.argv) > 1 else ['dark','stall','shore','snow']
    screens = sys.argv[2].split(',') if len(sys.argv) > 2 else ['menu']
    os.makedirs('/tmp/shots', exist_ok=True)
    for t in themes:
        for s in screens:
            shot(t, s, f'/tmp/shots/{s}-{t}.png')
