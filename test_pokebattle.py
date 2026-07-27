"""pokebattle.py 를 밖에서 검증한다. 프로그램 자신의 selftest와 독립."""
import itertools
import os
import random
import sys
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pokebattle as P

combos = P.COMBOS
n = len(combos)
A = [[int(P.duel(a, b) * 2 - 1) for b in combos] for a in combos]
IDX = {c: i for i, c in enumerate(combos)}


def optimal_total(slots, opponents, k):
    """슬롯당 상위 k후보로 완전탐색한 최적 총점. k를 키워도 안 변하면 최적."""
    scored = []
    for i in slots:
        row = [(P.duel(m[2], opponents[i][2]), m) for m in P.MONS]
        row.sort(key=lambda sm: (-sm[0], sm[1][0]))
        scored.append(row[:k])
    best = -1
    for combo in itertools.product(*scored):
        if len({m[0] for _, m in combo}) < len(slots):
            continue
        best = max(best, sum(s for s, _ in combo))
    return best


# 1) 카운터 배정의 최적성: 상위5 제한이 최적해를 놓치지 않는가
random.seed(0)
cases = [[random.choice(P.MONS) for _ in range(5)] for _ in range(15)]
K = 10  # 이론적 보장치는 k=슬롯수=5. 2배로 넓혀도 답이 같으면 충분.
for opps in cases:
    slots = list(range(5))
    got = sum(P.duel(m[2], opps[i][2])
              for i, m in zip(slots, P.counter_slots(slots, opps, set())))
    assert abs(got - optimal_total(slots, opps, K)) < 1e-9, opps
print(f"[1] 카운터 배정 최적성 OK — {len(cases)}케이스, 상위5 == 상위{K} 완전탐색")

# 2) 항상 중복 없는 5마리
rng = random.Random(1)
for t in range(300):
    opps = [random.choice(P.MONS) if random.random() < 0.5 else None for _ in range(5)]
    team = P.pick(opps, rng)
    assert len(team) == 5 and all(team) and len({m[0] for m in team}) == 5, team
print("[2] 중복 없는 5마리 OK — 300회 (아는 슬롯/미지 슬롯 혼합)")

# 3) 판정 대칭성
for a, b in itertools.product(combos, repeat=2):
    assert abs(P.duel(a, b) + P.duel(b, a) - 1.0) < 1e-9, (a, b)
print(f"[3] 대칭성 OK — 고유 타입조합 {n}종 전체 쌍 {n*n}건")

# 4) 같은 조합끼리 무승부 + 타입 순서 무관
for c in combos:
    assert P.duel(c, c) == 0.5
assert P.duel(("바위", "땅"), ("땅", "바위")) == 0.5
assert P.key(("바위", "땅")) == P.key(("땅", "바위"))
print("[4] 동일 조합 무승부 / 타입 순서 무관 OK")

# 5) 손으로 계산한 매치업 (표를 안 믿고 직접 계산)
hand = [
    (("물",),          ("불꽃",),          2.0, 0.5),   # 이미지 예시
    (("전기", "강철"), ("땅",),            1.0, 4.0),   # 전기0 강철1 -> max 1, 땅은 4배 반격
    (("노말",),        ("고스트",),        0.0, 0.0),   # 서로 무효 -> 무
    (("드래곤",),      ("페어리",),        0.0, 2.0),
    (("얼음",),        ("드래곤", "비행"), 4.0, 1.0),   # 망나뇽
    (("에스퍼",),      ("악",),            0.0, 2.0),
    (("전기",),        ("물", "비행"),     4.0, 1.0),   # 갸라도스
]
for a, b, ea, eb in hand:
    assert (P.best_mult(a, b), P.best_mult(b, a)) == (ea, eb), (a, b)
print(f"[5] 손계산 매치업 {len(hand)}건 OK")

# 6) 151마리 각각에 대해 실제 최선 카운터를 뽑는가
nolose = 0
for m in P.MONS:
    got = P.duel(P.counter_slots([0], [m], set())[0][2], m[2])
    beatable = max(P.duel(c, m[2]) for c in combos)
    assert got == beatable, (m[1], got, beatable)
    if beatable < 1.0:
        nolose += 1
print(f"[6] 151마리 최선 카운터 OK (확실히 못 이기는 상대: {nolose}마리)")

# 7) 상대 엔트리를 전부 알 때
tally = []
for _ in range(200):
    opps = [random.choice(P.MONS) for _ in range(5)]
    team = P.counter_slots(list(range(5)), opps, set())
    tally.append(sum(1 for mine, o in zip(team, opps)
                     if P.best_mult(mine[2], o[2]) > P.best_mult(o[2], mine[2])))
print(f"[7] 전부 알 때 200회 평균 {sum(tally)/len(tally):.2f}승/5판, 5승 {tally.count(5)}회")

# 8) NASH가 정말 균형인가 — 유리수 정확 연산, 37개 순수전략 전수
assert sum(w for _, w in P.NASH) == P.NASH_DEN
p_exact = [F(0)] * n
for c, w in P.NASH:
    p_exact[IDX[c]] = F(w, P.NASH_DEN)
gains = [sum(F(A[j][i]) * p_exact[i] for i in range(n)) for j in range(n)]
assert max(gains) == 0, [(combos[j], g) for j, g in enumerate(gains) if g > 0]
assert sum(p_exact) == 1
tight = sum(1 for g in gains if g == 0)
print(f"[8] 내쉬 균형 정확성 OK — exploitability = {max(gains)} (유리수 정확 0), "
      f"support {sum(1 for x in p_exact if x)}종, 무차별 전략 {tight}종")

# 9) 추출 분포의 슬롯 주변분포가 균형과 정확히 같은가 (표본이 아니라 분포 자체를 검사)
SUP = [c for c, _ in P.NASH]
caps = [len(P.COMBO_MONS[c]) for c in SUP]
dist = P.nash_multiset_dist(5, caps)
assert abs(sum(pr for pr, _ in dist) - 1) < 1e-12
marg = [0.0] * n
for pr, vec in dist:
    for i, k in enumerate(vec):
        assert k <= caps[i], ("정원 초과", SUP[i], k)
        marg[IDX[SUP[i]]] += pr * k / 5
drift = max(abs(marg[i] - float(p_exact[i])) for i in range(n))
round_gain = max(sum(A[j][i] * marg[i] for i in range(n)) for j in range(n))
print(f"[9] 슬롯 주변분포 = 균형 (최대편차 {drift:.2e}), "
      f"라운드 exploitability {round_gain:+.2e}, 실현가능 멀티셋 {len(dist)}개")
assert drift < 1e-12, drift
assert round_gain < 1e-12, round_gain

# 10) 시리즈(다수결) 수준 착취 가능성 — 시뮬레이션이 아니라 정확 계산.
#     양쪽 다 순서를 균등 무작위화하므로 페이오프는 멀티셋 쌍만의 함수:
#     E[sign(승수 - 패수)] over 무작위 전단사.
mine = []  # (확률, 조합 인덱스 5개) 를 순열까지 펼친 것
for pr, vec in dist:
    exp = []
    for i, k in enumerate(vec):
        exp += [IDX[SUP[i]]] * k
    perms = sorted(set(itertools.permutations(exp)))
    for pm in perms:
        mine.append((pr / len(perms), pm))
assert abs(sum(w for w, _ in mine) - 1) < 1e-12
print(f"     순서 있는 튜플 {len(mine):,}개로 전개")


def opp_edge(y):
    """상대 엔트리 y(조합 5개)의 시리즈 우위. 양수면 상대가 유리."""
    tot = 0.0
    for w, x in mine:
        s = 0
        for a, b in zip(x, y):
            v = A[a][b]
            s += 1 if v > 0 else -1 if v < 0 else 0
        tot += w if s > 0 else -w if s < 0 else 0.0
    return -tot


CAP = [len(P.COMBO_MONS[c]) for c in combos]
cands = [[i] * 5 for i in range(n) if CAP[i] >= 5]           # 순수 엔트리 전수
for i in range(n):                                            # 위협적인 조합과의 2종 혼합
    for j in range(n):
        if i != j and CAP[i] >= 4 and CAP[j] >= 1:
            cands.append([i] * 4 + [j])
edges = sorted((opp_edge(y), tuple(y)) for y in cands)
worst = edges[-1][0]
print(f"     상대 후보 {len(cands):,}개 전수 검사, 상대에게 가장 유리한 5개:")
for e, y in edges[:-6:-1]:
    print(f"       {e:+.5f}  " + ", ".join("/".join(combos[j]) for j in y)[:60])
print(f"[10] 최악의 상대 엔트리에게 상대 우위 {worst:+.4f}")
# 라운드 수준은 정확히 0이지만 다수결은 결합분포에 의존해 완전히 0으로는 못 만든다.
# 완전 균형은 37개 조합 전체의 5-멀티셋(~75만개) 위에서 double oracle을 돌려야 한다.
assert worst < 0.05, worst

# 11) 순서를 모를 때 E[승점]이 개별 점수의 합으로 분해되는가 (교차항 없음).
#     이게 성립하니 최대기대값 엔트리는 조합 탐색 없이 상위 5마리로 구해진다.
rng = random.Random(4)
for _ in range(20):
    a = [rng.choice(P.MONS) for _ in range(5)]
    b = [rng.choice(P.MONS) for _ in range(5)]
    exact = sum(sum(P.duel(x[2], y[2]) for x, y in zip(pm, b))
                for pm in itertools.permutations(a)) / 120
    decomp = sum(sum(P.duel(x[2], y[2]) for y in b) / 5 for x in a)
    assert abs(exact - decomp) < 1e-9, (exact, decomp)
print("[11] 무작위 순서에서 E[승점] = 개별 점수의 합 OK — 20케이스, 순열 120개 전수 대조")

# 12) --dup (중복 허용): 슬롯이 완전히 독립이라 시리즈 착취력이 0이 되는가.
#     라운드마다 승>=패 이고 슬롯이 독립이면, 합의 부호도 그 성질을 물려받는다.
pv = [0.0] * n
for c, w_ in P.NASH:
    pv[IDX[c]] = w_ / P.NASH_DEN
WW = [sum(pv[i] for i in range(n) if P.duel(combos[i], y) == 1.0) for y in combos]
DD = [sum(pv[i] for i in range(n) if P.duel(combos[i], y) == 0.5) for y in combos]
LL = [sum(pv[i] for i in range(n) if P.duel(combos[i], y) == 0.0) for y in combos]
assert all(WW[j] >= LL[j] - 1e-12 for j in range(n)), "라운드 수준부터 깨짐"


def dup_edge(y):
    """상대 엔트리 y 의 시리즈 우위. 내 5슬롯이 i.i.d. 이므로 정확히 컨볼루션."""
    d = [0.0] * 11
    d[5] = 1.0
    for j in y:
        nd = [0.0] * 11
        for s_, pr in enumerate(d):
            if pr:
                nd[min(s_ + 1, 10)] += pr * WW[j]
                nd[s_] += pr * DD[j]
                nd[max(s_ - 1, 0)] += pr * LL[j]
        d = nd
    return sum(d[:5]) - sum(d[6:])


cands = [[i] * 5 for i in range(n)]                       # 순수 엔트리 전수
for i, j in itertools.combinations(range(n), 2):          # 2종 혼합 전수
    for a in range(1, 5):
        cands.append([i] * a + [j] * (5 - a))
rng = random.Random(9)
for _ in range(20000):                                    # 3종 이상 무작위 표본
    cands.append([rng.randrange(n) for _ in range(5)])
worst_dup = max(dup_edge(y) for y in cands)
print(f"[12] --dup 시리즈 착취력 {worst_dup:+.2e} — 상대 후보 {len(cands):,}개 "
      f"(순수/2종 전수 + 무작위 2만)")
assert worst_dup < 1e-9, worst_dup

# 13) --dup 에서는 슬롯끼리 독립이라 각 슬롯이 무조건 최선 카운터를 받는다
for m in P.MONS:
    got = P.counter_slots([0], [m], set(), dup=True)[0]
    assert P.duel(got[2], m[2]) == max(P.duel(c, m[2]) for c in combos), m[1]
team = P.pick([P.BY_NAME["리자몽"]] * 5, random.Random(0), dup=True)
assert len({x[0] for x in team}) == 1, team          # 5슬롯 모두 같은 최선 카운터
print(f"[13] --dup 카운터 배정 OK — 151마리 전부 슬롯별 최선, 동일 상대 5슬롯은 같은 픽")

print("\n전부 통과")
