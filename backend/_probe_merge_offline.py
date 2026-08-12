"""离线验证族合并算法 v2：修复分组 bug"""
from collections import defaultdict

ICONS = {
    "号角阴兵": 1.0, "盗匪": 1.0, "叹息球": 1.5, "异色叹息球": 2.0,
    "故纸堆": 2.0, "镜中回忆": 2.0, "旗杆阴兵": 3.0, "贪婪的盗匪": 3.0,
    "异色贪婪的盗匪": 3.5, "厄运替身": 4.0, "缄默的绅士": 5.0,
    "失职的看守": 6.0, "异色失职的看守": 6.5,
}

FAMILIES = {
    "盗匪族": ["盗匪", "贪婪的盗匪", "异色贪婪的盗匪"],
    "看守族": ["失职的看守", "异色失职的看守"],
    "叹息球族": ["叹息球", "异色叹息球"],
}
FAMILY_OF = {}
for fam, members in FAMILIES.items():
    for m in members:
        FAMILY_OF[m] = fam
for s in set(ICONS) - set(FAMILY_OF):
    FAMILY_OF[s] = s


def merge(views, icons=ICONS):
    fam_views = defaultdict(list)
    for v in views:
        per_fam = defaultdict(dict)
        for n, c in v.items():
            fam = FAMILY_OF.get(n, n)
            per_fam[fam][n] = c
        for fam, g in per_fam.items():
            fam_views[fam].append(g)

    merged = {}
    for fam, fvs in fam_views.items():
        members = FAMILIES.get(fam, [fam])
        coexist = any(len(g) >= 2 for g in fvs)
        if coexist:
            for name in members:
                cs = [g[name] for g in fvs if name in g]
                if cs:
                    merged[name] = max(cs)
        else:
            freq = defaultdict(int)
            maxc = defaultdict(int)
            for g in fvs:
                for n, c in g.items():
                    freq[n] += 1
                    maxc[n] = max(maxc[n], c)
            if freq:
                best = max(freq, key=lambda n: (freq[n], maxc[n]))
                merged[best] = maxc[best]
    total = round(sum(icons[n] * c for n, c in merged.items()), 2)
    return merged, total


DATA = {
    "测试2": [
        {"叹息球": 4, "贪婪的盗匪": 2, "盗匪": 2, "厄运替身": 1, "镜中回忆": 3},
        {"贪婪的盗匪": 2, "盗匪": 2, "厄运替身": 1, "镜中回忆": 3},
        {"叹息球": 4, "贪婪的盗匪": 2, "盗匪": 2},
        {"厄运替身": 1, "镜中回忆": 3, "旗杆阴兵": 2},
    ],
    "测试3": [
        {"贪婪的盗匪": 5, "缄默的绅士": 4, "失职的看守": 1, "镜中回忆": 2},
        {"盗匪": 5, "缄默的绅士": 4, "失职的看守": 1, "镜中回忆": 2},
        {"贪婪的盗匪": 5, "缄默的绅士": 4, "失职的看守": 1, "镜中回忆": 2},
        {"贪婪的盗匪": 5, "缄默的绅士": 4, "失职的看守": 1, "镜中回忆": 2},
    ],
    "测试4": [
        {"盗匪": 6, "号角阴兵": 1, "异色失职的看守": 3, "失职的看守": 2},
        {"盗匪": 6, "号角阴兵": 1, "失职的看守": 5},
        {"盗匪": 6, "旗杆阴兵": 3, "号角阴兵": 1},
        {"盗匪": 6, "旗杆阴兵": 3, "号角阴兵": 1, "失职的看守": 1},
    ],
}
EXPECT = {"测试2": 38.5, "测试3": 52, "测试4": 43.5}

for k, views in DATA.items():
    merged, total = merge(views)
    print(f"{k}: 合并={merged} 总分={total} 期望={EXPECT[k]}")
