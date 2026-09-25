#!/usr/bin/env python3
"""The browser must not repaint our themes for us.

With the OS in dark mode, Chrome's Auto Dark Theme decides a page that never declares
`color-scheme` does not support dark mode and rewrites its palette itself. Measured: the
과일 노점 theme came out olive instead of cream and the goal line was nearly unreadable --
on a build whose own four themes were working perfectly. Nothing in the suite could see it,
because every other check runs a browser in its default scheme.

Renders each theme twice -- once normally, once under --enable-features=WebContentsForceDark --
and requires the pixels to match. The board is emptied and the preview pinned first, so the two runs are comparable; otherwise
the random fruit differ and the diff is dominated by content rather than by colour.
"""
import subprocess, os, re, sys, json, zlib, struct

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
W, H = 900, 720
THEMES = ['dark', 'stall', 'shore', 'snow']
TOL = 6          # JPEG-free PNGs: anything above this is a real repaint, not noise


def load(p):
    d = open(p, 'rb').read(); pos = 8; idat = b''; w = h = ct = 0
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos + 4])[0]; typ = d[pos + 4:pos + 8]
        if typ == b'IHDR': w, h, _bd, ct = struct.unpack('>IIBB', d[pos + 8:pos + 18])
        elif typ == b'IDAT': idat += d[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    raw = zlib.decompress(idat); ch = 4 if ct == 6 else 3; stride = w * ch + 1
    rows = []; prev = bytearray(w * ch)
    for y in range(h):
        f = raw[y * stride]; line = bytearray(raw[y * stride + 1:(y + 1) * stride])
        for x in range(len(line)):
            a = line[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p2 = a + b - c; pa = abs(p2 - a); pb = abs(p2 - b); pc = abs(p2 - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        prev = line; rows.append(bytes(line))
    return w, h, ch, rows


def shoot(theme, out, extra):
    host = ('<!doctype html><meta charset=utf-8><body style="margin:0">\n<script>\n'
            f'try {{ localStorage.setItem("fs_theme", {json.dumps(theme)}); }} catch (e) {{}}\n'
            'const f=document.createElement("iframe");\n'
            f'f.style.cssText="width:{W}px;height:{H}px;border:0;position:absolute;left:0;top:0";\n'
            'f.src="index.html?test=1";document.body.appendChild(f);\n'
            'f.onload=()=>setTimeout(()=>{\n'
            '  const D=f.contentDocument,F=f.contentWindow.__fs;\n'
            '  D.getElementById("btn-challenge").click();\n'
            '  setTimeout(()=>{\n'
            '    for(let r=0;r<F.ROWS;r++)for(let c=0;c<F.COLS;c++){F.grid[r][c]=-1;'
            'F.special[r][c]=null;F.hp[r][c]=0;}\n'
            '    F.nextColor=0; F.nextColor2=3; F.streak=0; F.drawNextPreview();\n'
            '    F.coins=1450; F.dirty=true; F.updateHUD(); F.draw();\n'
            '    document.title="READY";\n'
            '  },500);\n'
            '},400);\n</script>')
    page = f'_fd{os.getpid()}.html'
    open(page, 'w', encoding='utf-8').write(host)
    try:
        subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-first-run',
                        '--hide-scrollbars', f'--window-size={W},{H}',
                        '--virtual-time-budget=9000'] + extra +
                       [f'--screenshot={out}', f'http://localhost:8899/{page}'],
                       capture_output=True, timeout=180)
    finally:
        os.remove(page)
    return os.path.exists(out)


os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
os.makedirs('/tmp/shots', exist_ok=True)
fails = []
for t in THEMES:
    a_p, b_p = f'/tmp/shots/fd-{t}-normal.png', f'/tmp/shots/fd-{t}-dark.png'
    if not shoot(t, a_p, []) or not shoot(t, b_p, ['--enable-features=WebContentsForceDark']):
        fails.append(f'{t}: 스크린샷 실패'); continue
    A, B = load(a_p), load(b_p)
    if A[0] != B[0] or A[1] != B[1]:
        fails.append(f'{t}: 크기 불일치'); continue
    w, h, ch, ra = A; _, _, _, rb = B
    worst = 0; worst_at = None; off = 0
    for y in range(0, h, 7):
        for x in range(0, w, 7):
            i = x * ch
            d = max(abs(ra[y][i + k] - rb[y][i + k]) for k in range(3))
            if d > TOL:
                off += 1
                if d > worst: worst, worst_at = d, (x, y)
    total = len(range(0, h, 7)) * len(range(0, w, 7))
    pct = off * 100.0 / total
    print(f"  {t:<6} 다른 픽셀 {off}/{total} ({pct:.1f}%)  최대 차이 {worst}")
    # a handful of sampled points can differ on an anti-aliased edge; a repaint moves everything
    if pct > 2.0:
        fails.append(f'{t}: 브라우저 다크모드가 화면을 다시 칠함 '
                     f'({pct:.1f}% 픽셀, 최대 {worst} @ {worst_at})')

print(f"forcedark: {len(fails)} fail")
for f in fails[:6]: print('   ', f)
print('PASS' if not fails else 'FAIL')
sys.exit(1 if fails else 0)
