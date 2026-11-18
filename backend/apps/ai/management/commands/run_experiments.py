import json
import time

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from scipy import sparse

from apps.ai.management.commands.evaluate_recommenders import metrics, top_k
from apps.ai.models import DatasetRating

DATASET = "goodbooks10k"
KS = (10, 30, 50, 100)  # numărul de vecini
LAMS = (0, 10, 30, 100)  # shrinkage
SIZES = (3, 5, 10, 20, None)  # mărimea profilului (None = toate cărțile)
CONFIGS = [(k, lam) for lam in LAMS for k in KS]


def all_neighbors(ui, bidx, rt, n_users, n_books, chunk):
    """Calculează o singură dată similaritățile și derivă vecinii pentru toate configurațiile."""
    sums = np.bincount(ui, weights=rt, minlength=n_users)
    counts = np.bincount(ui, minlength=n_users)
    mean = (sums / np.maximum(counts, 1)).astype(np.float32)
    centered = rt - mean[ui]

    X = sparse.csr_matrix((centered, (bidx, ui)), shape=(n_books, n_users), dtype=np.float32)
    norms = np.sqrt(np.asarray(X.multiply(X).sum(axis=1)).ravel())
    norms[norms == 0] = 1.0
    X = (sparse.diags((1.0 / norms).astype(np.float32)) @ X).tocsr()
    XT = X.T.tocsr()

    ones = np.ones(len(bidx), dtype=np.float32)
    B = sparse.csr_matrix((ones, (bidx, ui)), shape=(n_books, n_users), dtype=np.float32)
    BT = B.T.tocsr()

    out = {}
    for k, lam in CONFIGS:
        kk = min(k, n_books - 1)
        out[(k, lam)] = (np.zeros((n_books, kk), dtype=np.int32), np.zeros((n_books, kk), dtype=np.float32))

    for start in range(0, n_books, chunk):
        end = min(start + chunk, n_books)
        S = (X[start:end] @ XT).toarray()
        N = (B[start:end] @ BT).toarray()  # câți cititori comuni au două cărți
        for i in range(end - start):
            S[i, start + i] = -1.0
        for lam in LAMS:
            Sl = S if lam == 0 else S * (N / (N + lam))
            for k in KS:
                kk = min(k, n_books - 1)
                top = np.argpartition(-Sl, kk, axis=1)[:, :kk]
                vals = np.take_along_axis(Sl, top, axis=1)
                order = np.argsort(-vals, axis=1)
                idx, sim = out[(k, lam)]
                idx[start:end] = np.take_along_axis(top, order, axis=1)
                sim[start:end] = np.maximum(np.take_along_axis(vals, order, axis=1), 0)
    return mean, out


def rank_knn(j_sub, c_sub, j_full, nb_idx, nb_sim, n_books, K):
    if len(j_sub) == 0:
        return []
    score = np.bincount(nb_idx[j_sub].ravel(), weights=(nb_sim[j_sub] * c_sub[:, None]).ravel(), minlength=n_books)
    score[j_full] = -np.inf
    pos = np.flatnonzero(score > 0)
    if len(pos) > K:
        top = pos[np.argpartition(-score[pos], K)[:K]]
        return top[np.argsort(-score[top])].tolist()
    return pos[np.argsort(-score[pos])].tolist()


def fmt(arr, i):
    return f"{arr.mean(axis=0)[i]:.4f}±{arr.std(axis=0)[i]:.4f}"


class Command(BaseCommand):
    help = "Experimente: mai multe seed-uri, variația k și shrinkage, curba de cold start."

    def add_arguments(self, parser):
        parser.add_argument("--seeds", type=int, default=5)
        parser.add_argument("--users", type=int, default=2000)
        parser.add_argument("--k", type=int, default=10, help="K pentru metrici")
        parser.add_argument("--test-ratio", type=float, default=0.2)
        parser.add_argument("--chunk", type=int, default=500)
        parser.add_argument("--out", default="")

    def handle(self, *args, **o):
        t0 = time.time()
        K = o["k"]

        self.stdout.write("Citesc rating-urile...")
        users, ui, bi, rt = {}, [], [], []
        qs = DatasetRating.objects.filter(dataset=DATASET).values_list("external_user_id", "book_id", "rating")
        for u, b, r in qs.iterator(chunk_size=200_000):
            ui.append(users.setdefault(u, len(users)))
            bi.append(b)
            rt.append(r)
        if not rt:
            raise CommandError("Nu există rating-uri. Rulează întâi import_ratings.")
        ui = np.array(ui, dtype=np.int32)
        rt = np.array(rt, dtype=np.float32)
        _, bidx = np.unique(np.array(bi, dtype=np.int64), return_inverse=True)
        n_users, n_books = len(users), int(bidx.max()) + 1

        R = {}  # R[seed][config][size] = [precision, recall, ndcg, hit]; R[seed]["pop"] = [...]
        for seed in range(1, o["seeds"] + 1):
            ts = time.time()
            rng = np.random.default_rng(seed)
            test = rng.random(len(rt)) < o["test_ratio"]
            ui_tr, b_tr, r_tr = ui[~test], bidx[~test], rt[~test]
            ui_te, b_te, r_te = ui[test], bidx[test], rt[test]

            self.stdout.write(f"[seed {seed}] antrenez toate configurațiile...")
            mean, nbs = all_neighbors(ui_tr, b_tr, r_tr, n_users, n_books, o["chunk"])
            pop = np.bincount(b_tr, minlength=n_books).astype(np.float64)

            order = np.argsort(ui_tr, kind="stable")
            su, sb, sr = ui_tr[order], b_tr[order], r_tr[order]
            rel_mask = r_te >= 4
            order2 = np.argsort(ui_te[rel_mask], kind="stable")
            ru, rb = ui_te[rel_mask][order2], b_te[rel_mask][order2]
            train_count = np.bincount(ui_tr, minlength=n_users)
            cand = np.unique(ru)
            cand = cand[train_count[cand] >= 20]
            sample = rng.choice(cand, size=min(o["users"], len(cand)), replace=False)

            # pregătim utilizatorii o singură dată (aceleași subseturi pentru toate configurațiile)
            prepared = []
            for u in sample:
                a, b = np.searchsorted(su, u, "left"), np.searchsorted(su, u, "right")
                j_full, c_full = sb[a:b], sr[a:b] - mean[u]
                a2, b2 = np.searchsorted(ru, u, "left"), np.searchsorted(ru, u, "right")
                rel = set(rb[a2:b2].tolist())
                p = pop.copy()
                p[j_full] = -1.0
                pop_list = top_k(p, 2 * K).tolist()
                perm = rng.permutation(len(j_full))
                prepared.append((j_full, c_full, rel, pop_list, perm))

            acc = {cfg: {m: [] for m in SIZES} for cfg in CONFIGS}
            acc_pop = []
            for j_full, c_full, rel, pop_list, perm in prepared:
                acc_pop.append(metrics(pop_list[:K], rel, K))
                for m in SIZES:
                    sel = perm if m is None else perm[:m]
                    j_sub, c_sub = j_full[sel], c_full[sel]
                    for cfg in CONFIGS:
                        nb_idx, nb_sim = nbs[cfg]
                        knn = rank_knn(j_sub, c_sub, j_full, nb_idx, nb_sim, n_books, K)
                        have = set(knn)
                        rec = knn + [x for x in pop_list if x not in have][: K - len(knn)]
                        acc[cfg][m].append(metrics(rec, rel, K))

            R[seed] = {cfg: {m: np.array(v).mean(axis=0) for m, v in d.items()} for cfg, d in acc.items()}
            R[seed]["pop"] = np.array(acc_pop).mean(axis=0)
            self.stdout.write(f"[seed {seed}] gata în {time.time() - ts:.0f}s (total {time.time() - t0:.0f}s)")

        seeds = list(R)
        pop_arr = np.array([R[s]["pop"] for s in seeds])

        # ---- tabel 1: configurații (profil complet)
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"=== Configurații (K={K}, profil complet, {len(seeds)} seed-uri, medie±std) ==="))
        self.stdout.write(f"{'k':>4s} {'shrink':>7s} {'Precision':>16s} {'Recall':>16s} {'NDCG':>16s} {'HitRate':>16s}")
        rows = []
        for cfg in CONFIGS:
            arr = np.array([R[s][cfg][None] for s in seeds])
            rows.append((arr.mean(axis=0)[2], cfg, arr))
        rows.sort(key=lambda t: -t[0])
        for _, cfg, arr in rows:
            self.stdout.write(f"{cfg[0]:4d} {cfg[1]:7d} {fmt(arr, 0):>16s} {fmt(arr, 1):>16s} {fmt(arr, 2):>16s} {fmt(arr, 3):>16s}")
        self.stdout.write(f"{'pop':>4s} {'-':>7s} {fmt(pop_arr, 0):>16s} {fmt(pop_arr, 1):>16s} {fmt(pop_arr, 2):>16s} {fmt(pop_arr, 3):>16s}")

        best = rows[0][1]
        baseline = (30, 0)
        shown = [baseline] if best == baseline else [baseline, best]

        # ---- tabel 2: cold start
        for cfg in shown:
            label = "configurația inițială" if cfg == baseline else "cea mai bună configurație"
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"=== Cold start: k={cfg[0]}, shrink={cfg[1]} ({label}) ==="))
            self.stdout.write(f"{'cărți în profil':>16s} {'Precision':>16s} {'Recall':>16s} {'NDCG':>16s} {'HitRate':>16s}")
            for m in SIZES:
                arr = np.array([R[s][cfg][m] for s in seeds])
                name = "toate" if m is None else str(m)
                self.stdout.write(f"{name:>16s} {fmt(arr, 0):>16s} {fmt(arr, 1):>16s} {fmt(arr, 2):>16s} {fmt(arr, 3):>16s}")
            self.stdout.write(f"{'populare':>16s} {fmt(pop_arr, 0):>16s} {fmt(pop_arr, 1):>16s} {fmt(pop_arr, 2):>16s} {fmt(pop_arr, 3):>16s}")

        if o["out"]:
            def pack(a):
                return {"precision": round(float(a[0]), 4), "recall": round(float(a[1]), 4),
                        "ndcg": round(float(a[2]), 4), "hit_rate": round(float(a[3]), 4)}
            payload = {
                "settings": {"seeds": seeds, "users": o["users"], "K": K, "test_ratio": o["test_ratio"]},
                "popularity": {"mean": pack(pop_arr.mean(axis=0)), "std": pack(pop_arr.std(axis=0))},
                "configs": {
                    f"k={cfg[0]},shrink={cfg[1]}": {
                        ("all" if m is None else str(m)): {
                            "mean": pack(np.array([R[s][cfg][m] for s in seeds]).mean(axis=0)),
                            "std": pack(np.array([R[s][cfg][m] for s in seeds]).std(axis=0)),
                        }
                        for m in SIZES
                    }
                    for cfg in CONFIGS
                },
            }
            with open(o["out"], "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.stdout.write(f"Rezultate salvate în {o['out']}")
        self.stdout.write(self.style.SUCCESS(f"Gata în {time.time() - t0:.0f}s."))