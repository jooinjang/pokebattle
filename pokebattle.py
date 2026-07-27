#!/usr/bin/env python3
"""1세대 포켓몬 151마리 중 타입 상성만으로 5마리 엔트리를 고른다.

판정: 서로에게 낼 수 있는 최대 배율을 비교해 높은 쪽이 승. 같으면 무승부.
시리즈: 슬롯끼리 1:1로 5판, 다승 팀이 승리.

양쪽 다 상대 엔트리를 모르고 동시에 제출하므로, 모르는 슬롯은 "랜덤 상대 대비
최강"이 아니라 1판 게임의 내쉬 균형에서 뽑는다. 아는 슬롯이 있으면 착취한다.

사용법:
    pokebattle.py                              # 상대 전부 미지 (균형 추출)
    pokebattle.py 리자몽 ? 피카츄 ? ?           # 아는 슬롯은 카운터, ?는 균형 추출
    pokebattle.py 6 ? 25 ? ?                   # 도감번호도 가능
    pokebattle.py --rank                       # 151마리를 타입 상성 강도순으로 나열
    pokebattle.py --maxev                      # 상대 151마리 균등 가정의 최대기대값 엔트리
    pokebattle.py --dup                        # 같은 포켓몬 중복 허용 규칙
    pokebattle.py --seed 7                     # 추출 고정
    pokebattle.py --selftest
"""
import itertools
import random
import sys
import unicodedata
from fractions import Fraction
from functools import lru_cache

CHART = {
    "노말": {"바위": 0.5, "고스트": 0, "강철": 0.5},
    "격투": {"노말": 2, "비행": 0.5, "독": 0.5, "바위": 2, "벌레": 0.5, "고스트": 0, "강철": 2, "에스퍼": 0.5, "얼음": 2, "악": 2, "페어리": 0.5},
    "비행": {"격투": 2, "바위": 0.5, "벌레": 2, "강철": 0.5, "풀": 2, "전기": 0.5},
    "독": {"독": 0.5, "땅": 0.5, "바위": 0.5, "고스트": 0.5, "강철": 0, "풀": 2, "페어리": 2},
    "땅": {"비행": 0, "독": 2, "바위": 2, "벌레": 0.5, "강철": 2, "불꽃": 2, "풀": 0.5, "전기": 2},
    "바위": {"격투": 0.5, "비행": 2, "땅": 0.5, "벌레": 2, "강철": 0.5, "불꽃": 2, "얼음": 2},
    "벌레": {"격투": 0.5, "비행": 0.5, "독": 0.5, "고스트": 0.5, "강철": 0.5, "불꽃": 0.5, "풀": 2, "에스퍼": 2, "악": 2, "페어리": 0.5},
    "고스트": {"노말": 0, "고스트": 2, "에스퍼": 2, "악": 0.5},
    "강철": {"바위": 2, "강철": 0.5, "불꽃": 0.5, "물": 0.5, "전기": 0.5, "얼음": 2, "페어리": 2},
    "불꽃": {"바위": 0.5, "벌레": 2, "강철": 2, "불꽃": 0.5, "물": 0.5, "풀": 2, "얼음": 2, "드래곤": 0.5},
    "물": {"땅": 2, "바위": 2, "불꽃": 2, "물": 0.5, "풀": 0.5, "드래곤": 0.5},
    "풀": {"비행": 0.5, "독": 0.5, "땅": 2, "바위": 2, "벌레": 0.5, "강철": 0.5, "불꽃": 0.5, "물": 2, "풀": 0.5, "드래곤": 0.5},
    "전기": {"비행": 2, "땅": 0, "물": 2, "풀": 0.5, "전기": 0.5, "드래곤": 0.5},
    "에스퍼": {"격투": 2, "독": 2, "강철": 0.5, "에스퍼": 0.5, "악": 0},
    "얼음": {"비행": 2, "땅": 2, "강철": 0.5, "불꽃": 0.5, "물": 0.5, "풀": 2, "얼음": 0.5, "드래곤": 2},
    "드래곤": {"강철": 0.5, "드래곤": 2, "페어리": 0},
    "악": {"격투": 0.5, "고스트": 2, "에스퍼": 2, "악": 0.5, "페어리": 0.5},
    "페어리": {"격투": 2, "독": 0.5, "강철": 0.5, "불꽃": 0.5, "드래곤": 2, "악": 2},
}

MONS = [
    (1, "이상해씨", ("풀", "독")),
    (2, "이상해풀", ("풀", "독")),
    (3, "이상해꽃", ("풀", "독")),
    (4, "파이리", ("불꽃",)),
    (5, "리자드", ("불꽃",)),
    (6, "리자몽", ("불꽃", "비행")),
    (7, "꼬부기", ("물",)),
    (8, "어니부기", ("물",)),
    (9, "거북왕", ("물",)),
    (10, "캐터피", ("벌레",)),
    (11, "단데기", ("벌레",)),
    (12, "버터플", ("벌레", "비행")),
    (13, "뿔충이", ("벌레", "독")),
    (14, "딱충이", ("벌레", "독")),
    (15, "독침붕", ("벌레", "독")),
    (16, "구구", ("노말", "비행")),
    (17, "피죤", ("노말", "비행")),
    (18, "피죤투", ("노말", "비행")),
    (19, "꼬렛", ("노말",)),
    (20, "레트라", ("노말",)),
    (21, "깨비참", ("노말", "비행")),
    (22, "깨비드릴조", ("노말", "비행")),
    (23, "아보", ("독",)),
    (24, "아보크", ("독",)),
    (25, "피카츄", ("전기",)),
    (26, "라이츄", ("전기",)),
    (27, "모래두지", ("땅",)),
    (28, "고지", ("땅",)),
    (29, "니드런♀", ("독",)),
    (30, "니드리나", ("독",)),
    (31, "니드퀸", ("독", "땅")),
    (32, "니드런♂", ("독",)),
    (33, "니드리노", ("독",)),
    (34, "니드킹", ("독", "땅")),
    (35, "삐삐", ("페어리",)),
    (36, "픽시", ("페어리",)),
    (37, "식스테일", ("불꽃",)),
    (38, "나인테일", ("불꽃",)),
    (39, "푸린", ("노말", "페어리")),
    (40, "푸크린", ("노말", "페어리")),
    (41, "주뱃", ("독", "비행")),
    (42, "골뱃", ("독", "비행")),
    (43, "뚜벅쵸", ("풀", "독")),
    (44, "냄새꼬", ("풀", "독")),
    (45, "라플레시아", ("풀", "독")),
    (46, "파라스", ("벌레", "풀")),
    (47, "파라섹트", ("벌레", "풀")),
    (48, "콘팡", ("벌레", "독")),
    (49, "도나리", ("벌레", "독")),
    (50, "디그다", ("땅",)),
    (51, "닥트리오", ("땅",)),
    (52, "나옹", ("노말",)),
    (53, "페르시온", ("노말",)),
    (54, "고라파덕", ("물",)),
    (55, "골덕", ("물",)),
    (56, "망키", ("격투",)),
    (57, "성원숭", ("격투",)),
    (58, "가디", ("불꽃",)),
    (59, "윈디", ("불꽃",)),
    (60, "발챙이", ("물",)),
    (61, "슈륙챙이", ("물",)),
    (62, "강챙이", ("물", "격투")),
    (63, "캐이시", ("에스퍼",)),
    (64, "윤겔라", ("에스퍼",)),
    (65, "후딘", ("에스퍼",)),
    (66, "알통몬", ("격투",)),
    (67, "근육몬", ("격투",)),
    (68, "괴력몬", ("격투",)),
    (69, "모다피", ("풀", "독")),
    (70, "우츠동", ("풀", "독")),
    (71, "우츠보트", ("풀", "독")),
    (72, "왕눈해", ("물", "독")),
    (73, "독파리", ("물", "독")),
    (74, "꼬마돌", ("바위", "땅")),
    (75, "데구리", ("바위", "땅")),
    (76, "딱구리", ("바위", "땅")),
    (77, "포니타", ("불꽃",)),
    (78, "날쌩마", ("불꽃",)),
    (79, "야돈", ("물", "에스퍼")),
    (80, "야도란", ("물", "에스퍼")),
    (81, "코일", ("전기", "강철")),
    (82, "레어코일", ("전기", "강철")),
    (83, "파오리", ("노말", "비행")),
    (84, "두두", ("노말", "비행")),
    (85, "두트리오", ("노말", "비행")),
    (86, "쥬쥬", ("물",)),
    (87, "쥬레곤", ("물", "얼음")),
    (88, "질퍽이", ("독",)),
    (89, "질뻐기", ("독",)),
    (90, "셀러", ("물",)),
    (91, "파르셀", ("물", "얼음")),
    (92, "고오스", ("고스트", "독")),
    (93, "고우스트", ("고스트", "독")),
    (94, "팬텀", ("고스트", "독")),
    (95, "롱스톤", ("바위", "땅")),
    (96, "슬리프", ("에스퍼",)),
    (97, "슬리퍼", ("에스퍼",)),
    (98, "크랩", ("물",)),
    (99, "킹크랩", ("물",)),
    (100, "찌리리공", ("전기",)),
    (101, "붐볼", ("전기",)),
    (102, "아라리", ("풀", "에스퍼")),
    (103, "나시", ("풀", "에스퍼")),
    (104, "탕구리", ("땅",)),
    (105, "텅구리", ("땅",)),
    (106, "시라소몬", ("격투",)),
    (107, "홍수몬", ("격투",)),
    (108, "내루미", ("노말",)),
    (109, "또가스", ("독",)),
    (110, "또도가스", ("독",)),
    (111, "뿔카노", ("땅", "바위")),
    (112, "코뿌리", ("땅", "바위")),
    (113, "럭키", ("노말",)),
    (114, "덩쿠리", ("풀",)),
    (115, "캥카", ("노말",)),
    (116, "쏘드라", ("물",)),
    (117, "시드라", ("물",)),
    (118, "콘치", ("물",)),
    (119, "왕콘치", ("물",)),
    (120, "별가사리", ("물",)),
    (121, "아쿠스타", ("물", "에스퍼")),
    (122, "마임맨", ("에스퍼", "페어리")),
    (123, "스라크", ("벌레", "비행")),
    (124, "루주라", ("얼음", "에스퍼")),
    (125, "에레브", ("전기",)),
    (126, "마그마", ("불꽃",)),
    (127, "쁘사이저", ("벌레",)),
    (128, "켄타로스", ("노말",)),
    (129, "잉어킹", ("물",)),
    (130, "갸라도스", ("물", "비행")),
    (131, "라프라스", ("물", "얼음")),
    (132, "메타몽", ("노말",)),
    (133, "이브이", ("노말",)),
    (134, "샤미드", ("물",)),
    (135, "쥬피썬더", ("전기",)),
    (136, "부스터", ("불꽃",)),
    (137, "폴리곤", ("노말",)),
    (138, "암나이트", ("바위", "물")),
    (139, "암스타", ("바위", "물")),
    (140, "투구", ("바위", "물")),
    (141, "투구푸스", ("바위", "물")),
    (142, "프테라", ("바위", "비행")),
    (143, "잠만보", ("노말",)),
    (144, "프리져", ("얼음", "비행")),
    (145, "썬더", ("전기", "비행")),
    (146, "파이어", ("불꽃", "비행")),
    (147, "미뇽", ("드래곤",)),
    (148, "신뇽", ("드래곤",)),
    (149, "망나뇽", ("드래곤", "비행")),
    (150, "뮤츠", ("에스퍼",)),
    (151, "뮤", ("에스퍼",)),
]

# 1판 게임의 내쉬 균형. 양쪽 다 상대 엔트리를 모르고 동시에 제출하므로
# "랜덤 상대 대비 최강"이 아니라 "어떤 상대에게도 안 지는" 혼합전략이 답이다.
# 유리수로 정확히 풀었고 exploitability == 0 (selftest에서 매번 재검증).
NASH_DEN = 62
NASH = [
    (("강철", "전기"), 17),
    (("땅",), 16),
    (("비행", "전기"), 8),
    (("땅", "바위"), 6),
    (("물", "에스퍼"), 6),
    (("얼음", "에스퍼"), 4),
    (("물", "비행"), 2),
    (("벌레", "풀"), 2),
    (("불꽃", "비행"), 1),
]

BY_NAME = {name: (dex, name, types) for dex, name, types in MONS}
BY_DEX = {dex: (dex, name, types) for dex, name, types in MONS}
SLOTS = 5


def key(types):
    """타입 조합의 정규형. (바위,땅)과 (땅,바위)는 같은 조합이다."""
    return tuple(sorted(types))


COMBOS = sorted({key(m[2]) for m in MONS})
COMBO_MONS = {c: [m for m in MONS if key(m[2]) == c] for c in COMBOS}


def eff(atk, defender):
    """공격 타입 하나가 방어 타입 조합에 내는 배율."""
    m = 1.0
    for d in defender:
        m *= CHART.get(atk, {}).get(d, 1.0)
    return m


def best_mult(attacker, defender):
    """공격 측이 낼 수 있는 최대 배율."""
    return max(eff(t, defender) for t in attacker)


@lru_cache(maxsize=None)
def duel(a, b):
    """a 관점 점수: 승 1.0 / 무 0.5 / 패 0.0."""
    x, y = best_mult(a, b), best_mult(b, a)
    return 1.0 if x > y else 0.0 if x < y else 0.5


def feasible_counts(k, caps):
    """합이 k이고 조합별 정원을 넘지 않는 개수벡터 전부."""
    out = []

    def rec(i, left, cur):
        if i == len(caps):
            if left == 0:
                out.append(tuple(cur))
            return
        for c in range(min(caps[i], left) + 1):
            rec(i + 1, left - c, cur + [c])

    rec(0, k, [])
    return out


def nash_multiset_dist(k, caps):
    """미지 슬롯 k개를 채울 타입 조합 멀티셋의 분포.

    슬롯마다 독립으로 뽑으면 안 된다. 균형은 강철/전기에 27.4%를 싣는데
    해당 포켓몬은 코일·레어코일 2마리뿐이라 중복 금지 규칙과 충돌한다.
    그래서 k마리를 한 덩어리로 뽑되 두 가지를 동시에 만족시킨다:

      1. 슬롯 주변분포 = 균형 그대로  -> 라운드 수준 착취력 정확히 0
      2. 결합분포 = 최대엔트로피(정원 조건부 독립)

    2번이 없으면 안 된다. 주변분포만 맞추고 결합이 퇴화하면(계통추출은
    서로 다른 멀티셋을 9개밖에 만들지 않는다) 다수결 승부에서 다시
    착취당한다 — 시리즈 착취력 +0.14 vs +0.04. test [10] 참고.

    구현: i.i.d. 추출을 실현가능집합에 조건화한 분포가 최대엔트로피 해다.
    조건화 후 주변분포가 균형이 되도록 IPF로 가중치를 미리 기울인다.
    """
    p = [w / NASH_DEN for _, w in NASH]
    live = [i for i in range(len(p)) if caps[i] > 0]
    if len(live) < len(p):  # 아는 슬롯이 유일한 포켓몬을 먼저 가져간 경우
        tot = sum(p[i] for i in live)
        p = [p[i] / tot if i in live else 0.0 for i in range(len(p))]

    vecs = [v for v in feasible_counts(k, caps) if all(v[i] == 0 for i in range(len(p)) if p[i] == 0)]

    def weigh(w):
        probs, marg = [], [0.0] * len(p)
        for v in vecs:
            pr = 1.0
            for i, c in enumerate(v):
                for _ in range(c):
                    pr *= w[i]
                pr /= FACT[c]
            probs.append(pr)
            for i, c in enumerate(v):
                marg[i] += pr * c
        s = sum(probs)
        return [x / s for x in probs], [x / (s * k) for x in marg]

    w = list(p)
    for _ in range(200):
        probs, marg = weigh(w)
        if max(abs(marg[i] - p[i]) for i in range(len(p))) < 1e-13:
            break
        w = [w[i] * (p[i] / marg[i]) if marg[i] > 0 else 0.0 for i in range(len(p))]
        s = sum(w)
        w = [x / s for x in w]
    return list(zip(probs, vecs))


FACT = [1, 1, 2, 6, 24, 120]


def sample_nash_dup(k, rng):
    """중복 허용판. 슬롯마다 그냥 독립으로 뽑으면 된다.

    정원 제약이 사라지므로 각 슬롯이 정확히 균형 분포를 따르고, 슬롯끼리
    독립이다. 이러면 라운드마다 승 확률 >= 패 확률이 보장되고, 독립인
    확률변수의 합은 자기 부호반전을 확률적으로 지배하므로 다수결에서도
    P(시리즈 승) >= P(시리즈 패)가 따라온다.

    중복 금지판(nash_multiset_dist)이 남기는 시리즈 착취력 +0.039가
    여기서는 정확히 0이 된다. 상대 엔트리 749,398개 전수 확인 — test [12].
    """
    combos = [c for c, _ in NASH]
    weights = [w for _, w in NASH]
    return [rng.choice(COMBO_MONS[c])
            for c in rng.choices(combos, weights=weights, k=k)]


def sample_nash(k, rng, used=()):
    """미지 슬롯 k개에 균형 표본을 배정한다. 슬롯 순서는 균등 무작위."""
    used = set(used)
    avail = [[m for m in COMBO_MONS[c] if m[0] not in used] for c, _ in NASH]
    caps = [len(a) for a in avail]
    if sum(caps) < k:
        raise SystemExit("아는 슬롯이 균형 support 포켓몬을 너무 많이 소진했습니다.")

    x, acc = rng.random(), 0.0
    for pr, vec in nash_multiset_dist(k, caps):
        acc += pr
        if x < acc:
            break
    team = []
    for i, c in enumerate(vec):
        team += rng.sample(avail[i], c)
    rng.shuffle(team)
    return team


def nash_prob(types):
    """이 타입 조합의 균형 확률."""
    k = key(types)
    return next((w / NASH_DEN for c, w in NASH if c == k), 0.0)


def resolve(token):
    """이름 또는 도감번호 -> 포켓몬. ?는 None(미지)."""
    if token in ("?", "-", "_"):
        return None
    if token.isdigit() and int(token) in BY_DEX:
        return BY_DEX[int(token)]
    if token in BY_NAME:
        return BY_NAME[token]
    raise SystemExit(f"모르는 포켓몬: {token!r} (1세대 한국어 이름 또는 1~151 도감번호)")


def counter_slots(slots, opponents, used, dup=False):
    """상대를 아는 슬롯들에 최선의 카운터를 배정한다.

    중복 허용이면 슬롯끼리 독립이라 각자 최선을 고르면 끝난다.
    중복 금지면 배정 문제가 되는데, 슬롯이 5개 이하라 슬롯당 상위 5후보만
    남겨도 최적 배정이 그 안에 존재한다.
    (좌측 정점 k개인 최대 가중 이분 매칭은 각 정점의 상위 k개만 봐도 충분)
    """
    if dup:
        return [max(MONS, key=lambda m: (duel(m[2], opponents[i][2]), -m[0]))
                for i in slots]

    scored = []
    for i in slots:
        row = [(duel(m[2], opponents[i][2]), m) for m in MONS if m[0] not in used]
        row.sort(key=lambda sm: (-sm[0], sm[1][0]))
        scored.append(row[:SLOTS])

    best = None
    for combo in itertools.product(*scored):
        if len({m[0] for _, m in combo}) < len(slots):
            continue
        total = sum(s for s, _ in combo)
        if best is None or total > best[0]:
            best = (total, combo)
    return [m for _, m in best[1]]


def pick(opponents, rng=None, dup=False):
    """슬롯별 상대(None=미지)를 받아 5마리를 고른다. dup이면 같은 포켓몬 중복 허용.

    아는 슬롯은 확정 카운터로 착취하고, 모르는 슬롯은 균형에서 뽑는다.
    모르는 슬롯에 '랜덤 상대 대비 최강'을 넣으면 상대도 동시에 최적화하는
    상황에서 그대로 카운터당한다 — 균형 추출만이 안 지는 것을 보장한다.
    """
    rng = rng or random.Random()
    unknown = [i for i, o in enumerate(opponents) if o is None]
    known = [i for i, o in enumerate(opponents) if o is not None]

    team = [None] * len(opponents)
    if unknown:
        draw = (sample_nash_dup(len(unknown), rng) if dup
                else sample_nash(len(unknown), rng))
        for i, m in zip(unknown, draw):
            team[i] = m
    used = {m[0] for m in team if m}
    for i, m in zip(known, counter_slots(known, opponents, used, dup) if known else []):
        team[i] = m
    return team


def outcome(a, b):
    x, y = best_mult(a[2], b[2]), best_mult(b[2], a[2])
    verdict = "승" if x > y else "패" if x < y else "무"
    return verdict, x, y


def fmt(mon):
    return f"{mon[1]}({'/'.join(mon[2])})"


def pad(s, width):
    """한글은 터미널에서 2칸을 먹으므로 표시 폭 기준으로 채운다."""
    w = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)
    return s + " " * max(0, width - w)


def ranking():
    """151마리를 타입 상성 강도순으로. (승수 + 무승부/2) / 151.

    타입 조합만이 승부를 가르므로 같은 조합인 포켓몬은 점수가 완전히 같다.
    동점은 같은 순위로 묶고, 다음 순위는 건너뛴다.
    """
    stat = {}
    for c in COMBOS:
        w = sum(1 for m in MONS if duel(c, m[2]) == 1.0)
        d = sum(1 for m in MONS if duel(c, m[2]) == 0.5)
        stat[c] = (w, d, len(MONS) - w - d, (w + d / 2) / len(MONS))

    # 동점은 같은 순위, 다음 순위는 건너뛴다. 서로 다른 타입 조합이 같은
    # 점수를 내는 경우도 있으므로(물/에스퍼와 전기/비행 둘 다 105/151)
    # 조합이 아니라 점수로 묶는다.
    ordered = sorted(MONS, key=lambda m: (-stat[key(m[2])][3], m[0]))
    scores = [stat[key(m[2])][3] for m in ordered]
    return [(1 + sum(1 for s in scores if s > sc), m, stat[key(m[2])])
            for m, sc in zip(ordered, scores)]


def print_ranking():
    rows = ranking()
    print(f"1세대 151마리 타입 상성 강도순 — {len(MONS)}마리 전체와 1:1로 붙였을 때의 성적")
    print("(같은 타입 조합은 성능이 완전히 동일하므로 동점 처리)")
    print()
    print(f"{pad('순위', 6)}{pad('포켓몬', 14)}{pad('타입', 16)}{'점수':>8}{'승':>6}{'무':>5}{'패':>5}")
    print("-" * 62)
    for rank, m, (w, d, l, s) in rows:
        print(f"{pad(str(rank), 6)}{pad(m[1], 14)}{pad('/'.join(m[2]), 16)}"
              f"{s:>8.4f}{w:>6}{d:>5}{l:>5}")
    return 0


def print_maxev(dup=False):
    """상대를 151마리 균등으로 가정했을 때 기대값이 최대인 엔트리.

    양쪽 다 순서를 모르면 대진이 무작위 전단사가 되어 E[승점]에 교차항이 없다
    (test [11]). 그래서 조합을 탐색할 필요 없이 개별 점수 상위 5마리가 곧 답이다.
    """
    score = {c: sum(duel(c, m[2]) for m in MONS) / len(MONS) for c in COMBOS}
    loss = {c: sum(1 for m in MONS if duel(c, m[2]) == 0.0) for c in COMBOS}
    print("타입 조합별 개별 기대점수 (상대 = 151마리 균등, 승1 무0.5 패0)")
    print()
    team = []
    # 동점은 패배가 적은 쪽 우선. 승패를 합산해 다수결로 가리므로 기대값이 같다면
    # 분산이 낮은 편이 유리하다 — 물/에스퍼와 비행/전기는 둘 다 105/151점이지만
    # 후자(15패)를 넣는 쪽이 시리즈 승률 84.45% -> 84.67%.
    for c in sorted(COMBOS, key=lambda c: (-score[c], loss[c]))[:10]:
        mark = ""
        pool = COMBO_MONS[c] * SLOTS if dup else COMBO_MONS[c]
        for m in pool:
            if len(team) < SLOTS:
                team.append(m)
                mark = " <-"
        print(f"  {score[c]:.4f}  {pad('/'.join(c), 14)}"
              f"{pad(', '.join(m[1] for m in COMBO_MONS[c]), 40)}{mark}")
    print()
    print(f"최대기대값 엔트리: {', '.join(fmt(m) for m in team)}")
    print(f"  판당 기대점수 {sum(score[key(m[2])] for m in team) / SLOTS:.4f}")
    print()
    if dup:
        print("(--dup: 같은 포켓몬 중복 허용. 최고 조합을 정원 없이 채웁니다)")

    # 최악의 카운터는 하드코딩하지 말고 매번 계산한다. 규칙이나 상성표가
    # 바뀌면 답도 바뀌는데, 문구만 남아 거짓말이 되기 쉽다.
    worst, wl = None, None
    for c in COMBOS:
        if not dup and len(COMBO_MONS[c]) < SLOTS:
            continue  # 중복 금지면 5마리를 채울 수 없는 조합은 애초에 짤 수 없다
        w = sum(1 for m in team if duel(c, key(m[2])) == 1.0)
        l = sum(1 for m in team if duel(c, key(m[2])) == 0.0)
        if worst is None or (w - l) > wl[0] - wl[1]:
            worst, wl = c, (w, l)
    print("주의: 이 엔트리는 상대가 적응하지 않는다는 가정에서만 최적입니다.")
    print(f"      상대가 {'/'.join(worst)} 5마리({', '.join(m[1] for m in COMBO_MONS[worst][:2])} 등)로"
          f" 맞추면 {wl[1]}승 {wl[0]}패로 집니다 (순서 무관).")
    print("      상대도 최적화한다면 인자 없이 실행해 균형 추출을 쓰세요.")
    return 0


def print_nash():
    print("1판 게임의 내쉬 균형. 각 슬롯이 이 확률을 따르므로 어떤 상대 엔트리를 만나도")
    print("판당 기대 승패는 0 이상이다. 5마리는 정원 제약 때문에 독립이 아니라 한 덩어리로 뽑는다.")
    print()
    for c, w in NASH:
        names = ", ".join(m[1] for m in COMBO_MONS[c])
        print(f"  {w:>2}/{NASH_DEN} = {w / NASH_DEN:6.2%}  {pad('/'.join(c), 14)} {names}")
    print()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    dup = "--dup" in argv
    argv = [a for a in argv if a != "--dup"]
    if "--maxev" in argv:
        return print_maxev(dup)
    if "--rank" in argv:
        return print_ranking()
    seed = None
    if "--seed" in argv:
        i = argv.index("--seed")
        seed = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    rng = random.Random(seed)

    tokens = argv or ["?"] * SLOTS
    if len(tokens) != SLOTS:
        raise SystemExit(f"슬롯 {SLOTS}개를 지정하세요. 모르는 슬롯은 ? 로. (받은 개수: {len(tokens)})")
    opponents = [resolve(t) for t in tokens]
    team = pick(opponents, rng, dup)

    if any(o is None for o in opponents):
        print_nash()
        if dup:
            print("--dup: 슬롯마다 위 분포에서 독립 추출합니다. 시리즈 착취력 정확히 0.")
            print()

    print(f"{pad('슬롯', 5)}{pad('상대', 24)}{pad('추천', 24)}{'내 배율':>8}{'상대 배율':>10}  판정")
    print("-" * 74)
    wins = draws = 0
    known = 0
    for i, (mine, opp) in enumerate(zip(team, opponents), 1):
        row = pad(str(i), 5)
        if opp is None:
            p = nash_prob(mine[2])
            print(f"{row}{pad('? (미지)', 24)}{pad(fmt(mine), 24)}{'':>18}  균형추출 p={p:.1%}")
            continue
        known += 1
        verdict, x, y = outcome(mine, opp)
        wins += verdict == "승"
        draws += verdict == "무"
        print(f"{row}{pad(fmt(opp), 24)}{pad(fmt(mine), 24)}{x:>8g}{y:>10g}  {verdict}")

    print("-" * 74)
    print(f"엔트리: {', '.join(fmt(m) for m in team)}")
    if known:
        print(f"확정 슬롯 {known}판 중 {wins}승 {draws}무 {known - wins - draws}패")
    if known < SLOTS:
        print(f"미지 슬롯 {SLOTS - known}개는 균형에서 무작위 추출 — 재실행하면 달라집니다 (--seed N 으로 고정).")
    return 0


def selftest():
    magneton = BY_NAME["레어코일"]
    assert magneton[2] == ("전기", "강철"), magneton

    # 도감 상세(이미지) 그대로: 레어코일이 2배 이상 때리는 타입
    strong = {t for t in CHART if best_mult(magneton[2], (t,)) >= 2}
    assert strong == {"물", "얼음", "비행", "바위", "페어리"}, strong

    # 받는 피해
    incoming = {t: eff(t, magneton[2]) for t in CHART}
    assert {t for t, v in incoming.items() if v >= 2} == {"불꽃", "격투", "땅"}
    assert {t for t, v in incoming.items() if v == 0} == {"독"}
    assert {t for t, v in incoming.items() if 0 < v <= 0.5} == {
        "노말", "전기", "풀", "얼음", "비행", "에스퍼", "벌레", "바위", "드래곤", "강철", "페어리"}

    # 같은 타입 조합끼리는 항상 무승부
    for _, _, ts in MONS:
        assert duel(ts, ts) == 0.5

    # 물 vs 불: 물 2배, 불 0.5배 -> 물 승
    water, fire = ("물",), ("불꽃",)
    assert best_mult(water, fire) == 2 and best_mult(fire, water) == 0.5
    assert duel(water, fire) == 1.0 and duel(fire, water) == 0.0

    # 서로 0배도 무승부 (노말 vs 고스트)
    assert duel(("노말",), ("고스트",)) == 0.5

    # 아는 슬롯은 확실히 이기는 픽이 와야 하고, 5마리는 중복이 없어야 한다
    charizard = BY_NAME["리자몽"]
    for s in range(20):
        team = pick([charizard, None, None, None, None], random.Random(s))
        assert duel(team[0][2], charizard[2]) == 1.0, team[0]
        assert len({m[0] for m in team}) == SLOTS

    # 내쉬 균형이 진짜 균형인지 유리수로 정확히 재검증.
    # 어떤 순수전략도 이 분포 상대로 기댓값 > 0 을 낼 수 없어야 한다.
    assert sum(w for _, w in NASH) == NASH_DEN
    p = {c: Fraction(w, NASH_DEN) for c, w in NASH}
    for j in COMBOS:
        gain = sum(Fraction(int(duel(j, c) * 2 - 1)) * q for c, q in p.items())
        assert gain <= 0, ("착취 가능:", j, gain)
    assert all(c in COMBO_MONS for c, _ in NASH)

    rows = ranking()
    assert len(rows) == len(MONS) and rows[0][0] == 1
    assert [r[0] for r in rows] == sorted(r[0] for r in rows)      # 순위는 단조
    assert [r[2][3] for r in rows] == sorted((r[2][3] for r in rows), reverse=True)
    for a, b in itertools.combinations(rows, 2):                   # 동점 -> 같은 순위
        assert (a[2][3] == b[2][3]) == (a[0] == b[0]), (a[1][1], b[1][1])
    assert len({r[1][0] for r in rows}) == len(MONS)               # 151마리 전원 정확히 한 번

    assert len(MONS) == 151 and len(CHART) == 18 and len(COMBOS) == 37
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
