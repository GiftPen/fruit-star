#!/usr/bin/env python3
"""Regenerates 난이도-곡선.md from the game itself.

Run:  python3 -m http.server 8899 &   then   python3 tools/gen-curves.py

Both curves are read by calling MODES through the ?test=1 hook, not by parsing the source
and not by hand. A difficulty table copied into a document is wrong the first time anyone
retunes a knob, and wrong quietly -- the document still reads as authoritative.
"""
import subprocess, os, re, json, datetime, sys

_PAGE = f'_{os.path.basename(__file__)[:-3]}-{os.getpid()}.html'
STAGES_SHOWN = 36          # 12 rounds; the design ceiling is 10 and the file says so

HOST = """<!doctype html><meta charset=utf-8><body style="margin:0"><script>
(async () => {
 try {
  const f = document.createElement('iframe');
  f.style.cssText = 'width:390px;height:800px;border:0;position:absolute;left:0;top:0';
  f.src = 'index.html?test=1'; document.body.appendChild(f);
  await new Promise(r => { f.onload = r; });
  await new Promise(r => setTimeout(r, 500));
  const F = f.contentWindow.__fs, D = f.contentDocument;
  const rush = []; let cum = 0;
  for (let st = 1; st <= %s; st++) {
    const q = F.MODES.rush.quota(st); cum += q;
    rush.push({ st, label: F.stageLabel(st), quota: q, cum });
  }
  D.getElementById('btn-arcade').click();
  await new Promise(r => setTimeout(r, 200));
  const arc = [];
  for (let lv = 1; lv <= F.MAX_LEVEL; lv++) {
    const m = lv - 1, A = F.MODES.arcade;
    arc.push({ lv, at: F.LEVEL_AT[m], colors: A.colors(m), spawns: A.spawns(m),
               on: A.crackerOn(m), gap: A.crackerGap(m), coin: A.coinFruit(m),
               gain: F.levelGain(m) });
  }
  document.title = 'RESULT ' + JSON.stringify({ rush, arc,
    perRound: F.STAGES_PER_ROUND, touches: F.MODES.rush.touches,
    rushCoin: F.MODES.rush.coinFruit(0), maxLv: F.MAX_LEVEL,
    startBuds: F.MODES.arcade.startBuds, rushBuds: F.MODES.rush.startBuds,
    rushSpawn: F.MODES.rush.spawns(0), rushColors: F.MODES.rush.colors(0),
    handSet: F.EARLY_QUOTA ? F.EARLY_QUOTA.length : 0 });
 } catch (e) { document.title = 'THREW ' + e.message; }
})();
</script>""" % STAGES_SHOWN

os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
open(_PAGE, 'w', encoding='utf-8').write(HOST)
try:
    out = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--headless', '--disable-gpu', '--no-first-run', '--window-size=500,900',
        '--virtual-time-budget=30000', '--dump-dom', f'http://localhost:8899/{_PAGE}'],
        capture_output=True, text=True, timeout=240).stdout
finally:
    os.remove(_PAGE)

m = re.search(r'RESULT (\{.*\})</title>', out, re.S)
if not m:
    t = re.search(r'<title>([^<]*)</title>', out)
    print('NO RESULT', t.group(1) if t else '?'); sys.exit(1)
d = json.loads(m.group(1))
PER, fm = d['perRound'], lambda n: f"{n:,}"

# the score gaps, described from the table rather than written out next to it
steps = [d['arc'][i]['at'] - d['arc'][i-1]['at'] for i in range(1, len(d['arc']))]
runs = []
for s in steps:
    if runs and runs[-1][0] == s: runs[-1][1] += 1
    else: runs.append([s, 1])
step_text = ' → '.join(f"{fm(s)}씩 {n}번" for s, n in runs)

L = []
A = L.append
A("# 난이도 곡선 — 스타 러시 목표 점수 · 아케이드 레벨")
A("")
A("> **이 파일은 손으로 고치지 마세요.** `python3 tools/gen-curves.py` 로 게임에서 직접")
A("> 뽑습니다. 수치를 바꾼 뒤 다시 돌리면 됩니다.")
A("")
A(f"생성: {datetime.date.today()} · 스타 러시 라운드당 {PER}스테이지 · 아케이드 {d['maxLv']}단계")
A("")
A("---")
A("")
A("## 스타 러시 — 라운드별 목표 점수")
A("")
A(f"한 스테이지는 **{d['touches']}터치**로 목표를 넘기면 통과입니다. 목표를 넘겨도 스테이지는 끝나지")
A("않습니다 — 남은 터치는 보너스 점수가 되고, 판이 차오르는 것이 그 대가입니다.")
A("")
A(f"라운드가 끝날 때마다({PER}스테이지마다) 특성을 하나 고릅니다.")
A("")
A("| 라운드 | -1 | -2 | -3 | 라운드 합 | 누적 |")
A("|---:|---:|---:|---:|---:|---:|")
rows = d['rush']
for i in range(0, len(rows) - PER + 1, PER):
    g = rows[i:i+PER]
    A(f"| **{i//PER + 1}** | " + " | ".join(fm(x['quota']) for x in g) +
      f" | {fm(sum(x['quota'] for x in g))} | {fm(g[-1]['cum'])} |")
A("")
if d['handSet']:
    A(f"처음 {d['handSet']}스테이지는 **손으로 정한 표**입니다 — 1,000 / 1,250 / 1,500 처럼 읽히는")
    A("숫자라야 목표가 목표로 보입니다. 그 뒤부터는 곡선이 이어받습니다.")
    A("")
A("**설계 상한은 라운드 10입니다.** 그 뒤 수치도 계산되지만 거기까지 가도록 만들어진 것은 아닙니다.")
A("")
A("---")
A("")
A("## 아케이드 — 레벨별 도달 점수")
A("")
A("아케이드에는 목표가 없습니다. 점수가 오르면 난이도가 오르고, 판이 가득 차면 끝납니다.")
A("**각 레벨은 정확히 한 가지만 바꿉니다** — `크래커 → 과일 색 → 매 턴 과일`이 한 바퀴입니다.")
A("")
A("| Lv | 도달 점수 | 과일 색 | 매 턴 과일 | 크래커 | 코인 과일 | 이 레벨에서 바뀌는 것 |")
A("|---:|---:|---:|---:|---|---:|---|")
for a in d['arc']:
    ck = f"{a['gap']}터치마다" if a['on'] else "—"
    A(f"| **{a['lv']}** | {fm(a['at'])} | {a['colors']} | {a['spawns']} | {ck} | "
      f"{round(a['coin']*100)}% | {a['gain'] or '시작'} |")
A("")
A("### 읽는 법")
A("")
A(f"- **과일 색** — {d['arc'][0]['colors']}종에서 시작해 {d['arc'][-1]['colors']}종까지. 8번째 과일(멜론)이")
A("  없으면 그 칸은 바꿀 것이 없어 빈 레벨이 됩니다.")
A("- **크래커** — 아이템으로만 치워집니다. 주기가 좁아지는 것이 이 사다리에서 가장 무거운 압박이라,")
A("  1터치마다는 마지막 레벨에만 옵니다.")
A(f"- **코인 과일** — 유일하게 플레이어 쪽으로 돌아오는 값입니다. "
  f"{round(d['arc'][0]['coin']*100)}%에서 {round(d['arc'][-1]['coin']*100)}%까지, 레벨당 +2%.")
A("  깊이 갈수록 아이템을 더 살 수 있게 해주는 완충입니다.")
A(f"- 점수 간격: {step_text}. 초반은 게임을 가르칠 만큼 빨리 오고, 후반은 도달이 성과가 되도록.")
A("")
A("### 두 모드의 차이")
A("")
A("| | 스타 러시 | 아케이드 |")
A("|---|---|---|")
A(f"| 시작 과일 종류 | {d['rushColors']}종 (처음부터) | {d['arc'][0]['colors']} → {d['arc'][-1]['colors']}종 |")
A(f"| 매 턴 과일 | {d['rushSpawn']}개 (유물로 증가) | {d['arc'][0]['spawns']} → {d['arc'][-1]['spawns']}개 |")
A(f"| 시작 과일 수 | {d['rushBuds']}개 | {d['startBuds']}개 |")
A(f"| 코인 과일 | {round(d['rushCoin']*100)}% 고정 | "
  f"{round(d['arc'][0]['coin']*100)} → {round(d['arc'][-1]['coin']*100)}% |")
A(f"| 터치 | 스테이지당 {d['touches']}회 | 무제한 |")
A("| 끝나는 조건 | 목표 미달 | 판이 가득 참 |")
A("| 난이도의 출처 | 스테이지 목표 + 유물 | 점수에 따른 사다리 |")
A("")

open('난이도-곡선.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(f"난이도-곡선.md 생성 — 러시 {len(rows)//PER}라운드 · 아케이드 {d['maxLv']}단계")
