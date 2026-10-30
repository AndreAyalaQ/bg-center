# Sample data: a fictional friend group

Six invented members used by tests, CI, the public demo and the sample eval track. None of them are real people. Real member docs live in the private `bg-center-data` repo.

Only files in `members/` are ingested. This README is not.

## The group

| Member | Nickname | City | Job | Diet | Height | Pets | Doc language |
| --- | --- | --- | --- | --- | --- | --- | --- |
| João Ferreira | Jota | Lisboa | Physiotherapist | Omnivore | 178 | Dog: Bolacha | PT |
| Joana Ribeiro | Jojo | Porto | UX designer | Vegetarian | 165 | None | EN |
| Rita Carvalho | Pi | Lisboa | Maths teacher | Vegetarian | 160 | Cat: Hipotenusa | PT |
| Tomás Almeida | Pipo | Lisboa | Software engineer | Omnivore | 191 | None | EN |
| Inês Duarte | Nês | Braga | Nurse | Vegetarian | 168 | Cats: Mostarda, Ketchup | PT |
| Diogo Matos | Dudu | Amesterdão | Chef | Pescatarian | 183 | *(field missing)* | EN |

## Planted traps

| Trap | Where | What it tests |
| --- | --- | --- |
| Lookalike names | João / Joana | Retrieval picks the right person; Joana's doc even mentions the mix-up |
| Lookalike nicknames | Pi (Rita) / Pipo (Tomás) | Nickname resolution |
| Shared facts | 3 in Lisboa, 3 vegetarians, 2 with cats | Aggregate questions need several members' chunks |
| Clear extremes | Oldest João, youngest Inês, tallest Tomás, shortest Rita | Aggregates have one correct answer |
| Cross-member stories | Porto 2019 (Rita, Tomás, Joana), the cake (João, Inês, Diogo), Monopoly (Rita, Diogo) | Same event told from several docs and angles |
| Stale fact | Diogo "back home in Coimbra", lives in Amsterdam | Current vs past facts |
| Missing field | Diogo has no `pets` field and no pets mentioned anywhere | The bot declines instead of guessing |
| Language mix | 3 docs in PT, 3 in EN; questions in both | Cross-lingual retrieval and answers |
| Indirect prompt injection | Last section of `joana.md` | The bot ignores instructions found inside documents |

## Regenerating eval questions

After editing any member, run:

```bash
python evals/generate_fact_questions.py
```

It rewrites `evals/sample_golden.generated.yaml`, recomputes every aggregate answer, and checks that all cases reference real member ids.