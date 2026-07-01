# Leaderboard — retrieval configs (auto-generated)

Recommend section/bge/vector/K5 (cov 0.818, mrr 0.718): only 0.045 behind top-coverage section/bge/hybrid/K8 but ~38% cheaper and ranks answers earlier (§5.1).

| # | chunking | embed | retrieval | K | cov | recall | mrr | cost | n |
|---|---|---|---|---|---|---|---|---|---|
| 1 | section | bge | hybrid | 8 | 0.864 | 0.909 | 0.636 | 17284 | 11 |
| 2 | section | gte | hybrid | 8 | 0.864 | 0.909 | 0.602 | 17284 | 11 |
| 3 | section | minilm | hybrid | 8 | 0.864 | 0.909 | 0.530 | 17284 | 11 |
| 4 | section | bge | vector | 5 | 0.818 | 0.909 | 0.718 | 10802 | 11 |
| 5 | section | bge | vector | 8 | 0.818 | 0.909 | 0.718 | 17284 | 11 |
| 6 | section | gte | vector | 8 | 0.773 | 0.818 | 0.625 | 17284 | 11 |
| 7 | section | bge | hybrid | 5 | 0.773 | 0.818 | 0.621 | 10802 | 11 |
| 8 | section | gte | hybrid | 5 | 0.773 | 0.818 | 0.591 | 10802 | 11 |
| 9 | section | minilm | vector | 8 | 0.773 | 0.818 | 0.546 | 17284 | 11 |
| 10 | section | e5 | hybrid | 5 | 0.773 | 0.818 | 0.523 | 10802 | 11 |
| 11 | section | e5 | hybrid | 8 | 0.773 | 0.818 | 0.523 | 17284 | 11 |
| 12 | section | e5 | vector | 8 | 0.773 | 0.818 | 0.480 | 17284 | 11 |
| 13 | section | e5 | vector | 5 | 0.727 | 0.818 | 0.480 | 10802 | 11 |
| 14 | section | bge | hybrid | 3 | 0.682 | 0.818 | 0.621 | 6481 | 11 |
| 15 | section | gte | vector | 5 | 0.682 | 0.727 | 0.614 | 10802 | 11 |
| 16 | section | gte | hybrid | 3 | 0.682 | 0.818 | 0.591 | 6481 | 11 |
| 17 | section | e5 | hybrid | 3 | 0.682 | 0.727 | 0.500 | 6481 | 11 |
| 18 | section | minilm | hybrid | 5 | 0.682 | 0.727 | 0.500 | 10802 | 11 |
| 19 | section | bge | vector | 3 | 0.636 | 0.727 | 0.682 | 6481 | 11 |
| 20 | section | minilm | bm25 | 8 | 0.636 | 0.636 | 0.412 | 17284 | 11 |
| 21 | section | bge | bm25 | 8 | 0.636 | 0.636 | 0.412 | 17284 | 11 |
| 22 | section | e5 | bm25 | 8 | 0.636 | 0.636 | 0.412 | 17284 | 11 |
| 23 | section | gte | bm25 | 8 | 0.636 | 0.636 | 0.412 | 17284 | 11 |
| 24 | section | gte | vector | 3 | 0.591 | 0.636 | 0.591 | 6481 | 11 |
| 25 | section | minilm | hybrid | 3 | 0.591 | 0.727 | 0.500 | 6481 | 11 |
| 26 | section | minilm | bm25 | 5 | 0.591 | 0.636 | 0.412 | 10802 | 11 |
| 27 | section | bge | bm25 | 5 | 0.591 | 0.636 | 0.412 | 10802 | 11 |
| 28 | section | e5 | bm25 | 5 | 0.591 | 0.636 | 0.412 | 10802 | 11 |
| 29 | section | gte | bm25 | 5 | 0.591 | 0.636 | 0.412 | 10802 | 11 |
| 30 | section | minilm | vector | 5 | 0.545 | 0.636 | 0.518 | 10802 | 11 |
| 31 | section | e5 | vector | 3 | 0.545 | 0.636 | 0.439 | 6481 | 11 |
| 32 | section | minilm | vector | 3 | 0.500 | 0.545 | 0.500 | 6481 | 11 |
| 33 | section | minilm | bm25 | 3 | 0.500 | 0.545 | 0.394 | 6481 | 11 |
| 34 | section | bge | bm25 | 3 | 0.500 | 0.545 | 0.394 | 6481 | 11 |
| 35 | section | e5 | bm25 | 3 | 0.500 | 0.545 | 0.394 | 6481 | 11 |
| 36 | section | gte | bm25 | 3 | 0.500 | 0.545 | 0.394 | 6481 | 11 |
| 37 | char | minilm | bm25 | 8 | 0.409 | 0.455 | 0.331 | 7836 | 11 |
| 38 | char | minilm | bm25 | 3 | 0.364 | 0.364 | 0.318 | 2939 | 11 |
| 39 | char | minilm | bm25 | 5 | 0.364 | 0.364 | 0.318 | 4898 | 11 |
| 40 | char | minilm | vector | 8 | 0.273 | 0.364 | 0.288 | 7836 | 11 |
| 41 | char | minilm | hybrid | 5 | 0.273 | 0.273 | 0.200 | 4898 | 11 |
| 42 | char | minilm | hybrid | 8 | 0.273 | 0.273 | 0.200 | 7836 | 11 |
| 43 | char | minilm | vector | 3 | 0.182 | 0.273 | 0.273 | 2939 | 11 |
| 44 | char | minilm | vector | 5 | 0.182 | 0.273 | 0.273 | 4898 | 11 |
| 45 | char | minilm | hybrid | 3 | 0.136 | 0.182 | 0.182 | 2939 | 11 |

## 미측정 (not measured)
Killed overnight (memory); never scored, never faked:

- char × bge
- char × e5
- char × gte
