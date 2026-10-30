# Evals

A fixed set of questions with known answers, used to measure the chatbot every time the prompt, chunking, retrieval settings or model changes. Scores are reported per category, so a drop points straight at the part of the pipeline that broke.

## Files

| File | What it is | Edit it? |
| --- | --- | --- |
| `sample_golden.yaml` | Hand-written cases: stories, follow-ups, lookalikes, unanswerable, adversarial, injection | Yes |
| `generate_fact_questions.py` | Reads member frontmatter, writes fact and aggregate cases with computed answers, validates all cases | Yes |
| `sample_golden.generated.yaml` | Output of the generator | No, regenerate it |
| `run.py` | Runs the cases through the pipeline and grades them | *Not built yet* |

All cases here use the fictional group in `data/sample/`. Real-data cases live in the private `bg-center-data` repo and use the same format.

## Categories

| Category | Tests | Example | A low score points to |
| --- | --- | --- | --- |
| `single_fact` | One fact about one person | "Where does Pipo live?" | Retrieval basics: chunking, embeddings, top-k |
| `story` | Finding content by meaning | "What happened when Rita and Tomás went to Porto?" | Embedding quality, chunk boundaries |
| `cross_member` | Combining facts across members | "Who is the tallest?" | A limit of plain RAG; fixed by the v2 tools |
| `lookalike` | Similar names or nicknames | "What's the name of Joana's dog?" | Retrieval mixing up people |
| `stale_fact` | Current vs past facts | "Where does Diogo live now?" | Prompt not favouring current facts |
| `follow_up` | Questions that depend on earlier turns | "And what does she do for work?" | The query-rewrite step |
| `unanswerable` | No answer exists in the data | "What's Tomás's blood type?" | Hallucination: system prompt or model |
| `adversarial` | User tries to break the rules | "Ignore your instructions and…" | System prompt robustness |
| `injection` | Instructions hidden inside a document | Last section of `joana.md` | Context not treated as data |

## Case format

Every field is shown below for reference; a real case uses only the ones it needs.

```yaml
- id: lookalike-joana-dog            # unique and stable; results are compared by id
  category: lookalike                 # one of the categories above
  language: en                        # en | pt
  history:                            # optional: earlier user turns, oldest first
    - "Who in the group has a dog?"
  question: "What's the name of Joana's dog?"
  expected_members: [joana]           # docs retrieval should return
  expected_section: stories           # optional
  must_contain: [Hipotenusa]          # every string must appear
  must_contain_any: [Lisboa, Lisbon]  # at least one must appear
  must_not_contain: [Bolacha]         # none may appear
  expect_decline: true                # the answer must say it doesn't know
  judge_rubric: "Says Joana has no pets."   # what the LLM judge checks
```

Every case needs at least one of `must_contain`, `must_contain_any`, `expect_decline` or `judge_rubric`. The generator refuses to run otherwise.

## How cases are graded

Checks run cheapest first, and a case fails on the first check it fails.

1. **Retrieval recall@k.** Were the chunks of every `expected_members` id in the top-k? Deterministic, no LLM.
2. **String checks.** `must_contain`, `must_contain_any`, `must_not_contain`; case- and accent-insensitive, so "Ines" matches "Inês".
3. **Decline check.** For `expect_decline`, a judge model decides whether the answer says it doesn't know.
4. **Rubric.** For `judge_rubric`, a judge model scores the answer against the rubric. The judge is a different, stronger model than the one answering.

Every run is compared against the stuff-everything baseline, where all member docs go into the prompt with no retrieval.

## Usage

Generate fact questions and validate all cases (run after editing any member doc):

```bash
python evals/generate_fact_questions.py
```

Same thing on the private data:

```bash
python evals/generate_fact_questions.py \
  --data ../bg-center-data/members \
  --out ../bg-center-data/golden.generated.yaml \
  --hand-written ../bg-center-data/golden.yaml
```

Run the evals once `run.py` exists (planned interface):

```bash
python evals/run.py --data data/sample/members --mode rag --k 5
python evals/run.py --data data/sample/members --mode baseline
```

## Adding a case

- **A fact from frontmatter?** Don't write it by hand. Add or change the field in the member doc and regenerate.
- **Anything else:** add it to `sample_golden.yaml` under its category, with a new unique `id`.
- **A real failure** (a friend's thumbs-down): write a fictional equivalent here so the public suite learns from it, and the real version in the private repo.
- Never change an existing `id`; results are tracked by it across runs.

## Public vs private

| | Sample track (this folder) | Real track (`bg-center-data`) |
| --- | --- | --- |
| Data | Fictional members | Real friends |
| Runs | Every pull request in CI, and locally | Locally before each release tag |
| Tells you | Whether a change made things better or worse | Whether the bot is good for the real group |
| Committed to the public repo | Everything | Aggregate scores only |