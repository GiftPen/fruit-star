#!/usr/bin/env python3
"""A long streak has to keep paying off, in sound and on screen.

The combo accent climbed the pentatonic scale and then STOPPED at its last rung: streak 6 and
streak 20 made exactly the same noise. At vol 0.07 over 0.07s it was buried under the pops
anyway. The badge popped by the same 1.35 on the second success as on the twentieth. And the
multiplier itself caps at 5, so from streak 6 on NOTHING changed -- number, sound or picture.
A tester said as much: the cluster tiers read, the combo felt flat.

Checks the accent keeps rising past the scale (in octaves, and capped so it cannot shriek),
that it thickens at its thresholds, and that the badge's pop and heat grow with the run.
Thresholds are read from the game, so retuning them is not a failure."""
import subprocess, os, re, json, sys
_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'   # per-process: two runs of the suite were deleting each other's page

TEST = """<script>
window.addEventListener('load', () => setTimeout(async () => {
 try {
  const F = window.__fs; const fails = [];
  const chk = (c, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want))
                                    fails.push({ case: c, got, want }); };
  const S = F.SFX;
  S.unlock(); S.resume();
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // ---- the accent must not flatten at the end of the scale
  const L = S.PENTA_LEN;
  chk('the scale has rungs to climb', L > 1, true);
  const atEnd = S.comboHz(L - 1), past = S.comboHz(L);
  chk('past the last rung it keeps climbing', past > atEnd, true);
  chk('a long streak is not the same note as a medium one',
      S.comboHz(L + 2) !== S.comboHz(2), true);

  // ...but it has to stop somewhere, or a 40-streak is a shriek
  const capped = S.comboHz(L * (S.COMBO_OCT_CAP + 1));
  chk('the climb is capped', S.comboHz(L * (S.COMBO_OCT_CAP + 4)), capped);
  chk('and the cap is still musical (under 4kHz)', capped < 4000, true);

  // ---- the accent thickens: more voices as the streak grows
  const voices = n => {
    const seen = [];
    const style = { play: f => seen.push(f) };
    // count tone() calls by wrapping the shared oscillator entry point
    return seen;
  };
  // count by observing how many oscillators the accent starts
  const countTones = n => {
    const ac = S.ctx || null;
    let made = 0;
    const realNow = performance.now;
    // OscillatorNode is created per tone(); patch the constructor the context hands out
    const proto = Object.getPrototypeOf(new (window.AudioContext || window.webkitAudioContext)());
    // Count what the ENGINE calls a voice, not just oscillators: a layer can be filtered
    // noise, and the shipped accent uses one for its body. Counting only OscillatorNode
    // reported "no new voice" for a threshold that plainly adds one.
    const real = proto.createOscillator, realBuf = proto.createBufferSource;
    proto.createOscillator = function (...a) { made++; return real.apply(this, a); };
    proto.createBufferSource = function (...a) { made++; return realBuf.apply(this, a); };
    S.play('combo', n);
    proto.createOscillator = real; proto.createBufferSource = realBuf;
    return made;
  };
  // Against a named sounding style, not whatever is shipped: the accent is switched off by
  // default right now, and "a silent style gains no voice at the chord" is not a bug.
  const wasStyle0 = S.comboStyle;
  S.setComboStyle('body');
  const vBase = countTones(0);
  const vChord = countTones(S.COMBO_CHORD);
  const vFlour = countTones(S.COMBO_FLOURISH);
  S.setComboStyle(wasStyle0);
  chk('the plain accent makes a sound at all', vBase >= 1, true);
  chk('it gains a voice at the chord threshold', vChord > vBase, true);
  chk('and another at the flourish threshold', vFlour > vChord, true);

  // ---- the badge grows with the streak, and heats past the multiplier cap
  F.start('rush');
  const badge = document.getElementById('streak-badge');
  const read = n => {
    F.streak = n; F.updateStreakBadge();
    return { hot: badge.classList.contains('hot'),
             heat: parseFloat(badge.style.getPropertyValue('--heat') || '0'),
             on: badge.classList.contains('on') };
  };
  const lo = read(1), mid = read(F.COMBO_HEAT_FROM), hi = read(F.COMBO_HEAT_FULL * 2);
  chk('a short streak does not glow', lo.hot, false);
  chk('it glows from the threshold', mid.hot, true);
  chk('and it stays glowing', hi.hot, true);
  chk('the glow grows with the streak', hi.heat > mid.heat, true);
  chk('the glow is clamped', hi.heat <= 1, true);

  // ...and none of it survives the streak being broken
  const off = read(0);
  chk('breaking the streak clears the badge', [off.on, off.hot], [false, false]);

  // ---- the accent has to be an instrument, not a beeper ----
  // It was ONE naked triangle oscillator with an instant attack. Watch the real audio graph
  // rather than the style table: reading the table back proves the code was written, not that
  // anything reaches the speaker.
  const osc = AudioContext.prototype.createOscillator;
  const heard = [];
  AudioContext.prototype.createOscillator = function () {
    const o = osc.call(this);
    const sv = o.frequency.setValueAtTime.bind(o.frequency);
    o.frequency.setValueAtTime = (v, t) => { heard.push(Math.round(v * 100) / 100); return sv(v, t); };
    return o;
  };
  const voicesOf = async (style, n) => {
    await sleep(600);                 // let the previous style's voices die: the accent budget
    S.setComboStyle(style); heard.length = 0;   // is 14 and these ring for up to 0.46s
    S.play('combo', n);
    return heard.slice();
  };
  const was = S.comboStyle;
  const SOUNDING = S.COMBO_KEYS.filter(k => k !== 'none');
  chk('there is a silent option and it really is silent',
      (await voicesOf('none', 4)).length, 0);
  for (const k of SOUNDING) {
    const v = await voicesOf(k, 1);
    chk(k + ': the accent is audible at all', v.length > 0, true);
    // Octave-related to the streak note, not equal to it: the shipped accent plays two
    // octaves DOWN so it sits under the pops instead of over them.
    const oct = Math.log2(Math.min(...v) / S.comboHz(1));
    chk(k + ': it is the streak note, in some octave', Math.abs(oct - Math.round(oct)) < 0.02, true);
  }
  // the default must not be the flat one, or nothing changed for anybody
  chk('the shipped default is not the old beeper', was === 'old', false);
  // "콤보는 소리가 너무 튀어요 혼자 따로 노는 느낌" -- it was climbing to 2.2kHz over pops
  // that own the mid and high. Played with, the axis turned out not to want a voice at all,
  // so the shipped setting is silence; 묵직 is what it would come back as, and it has to
  // stay under what it accents.
  chk('the shipped accent is silent for now', was, 'none');
  chk('묵직 sits below the pops', Math.min(...(await voicesOf('body', 4))) < S.popHz(0, 0), true);
  const rich = await voicesOf('bell', 1), flat = await voicesOf('old', 1);
  chk('종 has partials the old beeper did not', rich.length > flat.length, true);
  // Detuning is 종's technique for sounding struck, not a law every style must obey -- the
  // shipped accent earns its place by sitting low instead. Check it where it IS the point.
  const bell = await voicesOf('bell', 1);
  chk('종 shimmers: two voices a few cents apart',
      bell.some(a => bell.some(b => a !== b && Math.abs(a / b - 1) < 0.02)), true);
  // and the whole point of the ladder: a later streak is a higher note, in every style
  for (const k of SOUNDING) {
    const hi = await voicesOf(k, 4), lo = await voicesOf(k, 1);
    chk(k + ': a longer streak is a higher note', Math.min(...hi) > Math.min(...lo), true);
  }
  AudioContext.prototype.createOscillator = osc;
  S.setComboStyle(was);

  document.title = 'RESULT ' + JSON.stringify({ fails,
    hz: [0, 1, L - 1, L, L + 2, L * 5].map(n => Math.round(S.comboHz(n))),
    voices: [vBase, vChord, vFlour] });
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
        '--virtual-time-budget=30000','--dump-dom',f'http://localhost:8899/{_PAGE}?test=1'],
        capture_output=True, text=True, timeout=180).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
print(f"  연속별 음높이 Hz: {d.get('hz')}")
print(f"  액센트 목소리 수: {d.get('voices')}")
print(f"combo: {len(d['fails'])} fail")
for f in d['fails'][:8]: print('   ', json.dumps(f, ensure_ascii=False))
print('PASS' if not d['fails'] else 'FAIL')
sys.exit(1 if d['fails'] else 0)
