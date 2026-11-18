import json
import time

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from scipy import sparse

from apps.ai.models import DatasetRating, RecommendationModel

DATASET = "goodbooks10k"
SYSTEMS = ["popularitate", "item-kNN", "item-kNN + popularitate"]


def neighbors(ui, bidx, rt, n_users, n_books, k, chunk):
    """Cosinus ajustat item-item pe datele primite. Întoarce (media pe utilizator, vecini, similarități)."""
    sums = np.bincount(ui, weights=rt, minlength=n_users)
    counts = np.bincount(ui, minlength=n_users)
    mean = (sums / np.maximum(counts, 1)).astype(np.float32)
    centered = rt - mean[ui]

    X = sparse.csr_matrix((centered, (bidx, ui)), shape=(n_books, n_users), dtype=np.float32)
    norms = np.sqrt(np.asarray(X.multiply(X).sum(axis=1)).ravel())
    norms[norms == 0] = 1.0
    X = (sparse.diags((1.0 / norms).astype(np.float32)) @ X).tocsr()
    XT = X.T.tocsr()

    kk = min(k, n_books - 1)
    nb_idx = np.zeros((n_books, kk), dtype=np.int32)
    nb_sim = np.zeros((n_books, kk), dtype=np.float32)
    for start in range(0, n_books, chunk):
        end = min(start + chunk, n_books)
        S = (X[start:end] @ XT).toarray()
        for i in range(end - start):
            S[i, start + i] = -1.0
        top = np.argpartition(-S, kk, axis=1)[:, :kk]
        vals = np.take_along_axis(S, top, axis=1)
        order = np.argsort(-vals, axis=1)
        nb_idx[start:end] = np.take_along_axis(top, order, axis=1)
        nb_sim[start:end] = np.maximum(np.take_along_axis(vals, order, axis=1), 0)
    return mean, nb_idx, nb_sim


def top_k(scores, k):
    idx = np.argpartition(-scores, k)[:k]
    return idx[np.argsort(-scores[idx])]


def metrics(rec, rel, K):
    hits = [1 if x in rel else 0 for x in rec[:K]]
    h = sum(hits)
    dcg = sum(1.0 / np.log2(i + 2) for i, x in enumerate(hits) if x)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(K, len(rel))))
    return h / K, h / len(rel), dcg / idcg, 1.0 if h else 0.0


class Command(BaseCommand):
    help = "Evaluează recomandările (Precision@K, Recall@K, NDCG@K) pe un set de test ascuns."

    def add_arguments(self, parser):
        parser.add_argument("--k-values", default="5,10,20")
        parser.add_argument("--neighbors", type=int, default=30)
        parser.add_argument("--test-ratio", type=float, default=0.2)
        parser.add_argument("--users", type=int, default=3000, help="Câți utilizatori de test se evaluează")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--chunk", type=int, default=500)
        parser.add_argument("--out", default="", help="Fișier JSON în care se salvează rezultatele")
        parser.add_argument("--save", action="store_true", help="Salvează metricile în modelul activ")

    def handle(self, *args, **o):
        t0 = time.time()
        Ks = [int(x) for x in o["k_values"].split(",")]
        maxK = max(Ks)
        rng = np.random.default_rng(o["seed"])

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

        # împărțire: o parte din rating-urile fiecărui utilizator se ascunde
        test = rng.random(len(rt)) < o["test_ratio"]
        ui_tr, b_tr, r_tr = ui[~test], bidx[~test], rt[~test]
        ui_te, b_te, r_te = ui[test], bidx[test], rt[test]
        self.stdout.write(f"  antrenare: {len(r_tr):,} rating-uri, test: {len(r_te):,} ({time.time() - t0:.0f}s)")

        self.stdout.write("Antrenez modelul doar pe datele de antrenare...")
        mean, nb_idx, nb_sim = neighbors(ui_tr, b_tr, r_tr, n_users, n_books, o["neighbors"], o["chunk"])
        self.stdout.write(f"  gata ({time.time() - t0:.0f}s)")

        pop = np.bincount(b_tr, minlength=n_books).astype(np.float64)

        order = np.argsort(ui_tr, kind="stable")
        su, sb, sr = ui_tr[order], b_tr[order], r_tr[order]
        rel_mask = r_te >= 4
        order2 = np.argsort(ui_te[rel_mask], kind="stable")
        ru, rb = ui_te[rel_mask][order2], b_te[rel_mask][order2]

        train_count = np.bincount(ui_tr, minlength=n_users)
        cand = np.unique(ru)
        cand = cand[train_count[cand] >= 10]
        sample = rng.choice(cand, size=min(o["users"], len(cand)), replace=False)
        self.stdout.write(f"Evaluez {len(sample):,} utilizatori de test...")

        acc = {s: {K: [] for K in Ks} for s in SYSTEMS}
        seen_items = {s: {K: set() for K in Ks} for s in SYSTEMS}

        for u in sample:
            a, b = np.searchsorted(su, u, "left"), np.searchsorted(su, u, "right")
            J, c = sb[a:b], sr[a:b] - mean[u]
            a2, b2 = np.searchsorted(ru, u, "left"), np.searchsorted(ru, u, "right")
            rel = set(rb[a2:b2].tolist())

            p = pop.copy()
            p[J] = -1.0
            pop_list = top_k(p, 2 * maxK).tolist()

            score = np.bincount(nb_idx[J].ravel(), weights=(nb_sim[J] * c[:, None]).ravel(), minlength=n_books)
            score[J] = -np.inf
            pos = np.flatnonzero(score > 0)
            if len(pos) > maxK:
                knn = pos[np.argpartition(-score[pos], maxK)[:maxK]]
                knn = knn[np.argsort(-score[knn])].tolist()
            else:
                knn = pos[np.argsort(-score[pos])].tolist()

            for K in Ks:
                lists = {
                    "popularitate": pop_list[:K],
                    "item-kNN": knn[:K],
                }
                base = knn[:K]
                have = set(base)
                lists["item-kNN + popularitate"] = base + [x for x in pop_list if x not in have][: K - len(base)]
                for s, rec in lists.items():
                    acc[s][K].append(metrics(rec, rel, K))
                    seen_items[s][K].update(rec)

        results = {}
        self.stdout.write("")
        for K in Ks:
            self.stdout.write(self.style.SUCCESS(f"--- K = {K} ---"))
            self.stdout.write(f"{'sistem':28s} {'Precision':>10s} {'Recall':>8s} {'NDCG':>8s} {'HitRate':>8s} {'Acoperire':>10s}")
            for s in SYSTEMS:
                arr = np.array(acc[s][K])
                m = arr.mean(axis=0)
                cov = len(seen_items[s][K]) / n_books
                results.setdefault(s, {})[str(K)] = {
                    "precision": round(float(m[0]), 4),
                    "recall": round(float(m[1]), 4),
                    "ndcg": round(float(m[2]), 4),
                    "hit_rate": round(float(m[3]), 4),
                    "coverage": round(cov, 4),
                }
                self.stdout.write(f"{s:28s} {m[0]:10.4f} {m[1]:8.4f} {m[2]:8.4f} {m[3]:8.4f} {cov:10.4f}")

        payload = {
            "settings": {
                "test_ratio": o["test_ratio"],
                "neighbors": o["neighbors"],
                "test_users": int(len(sample)),
                "seed": o["seed"],
                "relevant": "rating >= 4 în setul ascuns",
            },
            "results": results,
        }
        if o["out"]:
            with open(o["out"], "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.stdout.write(f"Rezultate salvate în {o['out']}")
        if o["save"]:
            model = RecommendationModel.objects.filter(is_active=True, type="collaborative").first()
            if model:
                model.metrics = payload
                model.save(update_fields=["metrics"])
                self.stdout.write("Metricile au fost salvate în modelul activ.")
        self.stdout.write(self.style.SUCCESS(f"Gata în {time.time() - t0:.0f}s."))