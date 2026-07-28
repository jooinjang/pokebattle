#!/usr/bin/env python3
"""matches.json 의 관측 기록으로 특정 상대를 정찰한다.

pokebattle.py 는 상대를 모를 때의 균형 전략을 다룬다. 이쪽은 반대로,
상대가 균형에서 얼마나 벗어나 있고 그걸 어떻게 착취할지를 본다.

    scout.py                     # 기본 상대 자동 선택(가장 많이 붙은 팀)
    scout.py 운영1유닛           # 상대 지정
    scout.py 운영1유닛 --hide 강철/전기
                                 # 우리 주력 조합을 지정하면 그걸 노리는
                                 # 저격 픽이 어느 슬롯에서 오는지 집계한다
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pokebattle import (BY_NAME, COMBO_MONS, COMBOS, MONS, NASH, NASH_DEN,
                        SLOTS, best_mult, duel, key, pad)

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

    args = [a for a in argv if not a.startswith("--")]
    hide = None
    if "--hide" in argv:
        hide = tuple(sorted(argv[argv.index("--hide") + 1].split("/")))
    foe = args[0] if args else next(t for t, _ in teams.most_common() if t != us)
    E = entries_of(matches, foe)
    if not E:
        raise SystemExit(f"{foe} 의 기록이 없습니다.")

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
