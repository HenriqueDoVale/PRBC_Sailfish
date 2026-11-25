# Thesis writing pack

> ## IMPORTANT — Narwhal Sailfish latency measured before 20 October
>
> Every Narwhal Sailfish latency figure measured before 20 October 2026 used
> its **default header settings** (`header_size` 50 B, `max_header_delay`
> 5,000 ms). These are built for high load. At low and moderate load they
> inflate its latency **four to five times**: tuned to 30 B and 1,000 ms, its
> end-to-end latency fell from 3,877 to 789 ms at n=10 and from 4,637 to
> 1,159 ms at n=50 (`EVALUATION_RESULTS.md` section 8.2).
>
> - **Default-configuration Narwhal latencies are not its performance** and
>   must never be presented as such. Where they still appear (comparisons B
>   and C, the original workload sweep, the fixed-latency-budget study) they
>   are marked, and every latency ratio against Narwhal derived from them is
>   an **upper bound on our advantage, not its size**.
> - **The authoritative latency comparison with Narwhal is section 8.3** of
>   `EVALUATION_RESULTS.md`: fixed load, tuned configuration.
> - **Narwhal throughput figures are unaffected** — tuning costs it
>   throughput at high load, so its defaults are its best for throughput.


> ## IMPORTANT — one protocol, no development history
>
> Write the thesis as if the protocol in `PSEUDOCODE.md` is the one every
> experiment used. In the thesis text, never say that anything in our
> protocol was fixed, changed, added later or re-measured, and never say
> that a result comes from an earlier build, version, commit or date.
>
> - The history in these files ("Changes on …" sections, "Before / Now"
>   tables, "earlier build" / "new build" labels, commit ids, dates) is
>   background so you can update what you have already drafted. It is not
>   thesis content.
> - Where `EVALUATION_RESULTS.md` labels a figure "earlier build", use the
>   figure and drop the label. Those figures are conservative or within
>   run-to-run variation of the current protocol.
> - A table that only compares builds (`EVALUATION_RESULTS.md` §8.7) is not
>   presented as before and after. Use it at most as design rationale:
>   checking every vote's signature one at a time in the consensus loop
>   would limit the round rate at n=50, so the implementation checks
>   signatures on the connection reader tasks.
> - Reasons are welcome ("a vote signs the round and source as well as the
>   hash, so it cannot be presented as a vote for another slot"). Histories
>   are not ("we found that … and changed it").
> - Comparison C (the initial vs the revised implementation) is a
>   deliberate design comparison, not a fix history; keep it as
>   `EVALUATION_RESULTS.md` describes it.
> - The Narwhal tuning note above is about the baseline's configuration and
>   is unaffected by this rule.


Everything the writing-assistant session needs, and nothing it shouldn't
have. Upload all of these at the start of that session, plus the preliminary
report PDF (not in this repo — attach `Preliminary_Report.pdf` from your own
files).

## Read in this order

| # | File | What it is |
|---|---|---|
| 1 | `THESIS_CONTEXT.md` | **The brief.** How the session should work, the fixed table of contents, corrections to earlier notes, source material for chapters 1–3, the as-built implementation for chapter 6, and the communication-cost analysis for chapters 4–5. |
| 2 | `EVALUATION_RESULTS.md` | **The single authority for every evaluation number.** Three parts: method (testbeds, protocol variants, the latency comparability problem), the four comparisons, then further results — the throughput model, an open question about Narwhal, the workload sweep, the clean-hardware check and the supporting studies. Closes with the weak cells and what must not be overstated. |
| 3 | `PSEUDOCODE.md` | The algorithms as implemented, with source line references. The authority for the implementation chapter (6). |
| 3a | `PSEUDOCODE_PAPER.md` | The same protocol at the level of the Sailfish paper, five figures: Sailfish's three with our changes marked, plus the PRBC broadcast and recovery. Use these for chapters 4 and 5; `PSEUDOCODE.md` stays the reference for chapter 6. |
| 3b | `CORRECTNESS_OUTLINE.md` | The correctness outlines: PRBC alone for section 4.8, PRBC-Sailfish for chapter 5. Lemmas and proof sketches citing `PSEUDOCODE_PAPER.md` lines. |
| 3c | `IMPLEMENTATION_CHAPTER.md` | Section-by-section plan for chapter 6, modelled on the implementation chapter of André Santos's dissertation: initialization, tasks and channels, traffic planes, data structures, sampling, garbage collection, gaps, baselines and instrumentation, challenges. Captions for Figures 6.1–6.3, which the user adds as screenshots. |
| 4 | `RECOVERY_TESTING.md` | Recovery mechanism validated against a hypergeometric model, and how recovery works since the 27 October rewrite. |
| 5 | `PRBC_C_TESTING.md` | The `PRBC_SAMPLE_C` redundancy sweep — cost and benefit. |
| 6 | `OBJECTIVE1_2_ANALYSIS.md` | Why Narwhal's latency is higher and its network lower, read from its source. |
| 7 | `OBJECTIVE4_TESTING.md` | Throughput under a fixed 1,000 ms latency budget. |

Files 4–7 are the detailed studies behind the summary rows in
`EVALUATION_RESULTS.md` §13. Use them when a section needs the full method,
not just the headline.

## Deliberately not in this pack

- **`CLAUDE.md`** — operational notes: cluster IPs, commands, code layout.
  No use for prose.
- **`RESULTS_INVENTORY.md`** — the audit trail. It contains superseded
  figures, invalid runs and resolved conflicts, all deliberately preserved.
  Giving it to a writing session would actively mislead it.
- **`THIS_WEEKS_WORK.md`** — working notes, now superseded by
  `EVALUATION_RESULTS.md` for anything that would be written up.

## If two files disagree

`EVALUATION_RESULTS.md` wins on numbers. `PSEUDOCODE.md` wins on algorithms.
`THESIS_CONTEXT.md` wins on everything else. If a needed figure is in none of
them, ask — do not estimate.

## Changes on 22 October — apply to anything already drafted

- **Maximum throughput (`EVALUATION_RESULTS.md` §8.1):** every value is now
  presented as that protocol's ceiling. Remove any ≥ or "at least" from
  drafted text, tables or figures.
- **Latency comparison with Narwhal (§3, §8.3):** both protocols are now
  measured from the moment a batch is ready. Narwhal's batch-fill wait is
  subtracted from its figure; nothing is added to ours. The old interval
  ("+ full window", "worst case") is withdrawn.
- **Headline numbers (§8.3):** superseded by the 28 October changes below.

## Changes on 27 October — recovery (answers your question on the two gaps)

Both gaps in `RECOVERY_TESTING.md` (recovery fetched only the vertex; it
could run out of candidates and never restart) **are fixed in the code**. So
state the guarantee for the implementation, and do not list either as a
chapter 6 limitation.

- **Batch fetch.** A party that holds a certified vertex but not its batch
  asks the vertex's voters for the batch by its digest, and checks the batch
  against that digest. The vertex itself is the proof that the batch is
  needed: its digest carries a quorum of votes.
- **No responder quorum.** A voter answers with the vertex or batch whenever
  it holds it. The requester already holds a quorum of votes for the hash and checks
  everything against it. (Before, a responder needed a quorum of its own,
  which Byzantine voters could prevent.)
- **Never gives up.** After a full pass over the voters with no valid answer,
  recovery starts again, waiting twice as long each pass (up to 8 ×
  `RECOVERY_TIMEOUT_MS`). A late valid answer from anyone already asked is
  accepted.
- **Retention.** Correct parties keep delivered vertices and batches for R
  rounds after ordering (default 50, like Narwhal's `gc_depth`). This is the
  one bound to state: a party more than R rounds behind would need state
  transfer, which is not implemented. Narwhal has the same boundary.
- **The guarantee:** if a correct party hash-commits a vertex, it eventually
  holds the vertex and its batch after GST, provided it is less than R rounds
  behind the other correct parties. Argument: at least f+1 of the quorum's voters
  are correct, each stored the batch before voting, and each keeps it for R
  rounds; the requester keeps asking all of them.
- **Change only the text that describes recovery** (the protocol, the
  pseudocode, the guarantee and the limitations). **Do not change any
  number, table or result.** The recovery experiments stand as written.
- **Use `PSEUDOCODE.md` Figure 6** (rewritten) for the algorithm. Figures 1,
  3, 4 and 5 changed only where they touch recovery or retention. Figure 4 now
  notes that the "timeout suspension" lines have no effect; do not describe
  them as doing work.
- Two recovery limitations remain, both about speed: no "I don't have it"
  reply, and one request at a time (`THESIS_CONTEXT.md`, as-built gap 5).

## Changes on 27 October, later — correctness fixes

Writing the correctness argument showed four places where the code did not do
what the proof needs. All four are now in the code, and `PSEUDOCODE.md` was
rewritten to match (Figures 3, 4 and 5 changed, Figure 7 is new, every line
number moved). `THESIS_CONTEXT.md` ("Correctness fixes", under chapter 6)
explains each one.

- **Votes sign (round, source, hash)**, and **sources sign their vertices**.
- **Leader skipping as in Sailfish**, with the **no-vote certificate**. It is
  implemented now: remove any "the no-vote certificate is not implemented"
  from drafted text.
- **Vote rule and certificate fetch.** A party votes only when it has
  certified every parent; a missing certificate is fetched; ordering waits
  for a leader's whole history and orders it by (round, source).
- **Change only the text that describes the protocol** (chapters 4–6,
  pseudocode, correctness outline, as-built gaps). **No number, table or
  result changes**: the fixes act only when a party misbehaves or crashes.
- Use the line numbers of the new `PSEUDOCODE.md` only. Any line number
  quoted from the earlier version is wrong now.
- **Quorum.** Every threshold (votes, round advance, timeout and no-vote
  certificates) is q = n − f, the same threshold Narwhal uses; it equals
  2f + 1 when n = 3f + 1. In the thesis write q or n − f whenever n is
  general.
- **New: `CORRECTNESS_OUTLINE.md`** for section 4.8 and chapter 5's
  correctness outline. Two separate sets of lemmas: PRBC on its own
  (chapter 4), and PRBC-Sailfish using PRBC's theorems as a black box
  (chapter 5). Follow its "Do not claim" list.

## Changes on 28 October — batching, the gap, and new results

The protocol's batching is now as the supervisor asked, and the evaluation
was re-measured. Describe all of it as how the protocol works (the
one-protocol rule at the top of this file).

- **Batches are built when a party proposes** (`PSEUDOCODE.md` lines 18–22):
  transactions are always available, and the load only decides how many go
  into a batch. A party never waits for a batch to fill.
- **Minimum gap between a party's proposals** (line 36): Δ = n²/25 ms, so
  every machine runs at about half its CPU. Each round costs about n²
  vote-signature checks whatever the batch size; that is why the gap exists.
- **Votes for an already-certified slot are dropped unchecked** (line 80).
  It changes nothing the protocol decides.
- **New results** (`EVALUATION_RESULTS.md`): §8.1 maximum throughput, §8.2
  Narwhal's batch delay per size, §8.3 the headline (3.9× at 20 replicas,
  5.1× at 30, 2.7× at 50), §8.6 at 200k. Replace every earlier headline
  ratio in drafted text. Maximum throughput is described as comparable.
- **Sections that no longer describe our protocol** (listed at the top of
  `EVALUATION_RESULTS.md`): do not cite their figures for our latency,
  round rate or throughput; the author decides whether they are re-measured
  or dropped.
- `THESIS_CONTEXT.md` carries the new protocol text ("One batch per vertex",
  "Minimum gap between proposals") and what the results now say about each
  sentence of the abstract.

## Changes on 29 October — every correct party votes (your Lemma 4.6 question)

You were right: the proof of Lemma 4.6 did not cover the case you found, and
neither did the code. A party that collected q votes before it could vote
delivered and never voted, so Byzantine parties sending their votes to that
party alone could leave every other correct party one vote short.

- **The code now does what the proof needs** (rule (C6) in
  `CORRECTNESS_OUTLINE.md`): a party that certifies first delivers at once
  and still votes once the vote rule holds. A copy fetched by recovery
  carries no source signature and is never voted for; the source's own
  propose is.
- **`PSEUDOCODE.md`:** lines 48, 55, 57–59, 72–75, 100–102 and 271 changed in
  place, and a paragraph after Figure 3 explains them. No line number moved,
  so every line reference in other files still holds. The code references
  (`:NNNN`) are refreshed.
- **`CORRECTNESS_OUTLINE.md`:** new rule (C6); a new proof of Lemma 4.6
  (replace your `% CHECK` copy with it) and a remark after it; the remark
  after Theorem 4.7 now says totality fails only with a Byzantine sender;
  Lemma 5.11 cites line 75 instead of 72.
- **No number, table or result changes.**
- Present (C6) as how the protocol works, with its reason, never as a fix
  (the one-protocol rule).

## 29 October, later — your quorum and throughput questions

**Quorum in the older runs.**

- **Recovery, n = 7–10: the rows still describe the protocol, including the
  n = 8 bump.** Byz1 sends its vertex to the 2f + 1 lowest-ID peers whatever
  the quorum: that is the fault's fan-out, not the quorum. So who receives
  the vertex and who relays it are unchanged. The quorum only decides whether
  the vertex is certified: an excluded peer counts the 2f + 1 recipients'
  votes plus the proposer's own, 2f + 2, against q = n − f. That is enough at
  n = 7, 8 and 10 (at n = 8 the proposer's vote is the sixth), so those
  predictions are unchanged. At n = 9 one more vote is needed, from an
  excluded peer a relay reached; the prediction moves from 12.8% to 12.2%
  (observed 11.2%). `RECOVERY_TESTING.md` now states this: n = 9 predicted
  12.2%, the bump 1.85× predicted against 1.84× observed, observed values
  1.0–2.4 points below prediction.
- **Comparisons A and B at n = 20 and 30: no**, as the status box at the top
  of `EVALUATION_RESULTS.md` already says; the quorum (13 and 19 instead of
  14 and 21) is one more difference. Do not cite them for our protocol.

**Throughput** is counted from the batches themselves: each replica sums the
transactions in every batch it orders once the batch is local, divides by
the 60-second window, and we report the median across replicas. With full
fixed-size batches this equals blocks × transactions per block; with batches
that follow the load only the per-batch count is exact. The definition is
now in `EVALUATION_RESULTS.md` §3.

## 29 October, later still — pseudocode in the Sailfish paper's style

- **Chapters 4 and 5 use `PSEUDOCODE_PAPER.md`**: Sailfish's Figures 1–3 with
  our changes marked (`+` added, `~` changed), plus Figure 4 (PRBC broadcast)
  and Figure 5 (recovery and certificate fetch). Lines run 1–146 across the
  five figures, as in the paper. Drop the `+`/`~` marks or render them as
  shading.
- **`CORRECTNESS_OUTLINE.md` now cites these lines.** Replace every line
  number in drafted proofs with the new ones. The only `PSEUDOCODE.md`
  references left are in its implementation notes, for chapter 6.
- `PSEUDOCODE.md` stays the reference for chapter 6 (implementation).
- Sailfish's two extra timeout rules (echo a timeout after f + 1, forward a
  timeout certificate) are not in the protocol and are left out; Figure 2's
  notes say so.

## 30 October — the name APRBC

The current broadcast, the version this pack describes, is called **APRBC**.
This reverses the earlier rule "never write APRBC".

- **Figures say APRBC.** Figure 6.2 uses `APRBCSailfish`, `APRBCMessage` and
  `APRBCDag`. The source code still spells them `PRBC…`.
- **The prose is not settled yet.** The other pack files still say PRBC and
  PRBC-Sailfish. Do not rename anything in the text until the user confirms
  how far the name goes; if a passage needs it, ask.
- "PRBC-orig" stays out of the thesis, and the one-protocol rule is unchanged.

## Five decisions still open

Named in `THESIS_CONTEXT.md` and worth settling early, because they change
how chapters read:

1. **"ProSailfish" or "PRBC-Sailfish"?** The table of contents says one, the
   abstract and code say the other.
2. **Was the sampling designed to be VRF-based?** The implementation is
   deterministic and hash-derived, with no proof. Chapter 4 and chapter 6
   must agree on whether that is a simplification or an unfinished piece.
3. **Does the abstract's stated mechanism change?** It attributes the
   narrowing advantage to quadratic message growth; the measured mechanism
   (`EVALUATION_RESULTS.md` §9) is that the round rate falls with n, which
   is better supported. New evidence (§8.7): at n=50 the round rate was
   limited by n² vote-signature checks per round. That is quadratic
   per-round growth, but on the vote path, not in dissemination.
4. **The abstract's latency claim.** "Significantly lower finalization
   latency for small-to-medium systems (10–30 replicas)" is supported:
   measured (`EVALUATION_RESULTS.md` §8.3), 3.9× at 20 replicas and 5.1× at
   30, and still 2.7× at 50. "Narrows as the system scales" holds only from
   30 to 50 replicas; say the advantage is smallest at 50.
5. **The abstract's throughput sentence.** "Narwhal Sailfish achieves higher
   throughput at scale" is not supported, and neither is the opposite. Replace
   it with comparable maximum throughput (`EVALUATION_RESULTS.md` §8.1): ours
   measured higher, but with much larger batches than Narwhal was tested
   with.
