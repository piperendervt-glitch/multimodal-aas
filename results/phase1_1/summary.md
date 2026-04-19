# Phase 1.1 Single-Node Validation

- Model: `qwen2.5:7b`
- Temperature: 0.1
- Prompts: 5 (see `tests/phase1_1_prompts.json`)

## Headline

- **Total score:** 3.0 / 5.0
- **Go / No-Go:** Go  (>= 3.0 / 5.0)
- **JSON parse success:** 5 / 5
- **Mean response time:** 4.46 s

## Per-prompt results

| id | category | expected (primary / fallback) | predicted | confidence | score | JSON | time (s) |
|---|---|---|---|---|---|---|---|
| p01 | simple_sparrow | sparrow / unknown | sparrow | 0.9 | 1.0 | OK | 7.01 |
| p02 | simple_bulbul | bulbul / unknown | sparrow | 0.9 | 0.0 | OK | 3.80 |
| p03 | ambiguous | unknown / - | both | 1.0 | 0.0 | OK | 3.96 |
| p04 | mixed | both / unknown | both | 1.0 | 1.0 | OK | 3.87 |
| p05 | none | none / unknown | none | 1.0 | 1.0 | OK | 3.68 |

## Model reasoning

- **p01** (simple_sparrow): 記述からスズメの行動が推測できる
- **p02** (simple_bulbul): 灰色の鳥でピーヨと鳴くのはスズメの特徴
- **p03** (ambiguous): スズメとヒヨドリが飛来するという条件から、どちらも来ている可能性が高い
- **p04** (mixed): 記述にスズメとヒヨドリの特徴が両方含まれている
- **p05** (none): 記述に鳥の来訪はなく、現在の状況のみが述べられている
