#!/usr/bin/env python3
"""matches.json 의 관측 기록으로 특정 상대를 정찰한다.

pokebattle.py 는 상대를 모를 때의 균형 전략을 다룬다. 이쪽은 반대로,
상대가 균형에서 얼마나 벗어나 있고 그걸 어떻게 착취할지를 본다.

    scout.py                     # 기본 상대 자동 선택(가장 많이 붙은 팀)
    scout.py 운영1유닛           # 상대 지정
    scout.py 운영1유닛 --hide 강철/전기
                                 # 우리 주력 조합을 지정하면 그걸 노리는
                                 # 저격 픽이 어느 슬롯에서 오는지 집계한다
    scout.py 개발16유닛 --solo   # 개인 매치(3마리) — 그 성향을 착취하는 3마리
    scout.py 개발16유닛 --arrange 썬더 코일 썬더 고지 갸라도스
                                 # 5마리를 그 상대의 슬롯 습관에 맞춰 배치한다.
                                 # pokebattle.py --dup 이 뽑은 멀티셋을 그대로
                                 # 넣으면 균형 구성 + 정보 기반 배치가 된다.
"""
import itertools
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pokebattle import (BY_NAME, COMBO_MONS, COMBOS, MONS, NASH, NASH_DEN,
                        SLOTS, best_mult, duel, key, pad, resolve)

HERE = os.path.dirname(os.path.abspath(__file__))


def datafile():
    """본인 기록(matches.json)이 있으면 그걸, 없으면 익명 샘플을 읽는다."""
    mine = os.path.join(HERE, "matches.json")
    return mine if os.path.exists(mine) else os.path.join(HERE, "match-samples.json")


def load():
    path = datafile()
    d = json.load(open(path, encoding="utf-8"))
    if os.path.basename(path) != "matches.json":
        print(f"({os.path.basename(path)} 를 읽었습니다. 본인 기록은 matches.json 으로 만드세요)\n")
    return d["us"], d["matches"]


def verify(matches):
    """표기 점수와 상성 엔진 계산이 일치하는지. 기록 오류를 여기서 잡는다."""
    bad = []
    for i, m in enumerate(matches, 1):
        w = l = 0
        for a, b in m["slots"]:
            x, y = best_mult(BY_NAME[a][2], BY_NAME[b][2]), best_mult(BY_NAME[b][2], BY_NAME[a][2])
            w += x > y
            l += x < y
        if f"{w}:{l}" != m["score"]:
            bad.append((i, m["score"], f"{w}:{l}"))
    return bad


def entries_of(matches, team):
    """그 팀이 낸 엔트리를 슬롯 순서 그대로."""
    out = []
    for m in matches:
        if m["left"] == team:
            out.append([s[0] for s in m["slots"]])
        elif m["right"] == team:
            out.append([s[1] for s in m["slots"]])
    return out


def record(matches, team):
    w = d = l = 0
    for m in matches:
        if team not in (m["left"], m["right"]):
            continue
        a, b = (int(x) for x in m["score"].split(":"))
        if m["right"] == team:
            a, b = b, a
        w += a > b
        d += a == b
        l += a < b
    return w, d, l


def print_solo(E, foe, dup):
    """개인 매치(3마리) — 관측 분포를 착취하는 3마리와 기대 성적.

    내 3마리는 상대 한 명의 3마리와 순서대로 붙고, 동료 3판과 합산해
    6판 다승제. 동료는 못 고르므로 내 마진 기대값을 최대화하면 된다.
    """
    from pokebattle import SOLO_SLOTS, solo_margin_dist, solo_outcome, solo_pick
    picks = [key(BY_NAME[x][2]) for e in E for x in e]
    q = {c: n / len(picks) for c, n in Counter(picks).items()}
    team = solo_pick(None, dup, q)
    tk = [key(m[2]) for m in team]
    who = f"{foe} 성향" if foe else "전체 상대 풀"
    print(f"개인 매치 3마리 — {who}({len(picks)}픽) 착취")
    print()
    for i, m in enumerate(team, 1):
        c = key(m[2])
        w = sum(p for o, p in q.items() if duel(c, o) == 1.0)
        l = sum(p for o, p in q.items() if duel(c, o) == 0.0)
        print(f"  {i}번  {pad(m[1], 12)}({pad('/'.join(m[2]), 12)}) "
              f"승 {w:.0%} 무 {1-w-l:.0%} 패 {l:.0%}   마진 {w-l:+.2f}")
    md = solo_margin_dist(tk, q)
    w, d, l = solo_outcome(tk, q)
    print()
    print("  내 3판 마진: " + "  ".join(f"{s-3:+d} {md[s]:.0%}" for s in range(7) if md[s] > 0.005))
    print(f"  기대 마진 {sum((s-3)*md[s] for s in range(7)):+.2f}판")
    print(f"  팀 최종 (동료 포함): 승 {w:.1%}  무 {d:.1%}  패 {l:.1%}")
    print()
    from pokebattle import NASH as _N, NASH_DEN as _D
    _q = {c: w / _D for c, w in _N}
    _w, _, _l = solo_outcome([c for c, _ in _N][:SOLO_SLOTS], _q)
    print(f"  참고: 균형 추출(pokebattle.py --solo)은 승 = 패 {_w:.1%} 입니다.")
    print("        위 수치가 그보다 나은 만큼이 성향 착취로 얻는 이득입니다.")
    if foe:
        print(f"  주의: 개인 매치 상대는 4명 중 무작위입니다. {foe} 한 팀에만 맞추면")
        print(f"        다른 사람이 걸렸을 때 빗나갑니다. 팀명을 빼면 전체 풀 기준입니다.")
    return 0


def slot_dist(E, alpha=0.5):
    """슬롯별로 상대가 놓은 타입 조합의 경험분포. alpha 는 라플라스 평활.

    표본이 얇으므로(팀당 2~5경기) 관측 안 된 조합에도 최소 확률을 준다.
    평활이 없으면 한 번도 안 나온 픽에 0을 줘서 배치가 과적합된다.
    """
    out = []
    for s in range(SLOTS):
        seen = Counter(key(BY_NAME[e[s]][2]) for e in E)
        tot = len(E) + alpha * len(COMBOS)
        out.append({c: (seen[c] + alpha) / tot for c in COMBOS})
    return out


def arrange(team, E):
    """team(포켓몬 5마리)을 슬롯별 기대 마진 합이 최대가 되도록 배치한다.

    5! = 120 가지뿐이라 완전탐색. 반환 (최적 순열, 기대마진, 균등배치 기대마진).
    균등배치 값은 비교용 — 이만큼이 슬롯 습관에 베팅해서 얻는 이득이다.
    """
    dist = slot_dist(E)

    def margin(mon, s):
        c = key(mon[2])
        return sum((1 if duel(c, o) == 1.0 else -1 if duel(c, o) == 0.0 else 0) * p
                   for o, p in dist[s].items())

    best = None
    total = 0.0
    for pm in itertools.permutations(range(SLOTS)):
        v = sum(margin(team[i], s) for s, i in enumerate(pm))
        total += v
        if best is None or v > best[0]:
            best = (v, pm)
    return best[1], best[0], total / 120


def print_arrange(team, E, foe):
    order, ev, base = arrange(team, E)
    dist = slot_dist(E)
    print(f"{foe} 슬롯 습관에 맞춘 배치 (관측 {len(E)}경기)")
    print()
    print(f"{pad('슬롯', 5)}{pad('배치', 22)}{pad('그 슬롯의 상대 예상 (상위 3)', 44)}{'기대마진':>9}")
    print("-" * 82)
    for s, i in enumerate(order):
        mon = team[i]
        c = key(mon[2])
        top = sorted(dist[s].items(), key=lambda kv: -kv[1])[:3]
        m = sum((1 if duel(c, o) == 1.0 else -1 if duel(c, o) == 0.0 else 0) * p
                for o, p in dist[s].items())
        exp = ", ".join(f"{'/'.join(o)} {p:.0%}" for o, p in top)
        print(f"{pad(str(s+1), 5)}{pad(mon[1] + '(' + '/'.join(mon[2]) + ')', 22)}"
              f"{pad(exp, 44)}{m:>+9.2f}")
    print("-" * 82)
    print(f"엔트리: {', '.join(team[i][1] for i in order)}")
    print(f"  기대 마진 {ev:+.2f}판  (균등 무작위 배치는 {base:+.2f}판 — 배치로 얻는 이득 {ev-base:+.2f})")
    if abs(ev - base) < 0.15:
        print("  * 이득이 미미합니다. 이 멀티셋은 배치에 둔감하니 순서를 신경 쓸 필요가 없습니다.")
    print()
    print("주의: 배치를 이렇게 맞추는 순간 균형의 착취 불가능성은 깨집니다.")
    print(f"      {foe} 가 슬롯 습관을 바꾸면 이 이득이 그대로 손실이 됩니다.")
    return 0


def main(argv):
    us, matches = load()
    bad = verify(matches)
    if bad:
        print("기록 검증 실패:")
        for i, said, got in bad:
            print(f"  매치{i}  표기 {said} != 계산 {got}")
        return 1
    print(f"매치 {len(matches)}건 전부 상성 엔진 계산과 일치\n")

    teams = Counter()
    for m in matches:
        teams[m["left"]] += 1
        teams[m["right"]] += 1
    print("전적")
    for t, _ in teams.most_common():
        w, d, l = record(matches, t)
        print(f"  {pad(t, 12)} {w}승 {d}무 {l}패" + ("   <- 우리" if t == us else ""))

    hide = None
    if "--hide" in argv:
        i = argv.index("--hide")
        hide = tuple(sorted(argv[i + 1].split("/")))
        argv = argv[:i] + argv[i + 2:]
    solo = "--solo" in argv
    dup = "--dup" in argv
    argv = [a for a in argv if a not in ("--solo", "--dup")]
    lineup = None
    if "--arrange" in argv:
        i = argv.index("--arrange")
        lineup = argv[i + 1:]
        argv = argv[:i]
        if len(lineup) != SLOTS:
            raise SystemExit(f"--arrange 뒤에 포켓몬 {SLOTS}마리를 적으세요. (받은 개수: {len(lineup)})")
    args = [a for a in argv if not a.startswith("--")]
    foe = args[0] if args else next(t for t, _ in teams.most_common() if t != us)
    E = entries_of(matches, foe)
    if not E:
        raise SystemExit(f"{foe} 의 기록이 없습니다.")

    if solo:
        print()
        if args:                       # 팀을 명시하면 그 팀만
            return print_solo(E, foe, dup)
        pooled = [e for t, _ in teams.most_common() if t != us
                  for e in entries_of(matches, t)]
        return print_solo(pooled, None, dup)
    if lineup:
        print()
        return print_arrange([resolve(x) for x in lineup], E, foe)

    print(f"\n{'='*70}\n{foe} 정찰 — 관측 엔트리 {len(E)}개\n{'='*70}")
    for i, e in enumerate(E, 1):
        print(f"  E{i}  " + ", ".join(f"{x}({'/'.join(BY_NAME[x][2])})" for x in e))

    picks = [key(BY_NAME[x][2]) for e in E for x in e]
    cnt = Counter(picks)
    nash = {c: w / NASH_DEN for c, w in NASH}
    print(f"\n타입 조합 분포 ({len(picks)}픽) vs 균형")
    for c, k in cnt.most_common():
        print(f"  {k:>2}/{len(picks)} = {k/len(picks):5.1%}  {pad('/'.join(c), 14)}"
              f" 균형 {nash.get(c, 0.0):5.1%}")
    insup = sum(k for c, k in cnt.items() if c in nash) / len(picks)
    q = {c: cnt[c] / len(picks) for c in COMBOS}
    gain = {c: sum((1 if duel(c, o) == 1.0 else -1 if duel(c, o) == 0.0 else 0) * p
                   for o, p in q.items()) for c in COMBOS}
    top = max(gain, key=gain.get)
    print(f"\n  균형 support 비중 {insup:.0%}  (균형 상대라면 100%)")
    print(f"  라운드 착취 가능성 +{gain[top]:.3f}  최적 대응 {'/'.join(top)}"
          f" ({', '.join(m[1] for m in COMBO_MONS[top][:3])})")
    print(f"  균형 분포였다면 이 값이 0.000 입니다")

    if hide:
        snipe = [c for c in COMBOS if duel(c, hide) == 1.0]
        print(f"\n{'/'.join(hide)} 를 잡는 저격 픽이 어느 슬롯에서 오는가")
        print(f"  저격 조합: {', '.join('/'.join(c) for c in snipe)}")
        col = [0] * SLOTS
        for e in E:
            for i, x in enumerate(e):
                col[i] += key(BY_NAME[x][2]) in snipe
        for i in range(SLOTS):
            print(f"  {i+1}번  {col[i]}/{len(E)} {'█' * col[i]}")
        safe = [i + 1 for i in range(SLOTS) if col[i] == 0]
        print(f"  => 저격이 한 번도 안 온 슬롯: {safe if safe else '없음'}")
        print(f"     엔트리 추이(오래된 순): "
              + " → ".join(str(sum(1 for x in e if key(BY_NAME[x][2]) in snipe)) for e in E))

    print(f"\n관측 엔트리 전부를 상대로 한 순수 5칸 성적 (순서 무관, 확정)")
    rows = []
    for c in COMBOS:
        r = []
        for e in E:
            w = sum(1 for x in e if duel(c, key(BY_NAME[x][2])) == 1.0)
            l = sum(1 for x in e if duel(c, key(BY_NAME[x][2])) == 0.0)
            r.append(1 if w > l else -1 if l > w else 0)
        rows.append((sum(r), r.count(-1), c, r))
    rows.sort(key=lambda t: (-t[0], t[1]))
    print(f"  {pad('조합', 14)}{pad('E1..E' + str(len(E)), 4 * len(E) + 2)}승-무-패   포켓몬")
    for s, nl, c, r in rows[:6]:
        mark = "".join({1: " 승", 0: " 무", -1: " 패"}[v] for v in r)
        print(f"  {pad('/'.join(c), 14)}{pad(mark, 4*len(E)+2)}"
              f"{r.count(1)}-{r.count(0)}-{r.count(-1)}    "
              f"{', '.join(m[1] for m in COMBO_MONS[c][:3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
