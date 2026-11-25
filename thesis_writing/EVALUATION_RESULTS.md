# Evaluation results — PRBC-Sailfish

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


> ## IMPORTANT — which sections describe the protocol as it is
>
> A party builds its batch when it proposes, from the load since its previous
> proposal, and proposes at most once every Δ = n²/25 ms (`THESIS_CONTEXT.md`,
> "One batch per vertex" and "Minimum gap between proposals"). These
> sections were measured that way and are the results to use: **§8.1**
> (maximum throughput), **§8.2** (Narwhal's configuration, including its batch
> delay per size), **§8.3** (the headline) and **§8.6 at 200k**.
>
> These sections measured our protocol with fixed-size batches. **Do not cite
> their figures for our latency, round rate or throughput** until the author
> decides whether to re-measure or drop them: comparisons A, B and C (§4–6),
> §8.4, §8.5's comparison with our protocol, §8.6 at 150k, §9's fitted
> values, §11 and the PRBC figures in §13. Their Narwhal-only and
> Sailfish-only content (§8.5's trace, §10, §12) stands.
>
> Comparisons A–C also counted votes against a quorum of 2f + 1: 13 and 19
> at n = 20 and 30, where the protocol uses n − f, 14 and 21 (at n = 10 both
> are 7). Our Sailfish baseline uses 2f + 1 at every size; where n ≠ 3f + 1
> that is one vote below a safe quorum, which can only make the baseline
> faster.
>
> Per the README's one-protocol rule, never write that the batching or the
> gap changed; describe both as how the protocol works.

**This file is the single authority for every evaluation number in the
thesis.** If a figure appears here and also somewhere else, this one wins.
If a number is not here, ask — do not take it from another document and do
not estimate it.

Compiled 16 October 2026, last updated 28 October, from the full run record.

**Suggested shape for chapter 7** — the results chapter presents four
comparisons and nothing else:

| § | content | source |
|---|---|---|
| 7.1 | Experimental setup — testbeds, metrics, how latency is compared (both from batch ready), run counts | §1–3 |
| 7.2 | Comparison A — probabilistic vs reliable broadcast | §4 |
| 7.3 | Comparison B — both against Narwhal | §5 |
| 7.4 | Comparison C — what the architecture change bought | §6 |
| 7.5 | Why n=50 is absent from A–C — the 10-machine limit | §7 |
| 7.6 | Comparison D — on 50 machines | §8 |
| 7.7 | **The recovery mechanism** | `RECOVERY_TESTING.md` |
| 7.8 | Summary | — |

§9–13 of this file are supporting material that may be drawn on where a
section needs it, not sections in their own right. **§14 and §15 are
guardrails for drafting, not thesis content** — they exist so nothing
indefensible gets written, and they do not appear in the thesis. Working notes, superseded
figures and the audit trail live in `RESULTS_INVENTORY.md`, which is *not*
part of this pack.

---

## 1. Testbeds — never mix them in one table

| ID | What it is | Node placement |
|---|---|---|
| **T2** | 10 machines, GCP europe-west4-a, `n2d-highcpu-8`, 8 vCPU / 8 GB | 1 / 2 / 3 nodes per machine at n = 10 / 20 / 30 |
| **T3** | 50 machines, GCP `n2`, 8 vCPU | **1 node per machine at every n** |

Two effects separate them, and they pull opposite ways:

- **Hardware.** At n=10 both are 1:1, so density is ruled out — yet the
  ceiling fell about 11%, from ~136–138k on T2 to ~120–125k on T3. T3's
  machines are slower for this workload (`n2d` → `n2`).
- **Density.** At n ≥ 20, T2 packs several nodes per machine. This dominates:
  T3's n=20 ceiling is ~120k against T2's ~80k — 50% better on slightly
  weaker hardware, because a node with a whole machine beats two sharing one.

Everything below: 512 B transactions, 60-second measurement window, no
injected faults, LAN. Our figures are medians across nodes.

---

## 2. Protocol variants

| Name | What it is |
|---|---|
| **PRBC-orig** | First PRBC-Sailfish. Payload carried inline in every consensus message. |
| **APRBC** | The current protocol. Three-plane TCP, batch broadcast before vertex creation, vertex carries a 32-byte digest only, voting gated on local batch availability. |
| **Sailfish-inline** | Our Sailfish, payload inline, signed-vote RBC. The deterministic-broadcast baseline. |
| **Narwhal** | `nibeshrestha/sailfish`, run through its own harness. The state-of-the-art baseline. |

> **These are internal labels, not thesis names.** "APRBC" and "PRBC-orig"
> distinguish two versions of our own protocol during development; the thesis
> calls the contribution by its proper name throughout (see the naming
> decision in `THESIS_CONTEXT.md`). Where the prose needs to distinguish the
> two versions — comparison C does — say "the initial implementation" and
> "the revised implementation", or similar. Never write "PRBC-orig" in the
> thesis. **Superseded in part on 30 October:** the user now calls the current
> broadcast APRBC, and the figures use that name; see `README.md`.

---

## 3. Metrics, and the one comparability problem

| metric | starts when | ends |
|---|---|---|
| our consensus latency | vertex created | committed |
| our E2E latency | **batch ready** | committed |
| Narwhal consensus latency | **header formed** | committed |
| Narwhal E2E latency | **client sends a transaction** | committed |
| **Narwhal, from batch ready** — what we compare against | **batch sealed** | committed |

**Throughput.** Each of our replicas counts the transactions in every batch
it orders, read from the batch itself, once the batch is local. Throughput
is that count divided by the 60-second window, reported as the median across
replicas. Batch sizes follow the load, so this per-batch count replaces
"blocks × transactions per block"; the two agree whenever every batch is
full, as in the runs with fixed-size batches. Narwhal's throughput is the
figure its own benchmark harness reports.

**The asymmetry.** Both protocols batch transactions. Each of our parties
builds a batch when it proposes, holding the transactions that arrived since
its previous proposal; each Narwhal worker seals a batch when it holds 500
transactions or its batch delay expires. Narwhal's E2E clock starts when the
client sends a transaction, so it includes the time that transaction waits in
the worker for its batch. Ours starts when the batch is built, and our
transactions are generated at that moment, so no transaction is seen waiting.
Comparing the two raw figures would charge Narwhal for a wait our measurement
leaves out.

**How we compare: both from batch ready.** We subtract Narwhal's batch-fill
wait from its E2E latency, so both figures run from the moment a batch is
ready to commit. **Our figure is never modified; nothing is added to it.**

**Narwhal's fill wait** is taken from its own logs where a run was traced
(client send to batch sealed, `trace_narwhal.py`). Otherwise it is estimated
as half its batch interval: a batch seals when it holds 500 transactions or
when `max_batch_delay` expires, whichever is first, and a transaction arriving
at a steady rate waits half of that on average:
`fill = min(500 × n / rate, max_batch_delay) / 2`. The estimate matched the
log in every run where both exist:

| run | estimate | measured in Narwhal's logs |
|---|---|---|
| n=10, 100k, batch delay 200 ms | 25 ms | 22 ms |
| n=50, 75k, batch delay 400 ms | 167 ms | 168 ms |
| n=50, 150k, batch delay 400 ms | 83 ms | 86 ms |

**Why this is fair.** The fill wait comes from batching, not from anything
specific to Narwhal. In a deployment our transactions would also arrive one
at a time and a replica would wait for its batch in the same way; our
generator hides that wait. Taking it out of Narwhal's figure measures both
protocols over the same span, batch ready to commit, which is the part where
the two designs differ. (A transaction of ours would wait half the gap Δ on
average: 2, 8, 18 and 50 ms at n = 10, 20, 30 and 50.)

**Do not compare our E2E against Narwhal's consensus latency.** Narwhal's
consensus clock starts when the header is formed, after the batch has waited
for acknowledgements and for the next header, so that comparison would leave
out a stage our E2E includes.

**The pairing rule, in one place.** Against **Narwhal**: our E2E against
Narwhal's E2E from batch ready. Against **our own Sailfish**, see §4.1: its
consensus latency spans the same interval as our end-to-end, so both pairings
are reported. Never mix pairings within one table.

**Sailfish-inline has no end-to-end figure at all.** Its payload travels
inside the consensus message, so there is no separate batch step and the
binary reports only consensus latency. This is why comparison A (§4) and the
inline column of comparison B (§5) carry consensus latency alone. It is a
property of the protocol, not a gap in the measurements — do not ask for it
and do not derive it.

**Also report consensus latency separately.** Both protocols define it as
"proposal object formed → committed", which is genuinely analogous. It
favours Narwhal in places. Reporting it is what makes the E2E claim credible.

**Limitation to state.** Both figures leave out the wait before a
transaction is in a batch: on average half the gap for ours (2 / 8 / 18 /
50 ms at n = 10 / 20 / 30 / 50) and Narwhal's fill wait at its chosen batch
delays (4 / 16 / 36 / 125 ms, §8.2). Making the generator stream and
timestamp individual transactions would remove the need for any adjustment —
future work.

**Change, 22 October.** Earlier versions reported our latency as an interval:
measured, up to measured plus one full batch interval, the wait of the
*first* transaction in a batch. That is a worst case, and the supervisors
questioned adding a figure that large to ours (at n=10, about half our
consensus time). It is replaced by the method above. No conclusion changes.

---

# The four comparisons

## 4. Comparison A — probabilistic broadcast vs reliable broadcast

**Testbed T2, n = 10/20/30, each protocol at its own ceiling. Both carry
payload inline and use Sailfish ordering, so the broadcast primitive is the
only difference.** 3 runs per cell.

### 4.1 Which metrics pair with which — read before using the table

`sailfish.rs` measures **no end-to-end latency at all**; it prints only
`Consensus TPS` and `Consensus latency`. That is not a gap in the record — in
an inline protocol the payload *is* the vertex, so there is no dissemination
step between "batch ready" and "vertex created" and there is nothing separate
to measure.

The consequence matters: **Sailfish's consensus latency spans the same
interval as our *end-to-end* latency**, not our consensus latency. Our
consensus clock starts after the batch has gone out; Sailfish has no such gap
to exclude. So there are two defensible pairings and they answer different
questions.

| n | our cons. | our E2E | Sailfish cons. | ordering layer<br>(cons vs cons) | delivery<br>(our E2E vs their cons) |
|---|---|---|---|---|---|
| 10 | ~69 ms | ~98 ms | 90.2 ms | 1.31× | **0.92× — Sailfish faster** |
| 20 | ~256 ms | ~312 ms | 907 ms | 3.54× | **2.91×** |
| 30 | ~442 ms | ~531 ms | 1,943 ms | 4.40× | **3.66×** |

**Report both, and say what each measures.** Consensus-against-consensus
compares the ordering layers; our-E2E-against-their-consensus compares
delivery and is the stricter test. The claim survives either: the advantage
grows monotonically with committee size.

**The n=10 reversal must be stated, not smoothed over.** Under the delivery
pairing a ten-node committee is slightly faster with reliable broadcast. This
is consistent with everything else at that size — the architecture change
also cost 6.6% throughput at n=10 (§6) — and the explanation is the same: a
ten-node committee does not have the communication problem these mechanisms
solve. Independent corroboration: the WAN study separately found Sailfish
slightly faster than ours at LAN at every rate, attributing it to the absence
of a separate dissemination step.

### 4.2 Throughput

| n | PRBC-orig | Sailfish-inline | gain |
|---|---|---|---|
| 10 | 146,500 | 92,825 | **1.58×** |
| 20 | 79,667 | 19,458 | **4.09×** |
| 30 | 69,475 | 13,100 | **5.30×** |

Inline round rate collapses 18.6 → 2.1 → 0.9 per second.
Input rates: ours unlimited / 80k / 70k; inline 90k / 20k / 14k.

**The claim this supports:** the advantage grows monotonically with committee
size on both throughput and latency, which is the direction the complexity
analysis predicts — reliable broadcast forwards n² payload copies, ours
forwards (n−1) + s(s−1), which is linear in n (§13.2).

**Caveat that must be stated.** Density rises 1 → 2 → 3 nodes per machine
across these rows, and inline Sailfish is bandwidth-bound, so part of the
widening is contention rather than protocol. §12 is the clean-hardware check:
the effect holds but is milder.

## 5. Comparison B — both against Narwhal, same testbed

> **Narwhal ran with its default header settings in comparisons B and C**
> (`max_header_delay` 5,000 ms, untuned `header_size`). Section 8.2 shows these
> inflate its latency at moderate load: on the 50-machine cluster, tuning cut
> its end-to-end latency from 3,877 to 789 ms at n=10 and from 4,637 to
> 1,159 ms at n=50, four to five times. Its latency figures here, marked †,
> are therefore **default-configuration values**, and the latency ratios
> against Narwhal in these two sections are **upper bounds on our advantage,
> not its size.** They also still include Narwhal's batch-fill wait (§3),
> which was not subtracted here. The corrected comparison is section 8.3. Throughput figures
> are unaffected: tuning costs Narwhal throughput at high load, so its
> defaults are its best for throughput.

Throughput, and latency under both pairings. Narwhal reports consensus and
end-to-end; we report both; Sailfish-inline reports consensus only, which per
§4.1 spans the same interval as an end-to-end figure.

| n | TPS: ours / inline / Narwhal | Narwhal TPS lead |
|---|---|---|
| 10 | 146,500 / 92,825 / 192,400 | 1.31× |
| 20 | 79,667 / 19,458 / 167,631 | 2.10× |
| 30 | 69,475 / 13,100 / 123,200 | 1.77× |

**Latency — end-to-end against end-to-end**, the pairing to use against
Narwhal (§3):

| n | PRBC-orig E2E | Narwhal E2E † | our lead (upper bound) |
|---|---|---|---|
| 10 | ~98 ms | ~3,800 ms | 38.8× |
| 20 | ~312 ms | ~3,050 ms | 9.8× |
| 30 | ~531 ms | ~3,400 ms | 6.4× |

**Latency — consensus against consensus**, the ordering-layer cross-check:

| n | PRBC-orig | Sailfish-inline | Narwhal † |
|---|---|---|---|
| 10 | ~69 ms | 90.2 ms | ~706 ms |
| 20 | ~256 ms | 907 ms | ~1,070 ms |
| 30 | ~442 ms | 1,943 ms | ~1,500 ms |

Ratios against Narwhal on this pairing: 10.2× / 4.18× / 3.39×.

**What it shows:** the trade-off before the architecture change. Narwhal
leads throughput everywhere. We lead latency against its *default*
configuration; how much of that lead survives tuning is answered in section
8.3, not here. Note that inline Sailfish is *slower
than Narwhal* on consensus latency at n=30 (1,943 against ~1,500 ms) — the
deterministic-broadcast baseline loses to both by that committee size.

## 6. Comparison C — what the architecture change bought

**Same testbed. APRBC replaces PRBC-orig.**

The default-settings notice at the top of section 5 applies here too.

| n | APRBC TPS / cons / E2E | Narwhal TPS / cons† / E2E† | TPS | cons (upper bound) | E2E (upper bound) |
|---|---|---|---|---|---|
| 10 | 136,900 / 71.3 / 163 ms | 192,400 / ~706 / ~3,800 ms | 1.41× N | 9.9× us | 23.3× us |
| 20 | 119,317 / 165.9 / 228 ms | 167,631 / ~1,070 / ~3,050 ms | 1.40× N | 6.5× us | 13.4× us |
| 30 | 89,508 / 330.7 / 423 ms | 123,200 / ~1,500 / ~3,400 ms | 1.38× N | 4.5× us | 8.0× us |

Against PRBC-orig on the identical testbed — the before/after that isolates
the change:

| n | TPS | consensus latency |
|---|---|---|
| 10 | **−6.6%** | +3.3% (slightly worse) |
| 20 | **+49.8%** | **−35.2%** |
| 30 | **+28.8%** | **−25.2%** |

**What it shows:** the change costs a little at n=10 and pays increasingly
from n=20 up, and Narwhal's throughput lead flattens to a constant ~1.4× at
every size. The latency columns against Narwhal are default-configuration
upper bounds; the point of this section is the before/after of our own
protocol, which is unaffected.

**Note for the prose.** §4 says the primitive helps *least* at n=10 (1.58×);
this section says the architecture change actively *cost* 6.6% there. Both
are true and consistent — a 10-node committee does not have the
communication problem these changes solve — but stated carelessly they read
as contradictory.

---

## 7. The n=50 limit of the 10-machine testbed

n=50 is deliberately absent from comparisons A, B and C. At five nodes per
machine, that testbed could not sustain a 50-node committee:

- APRBC was **bistable** — 63,467 tx/s once in seven attempts, the other six
  between 21,925 and 57,250.
- Narwhal reported **η > 1** in five of eleven runs (up to 1.051), which is
  not physically possible and indicates a measurement-window failure.
- Sailfish-inline **deadlocked at every rate tried**.

**This is a result, not a missing cell.** It is the limit of that environment
and the reason the evaluation moved to 50 physical machines. Note also that
the inline deadlock does **not** reproduce on T3 — so every deadlock claim
must be scoped to the 10-machine testbed.

---

## 8. Comparison D — APRBC vs Narwhal on 50 machines

All cells measured or re-verified on a cluster confirmed free of stale
processes (1 and 15 October).

**Configuration.** Ours: each party builds its batch when it proposes, from
the load since its previous proposal (capped at `--n-tx` transactions), and
proposes at most once every Δ = n²/25 ms (4 / 16 / 36 / 100 ms at n = 10 /
20 / 30 / 50). Each round costs every party about n² vote-signature checks
whatever the batch size, so Δ sets the round rate and the CPU; with this rule
each machine runs at about half its CPU (measured 50–58% at 100k). Vote
signatures are checked on the connection reader tasks (§8.7). Narwhal: header
settings tuned (§8.2), 256,000-byte (500-transaction) batches, and its batch
delay chosen per size as its best setting that carries the load (§8.2). A
configuration counts only if at least 95% of the offered load is committed.
**In the thesis, do not distinguish builds or present any of this as a
change** (README).

### 8.1 Maximum throughput

Highest delivered rate with at least 95% of offered load committed, one
measured run per cell. Ours with batches built from the load, capped at 4,000
transactions, and the gap rule; Narwhal with its default header settings (its
best for throughput, section 8.2) and 500-transaction batches. **Every cell is
that protocol's maximum throughput (its ceiling) at that size. Do not mark any
cell with ≥ or "at least".** For ours the next higher offered rate did not
complete (350k at n=10, 330k at n=30, 240k at n=50); at n=20 the 310k run is
already at the limit (96.3% delivered, batches at the cap).

| n | ours | Narwhal | ours / theirs |
|---|---|---|---|
| 10 | 297,787 (at 300k) | 243,467 (at 250k) | 122% |
| 20 | 298,565 (at 310k) | 252,146 (at 260k) | 118% |
| 30 | 277,597 (at 280k) | 241,016 (at 252k) | 115% |
| 50 | 198,483 (at 200k) | 194,695 (at 200k) | 102% |

- Runs next to the threshold: Narwhal n=10 at 275k delivered 260,601 (94.7%);
  Narwhal n=30 re-run on the clean cluster delivered 94.3% at 231k and 93.2%
  at 261k. So Narwhal's n=10 and n=30 maxima are fuzzy by several percent.
- Narwhal's batch size (256,000 B, 500 tx) was never varied on T3, so its
  figures are the best measured, not established maxima. Ours reaches its
  maximum with batches of up to 3,700–3,800 transactions at n=10–20.
- The two throughput definitions differ by a few percent (section 3). A
  difference within about 6% is not a ranking.

**What it shows: maximum throughput is comparable.** Our measured maximum is
15–22% higher at 10–30 replicas and level at 50, but we reach it with batches
of up to about 3,800 transactions, while Narwhal was measured only with
500-transaction batches: its maximum with larger batches was not measured.
So the claim is "comparable", never "higher".

**Latency near maximum throughput — not tabulated, one sentence.** The two
maxima sit at different offered rates, so a latency column here would
mislead. The sentence to write:

> *Near maximum throughput both protocols commit in several hundred
> milliseconds: ours in 342–751 ms, Narwhal Sailfish with tuned header
> settings in about 400–445 ms at 20–30 replicas while giving up 5–15% of its
> throughput. Our latency advantage is a moderate-load result.*

Sources: ours at its maximum, n=10 360.0 ms, n=20 750.6 ms, n=30 434.0 ms,
n=50 342.4 ms. Narwhal, 21 October, tuned (header 30 B, delay 1,000 ms, batch
delay 50 ms): n=20 at 260k delivered 245,667 tx/s (94.5%), 444 ms from batch
ready; n=30 at 252k delivered 215,551 (85.5%), 396 ms from batch ready. **Never
cite Narwhal's default-settings latency at these rates (3,043 / 2,611 /
2,041 ms).**

### 8.2 Narwhal's configuration — tuned for moderate load

Narwhal Sailfish's defaults, `header_size` 50 B and `max_header_delay`
5,000 ms, are built for high load. At low and moderate load they dominate its
latency, which is why its latency appeared to *fall* as offered load rose
(section 10).

- `header_size` 50 B means a primary may not propose until it holds two
  32-byte digests. At low load the round leader is often late, so rounds stall
  or skip it, and everything behind that leader waits for the next one that
  commits.
- `max_header_delay` 5,000 ms then puts a multi-second tail on non-leader
  batches.

Tuned to `header_size` 30 B (one digest suffices) and `max_header_delay`
1,000 ms. At n=50, 75,000 tx/s, measured 20 October:

| config | header interval | leader latency | non-leader latency | E2E mean | E2E p90 | delivered |
|---|---|---|---|---|---|---|
| default | 1,944 ms | none committed | — | 4,637 ms | 8,693 ms | 91.1% |
| header 30 B | 697 ms | 257 ms | 5,063 ms | 3,522 ms | 9,433 ms | 98.9% |
| header 30 B + delay 1 s | 501 ms | 214 ms | 1,308 ms | **1,159 ms** | **1,808 ms** | 97.8% |

**At high load the tuned configuration costs Narwhal throughput:** at n=50 /
150k it delivered 92.8% of offered load, below the 95% threshold, against
99.1% with the defaults. So the tuned configuration is used for every Narwhal
figure at moderate load, and the defaults for ceilings and high-load figures,
each protocol at its best for the load in question, as our batch size is.

**Every moderate-load Narwhal latency in earlier versions of this file used
the defaults and overstated its latency several-fold. None of them may be
cited as its performance.**

**Batch delay, chosen per size.** With the header settings tuned, Narwhal's
batch delay sets how often it seals a batch, and so its round rate, as our
gap sets ours. At 100,000 tx/s it was run at our gap and at larger delays.
Per size we keep the setting with the lowest latency from batch ready among
those that commit at least 95% of the load (bold):

| n | batch delay | delivered | E2E | fill | from batch ready |
|---|---|---|---|---|---|
| 10 | 4 ms | 97.6% | 484 ms | 2 ms | 482 ms |
| 10 | **8 ms** | 99.0% | 477 ms | 4 ms | **473 ms** |
| 10 | 32 ms | 99.4% | 737 ms | 16 ms | 721 ms |
| 10 | 200 ms | 99.7% | 789 ms | 22 ms, measured | 767 ms |
| 20 | 16 ms | 90.3% ✗ | 91 ms | 8 ms | 83 ms |
| 20 | **32 ms** | 99.2% | 170 ms | 16 ms | **154 ms** |
| 20 | 200 ms | 99.7% | 627 ms | 50 ms | 577 ms |
| 30 | 36 ms | 91.1% ✗ | 222 ms | 18 ms | 204 ms |
| 30 | 50 ms | 90.7% ✗ | 202 ms | 25 ms | 177 ms |
| 30 | **72 ms** | 98.2% | 468 ms | 36 ms | **432 ms** |
| 30 | 200 ms | 98.9% | 806 ms | 75 ms | 731 ms |
| 50 | 100 ms | 87.1% ✗ | 675 ms | 50 ms | 625 ms |
| 50 | 200 ms | 98.2% | 773 ms | 100 ms | 673 ms |
| 50 | **400 ms** | 99.0% | 744 ms | 124 ms, measured | **621 ms** |

Fill waits estimated per section 3 unless marked measured. Smaller delays
give Narwhal lower latency at n=20–50 but do not carry the load. At n=10 its
E2E is about 440 ms above its own consensus latency at every delay tried
(consensus 44 / 42 / 278 ms at 4 / 8 / 32 ms): that time is spent between the
client and the header, not in consensus, and was not traced.

### 8.3 Fixed load, each at its best configuration — the headline

Both at 100,000 tx/s, each at its best configuration (sections 8 and 8.2).
Every point committed at least 98% of the offered load. Both latencies are
measured from the moment a batch is ready (section 3).

| n | ours (gap Δ) | Narwhal from batch ready (batch delay) | result |
|---|---|---|---|
| 10 | 11.9 ms (4 ms) | 473 ms (8 ms) | ours 40× faster — see below |
| 20 | 39.2 ms (16 ms) | 154 ms (32 ms) | **ours 3.9× faster** |
| 30 | 84.8 ms (36 ms) | 432 ms (72 ms) | **ours 5.1× faster** |
| 50 | 226.1 ms (100 ms) | 621 ms (400 ms) | **ours 2.7× faster** |

Delivered: ours 99,975 / 99,923 / 99,830 / 99,489; Narwhal 99,020 / 99,192 /
100,134 (of 102,000 offered) / 99,029 tx/s. Our CPU: 57.8 / 54.7 / 51.3 /
49.9% of the machine. Narwhal's CPU was not measured.

- **n=10: do not lead with 40×.** Narwhal's consensus takes 42 ms there;
  most of its 473 ms is spent before consensus, at every batch delay tried,
  and was not traced (section 8.2).
- **The 95% rule matters.** Narwhal reaches 83 ms at n=20 and 177 ms at n=30,
  but only while committing about 90% of the load (section 8.2). Against
  those, ours would be about 2× faster. State the rule wherever the ratios
  appear.
- **Ours is held at about half the CPU** by the gap rule, while Narwhal gets
  the batch delay that works best for it. If anything, that favours Narwhal.
- Our latency is about 2.2–2.6 round periods (11.9 / 4.6, 39.2 / 16.9,
  84.8 / 37.6, 226.1 / 102 ms): the gap sets the round period.
- Our consensus latency (vertex created → committed) was not recorded for
  these runs; section 3 asks for it next to the E2E figure. **Open.**

**This is the comparison to lead with.** The sentence to write: *at 100,000
transactions per second, with each protocol at its best configuration and
measured from the moment a batch is ready, our latency is 3.9× lower than
Narwhal Sailfish's at 20 replicas, 5.1× at 30 and 2.7× at 50; at 10 replicas
the difference is larger still.*

**Superseded, do not cite:** every earlier figure of this section (127.2 /
252.4 / 386.0 / 651.2 ms; 6.0×, 2.3×, 1.9×, level) and the figures 131.4 /
265.2 / 417.4 / 1,310.2 ms.

### 8.4 Matched batch size at the original operating points — removed

This comparison fixed our protocol at 500-transaction batches, which it does
not have: its batch size follows the load (section 8). Do not cite any figure
from earlier versions of this section (131.4 / 393.7 / 552.5 / 903.2 ms;
5.8×, 1.3×, 1.2×, 1.1×).

### 8.5 Latency anatomy — corrected

**An earlier version of this section attributed Narwhal's latency to its
delivery-acknowledgement wait. That was wrong.** Every sample transaction was
traced through Narwhal's own logs (client send, batch sealed, digest placed in
a header, commit), all logged on one machine and so free of clock skew. The
long pre-consensus stage was mostly a digest waiting for the *next header*,
because under the defaults headers formed slowly:

| n=50, 75k | header interval | digests per header | sealed to digest in header, median |
|---|---|---|---|
| default | 1,944 ms | 5.91 | 1,666 ms |
| tuned | 501 ms | 1.52 | 31 ms |

At n=50 / 150k with the defaults, the median of that stage (165 ms) is about
half the header interval (389 ms), which is what a digest arriving at a random
moment waits on average. **The acknowledgement path itself takes tens of
milliseconds.**

**Our side of the anatomy is not measured for the current configuration.**
The earlier table here compared our consensus and pre-consensus stages with
Narwhal's, with our batches at a fixed 500 transactions; it is withdrawn. What
carries over: our latency is a small number of round periods (about 2.2–2.6,
section 8.3), and the gap Δ sets the round period.

### 8.6 High load at n=50

Where Narwhal's defaults are its best valid configuration (section 8.2):

| rate | ours | Narwhal E2E, default | Narwhal from batch ready | result |
|---|---|---|---|---|
| 150k | not measured | 848-1,274 ms (two runs) | 762-1,188 ms (fill 86 ms, measured) | — |
| 200k | 342.4 ms (99.2% delivered) | 1,145 ms | 1,082 ms (fill 63 ms, estimated) | ours 3.2× faster |

Ours at 200k is its maximum-throughput run (section 8.1). The high-load rows
at n=10/20/30 in earlier versions of this file used Narwhal's defaults and
were not re-checked against the tuned configuration. They are omitted.

### 8.7 What limited our round rate at n=50

In the earlier build every replica checked every vote's signature one at a
time in the consensus loop: 50 × 50 = 2,500 Ed25519 checks per round at n=50,
against 100 at n=10. At 100k with 550-transaction batches, 22 October:

| run | delivered | rounds/s | E2E |
|---|---|---|---|
| earlier build | 25%, collapsed | 0.9 | — |
| earlier build, smaller relay sample (s=8) | 49%, collapsed | 1.8 | — |
| earlier build, 256 B transactions | 77% | 2.8 | — |
| earlier build, 256 B + smaller sample | 71% | 2.6 | — |
| earlier build, vote signatures off (diagnostic only) | 99% | 3.6 | 694 ms |
| **new build, signatures on, checked on reader tasks** | **99%** | **3.6** | **705 ms** |

Shrinking the payload, by halving transaction size or the relay sample,
helped but did not sustain the load; removing the checks did. Checking on the
per-peer reader tasks, which run in parallel on the machine's eight cores,
recovers nearly all of that while every vote is still verified. With it,
500-transaction batches also hold at n=50 (99.2%, 4.0 rounds/s, 651 ms,
section 8.3).

**So the earlier n=50 loss was an implementation bottleneck, not the
protocol's payload amplification.** Our extra payload over Narwhal is about
2.8× at n=50 and 3.2× at n=10 (section 13.2): it does not grow with n.

**For the thesis:** chapter 6 describes vote verification as built, on the
reader tasks, and may give this section's finding as the reason: checking
every vote's signature one at a time in the consensus loop would limit the
round rate at n=50. Do not say that any result predates it, and give no
before/after figure.

**The same cost is why the protocol has a minimum gap between proposals**
(section 8): every round costs each party about n² signature checks whatever
its batch size, so the gap, not the batch size, decides how much CPU the
protocol uses.

---

# Further results

## 9. The governing throughput model

Our throughput obeys `ceiling = rounds_max x n_tx x n`, where `rounds_max` is
the round rate bounded by round-trip time and dissemination. It has predicted
every measured ceiling to within about 1%, and was used to *predict* before
measuring — not fitted afterwards.

| n | n_tx | rounds_max | predicted | measured |
|---|---|---|---|---|
| 10 | 500 | 24 | 120k | ~120k |
| 10 | 1,000 | 19.2 | 192k | 191,983 |
| 10 | 2,000 | 11.6 | 232k | 232,033 |
| 10 | 4,000 | 6.2 | 248k | 248,000 |
| 30 | 500 | 7.3 | 109.5k | **109,167** |
| 50 | 500 | 3.0 | 75k | 74,167 |
| 50 | 2,000 | 1.5 | 150k | 146,700 |

Earlier build (section 8). The new build raises `rounds_max` at n=50: 500-transaction batches sustain 4.0 rounds per second at 100k (section 8.3), against 3.0 before.

**The consequence that matters.** The collection window is
`window = n_tx x n / rate`. Substituting `rate = ceiling` gives

> **window = 1 / rounds_max**

— at saturation the collection window equals the round period, *independent
of batch size*. Enlarging batches raises throughput and slows rounds in exact
proportion, so latency-at-ceiling does not improve. Confirmed at n=50:
500-tx gives 3.0 rounds/s and 903 ms; 2,000-tx gives 1.5 rounds/s and
1,796 ms.

Since a commit takes roughly two rounds plus the window, our latency floor is
about `3 / rounds_max`, and `rounds_max` falls with n. Checked: n=10 with
rounds_max 24 predicts 125 ms against 125.8 measured; n=50 with 3.0 predicts
1,000 ms against 903 measured.

**This matters for the abstract.** The abstract attributes the narrowing
advantage to "quadratic-ish per-round message growth". The measured mechanism
is sharper: `rounds_max` falls as n grows, so the latency floor rises with
committee size regardless of tuning. **Ask before drafting — the two
explanations are not the same and the measured one is better supported.**

---

## 10. Narwhal's load-dependence — resolved

Narwhal's latency appeared to fall as offered load rose: at n=50, 5,043 ms at
75k against 848 ms at 150k. **It was its default configuration.** With
`header_size` 30 B and `max_header_delay` 1,000 ms it reaches 1,159 ms at
75k, about what its defaults give at 150k, so once configured for the load its
latency is roughly flat. The defaults are built for high load: there, digests
arrive so quickly that neither parameter binds; at low load both dominate.
Evidence in sections 8.2 and 8.5.

The batch collection window is ruled out as the cause. Between 75k and 150k it
halves, from 168 to 86 ms mean wait, which is about 3% of the change.

Our protocol shows the same direction at fixed batch size, for an explained
reason: at n=50 with 2,000-transaction batches, 100k gives 2,453 ms and 150k
gives 1,796 ms, tracking the round rate (1.0 against 1.5 per second) almost
exactly. Both systems are pacing-limited below their ceilings; Narwhal's
defaults added a much larger penalty on top.

---

## 11. The original workload sweep — needs re-running

The supervisor's stated experiment: fix the setup, sweep 1,000 to 20,000
tx/s, show our latency beats Narwhal's. n=10, one node per machine.

| offered tx/s | APRBC | Narwhal (default settings) |
|---|---|---|
| 1,000 | 9,456 ms | 2,966 ms |
| 5,000 | 1,900 ms | 2,385 ms |
| 10,000 | 950 ms | 1,696 ms |
| 15,000 | 634 ms | 652 ms |
| 20,000 | 475 ms | 1,228 ms |

We win from 5k to 20k, by 2.6× at 20k. **Narwhal wins at 1,000 tx/s, and that
row must be reported and then explained** — it is the batch-pacing artefact
(§13.1), not protocol behaviour, and the cap fixes it.

⚠ **This whole table predates the pacing fix and should be re-run before
publication.** Its Narwhal column also used default header settings, so its latency
is inflated (see the note at the top of this file). Flag it to the user rather than presenting it as current.

---

## 12. Inline Sailfish on clean hardware

Run on T3 at a matched 20,000 tx/s so density is not a factor.

| n | TPS | η | consensus | rounds/s | network TX | machine CPU |
|---|---|---|---|---|---|---|
| 10 | 20,600 | 103% | 445.0 ms | 4.1 | 1,600 Mbps | 13.3% |
| 20 | 20,458 | 102% | 926.5 ms | 2.1 | 3,324 Mbps | 25.0% |
| 30 | 20,258 | 101% | 1,357.8 ms | 1.4 | 4,907 Mbps | 38.9% |
| 50 | 15,608 | **78%** | 4,369.5 ms | 0.8 | 5,595 Mbps | 43.5% |

**Important methodological point.** At this load both protocols are
*pacing-limited*, not capacity-limited: measured round rate matches the
generator's batch-formation rate `500 × n / rate` at every size (4.1 vs 4.0,
2.1 vs 2.0, 1.4 vs 1.33, 0.8 vs 0.8). So round rate here measures the load
generator, not either protocol. The protocol-controlled quantity is latency
*above* the collection window: 195 / 427 / 608 / **3,120 ms** at
n=10/20/30/50, against APRBC's 510 ms at n=50 with its pacing cap engaged.

**The wall is network, not CPU.** Per-node transmission scales linearly at
roughly 160 Mbps per committee member. Extrapolated, n=50 needs ~8 Gbps to
keep up; it delivered 5,595 Mbps and fell to 78%, with CPU at only 43.5%.

---

## 13. Supporting studies

Each has a dedicated document in this pack with full method and data.

**All four used the current protocol (APRBC) on testbed T2, at n=10 —
n=7–10 for recovery.** They describe the protocol the thesis presents, so
they are directly usable, but their figures must not be placed in a table
with comparison D's, which is T3. The visible consequence: the fixed-budget
study reports a ~136–138k ceiling at n=10 where §8.1 gives ~120–125k for the
same committee size. That is the `n2d` → `n2` hardware difference in §1, not
a contradiction — but say which testbed each figure comes from wherever both
appear.

| study | headline | source |
|---|---|---|
| **Batch-pacing fix** | n=50 at 20k: E2E 2,693.9 → **1,175.7 ms** (−56%) with throughput flat (19,175 → 19,670) and round rate 0.8 → 2.0 | §13.1 below |
| **Recovery vs theory** | hypergeometric model predicts the recovery rate within 1.0–2.4 pp at n = 7/8/9/10, including a non-monotonic bump at n=8 predicted *before* measurement | `RECOVERY_TESTING.md` |
| **Redundancy dial** | `PRBC_SAMPLE_C` swept over 7 values; dissemination fits `73.7 + 7.393·s²` Mbps; **C ≈ 1.8 is the sweet spot** — 65% less recovery need for 30% more network | `PRBC_C_TESTING.md` |
| **Fixed latency budget** | **Conclusion withdrawn.** Measured against Narwhal's default settings (ours ~136–138k tx/s within 1,000 ms, Narwhal ~19–30k). Tuned, Narwhal reaches 789 ms at 100k tx/s on the 50-machine cluster, inside the budget. Our own figures stand; the 4.6–7× comparison must not be cited | `OBJECTIVE4_TESTING.md` |
| **Network cost** | ours 258.4 Mbps per node against Narwhal's 67–70 at matched throughput — **~3.7× more**, agreeing with code reading and the fitted model | `OBJECTIVE1_2_ANALYSIS.md` |
| **Amplification** | predicted \|S\| + \|S\|² vs measured: 30/26.0, 56/50.9, 72/69.2, 110/114.1 at n=10/20/30/50. Formulas written before the runs; within 13% | §13.2 below |

### 13.1 The batch-pacing fix

Our generator paced itself at one batch every `n_tx × n / rate` ms, so at low
per-node rates a node idled waiting for a full batch. At 1,000 tx/s over 10
nodes that is a five-second wait, and it is the source of the 9,456 ms
outlier in the original workload sweep. `MAX_BATCH_DELAY_MS` caps the
interval and shrinks the batch proportionally, preserving the configured
rate. Off by default.

| n=50, 20,000 tx/s | tx/block | TPS | consensus | E2E | rounds/s |
|---|---|---|---|---|---|
| cap disabled | 500 | 19,175 | 2,490.7 ms | 2,693.9 ms | 0.8 |
| cap 500 ms | 200 | 19,670 | 1,010.5 ms | **1,175.7 ms** | 2.0 |

Local check (n=7, 1,000 tx/s): 3,932.1 → **950.0 ms**, throughput 950 → 962.

This also revises the scaling claim: the n=50 versus n=10 gap at the same
offered rate narrows from 5.7× to 2.5×.

### 13.2 Amplification — how many times one batch crosses the network

**The correct formula is `(n − 1) + s(s − 1)`,** where `s = ⌈1.4·√n⌉` is the
relay committee size (5, 7, 8, 10 at n = 10, 20, 30, 50).

It follows directly from the code. The originator broadcasts the complete
batch to **every** other replica — `prbc_sailfish.rs:922-926`,
`DispatchTarget::All`, unconditional and independent of consensus. Each of
the s committee members selected for that digest then
forwards it to its own sample of s, minus itself.

Verified against the binary's own Dissemination-plane byte counters,
amplification computed as plane TX ÷ the node's own generated payload:

| run | s | predicted | measured | ratio |
|---|---|---|---|---|
| n=10, 100k | 5 | 29 | 32.5 | 1.120 |
| n=20, 260k | 7 | 61 | 63.8 | **1.046** |
| n=30, 100k | 8 | 85 | 88.8 | **1.045** |

The constant ~4.5% excess at n=20 and n=30 is framing and header overhead.
n=10 is a weaker check because the committee term is small there.

> **An earlier version of this file gave `|S| + |S|²`, taken from a shared
> campaign artifact. That formula omits the initial broadcast entirely, and
> its error grows with n (1.08 → 1.14 → 1.23 against the same measurements).
> It is wrong for this implementation. Do not use it, and do not use its
> measured column (26.0 / 50.9 / 69.2 / 114.1), which is measuring something
> other than batch amplification.**

**Consequence for the prose:** the abstract, the Resumo and §1.3 are correct
as written — the batch *is* multicast to all replicas and then relayed by a
committee. Chapters 4–6 and chapter 7 agree on this formula.

Not yet computed: n=50. The per-plane byte counters from a T3 n=50 run would
give the fourth point; predicted is 139.

# Caveats

## 14. Weak cells — do not build an argument on these

| cell | why |
|---|---|
| section 8.6, n=50 @150k Narwhal | two runs gave 848 and 1,274 ms |
| section 8.3, n=50 Narwhal | two runs at 400 ms gave 621 and 763 ms from batch ready; 2.7× uses the lower, 3.4× would use the higher |
| section 8.3, n=10 | Narwhal's ~440 ms before consensus is untraced; do not lead with 40× |
| section 8.3, ours | one run per size; our consensus latency not recorded |
| sections 8.2, 8.3, 8.6: Narwhal fill wait marked estimated | half its batch interval, not traced in that run; the estimate matched the log in all three traced runs (section 3) |
| section 8.1 | Narwhal's n=10 and n=30 sit next to runs just under 95%; Narwhal's batch size was not varied |
| Comparison A, all rows | density confound; section 12 is the check |
| Narwhal generally | mostly single runs; where repeated, spreads of 43-51%, and delivery at one configuration varied between 91% and 99% across runs |

## 15. Things that are true and must not be overstated

- **Throughput is comparable, not higher.** Our measured maximum is 15–22%
  above Narwhal's at n=10–30 and within 2% at n=50 (section 8.1), but with
  batches of up to about 3,800 transactions against Narwhal's 500, and
  Narwhal's maximum with larger batches was not measured. Never write that
  either protocol has the higher maximum throughput.
- **Our latency lead is 3.9× at n=20, 5.1× at 30 and 2.7× at 50** (section
  8.3), each protocol at its best configuration that carries at least 95% of
  the load. Do not lead with the n=10 figure (40×), and do not write that the
  lead narrows steadily with size: it is smallest at 50.
- **Our latency lead is a moderate-load result.** Near maximum throughput
  both protocols take several hundred milliseconds, and Narwhal is faster at
  n=20 (444 against 751 ms; section 8.1).
- **The 95% rule is part of the claim.** Narwhal has lower-latency settings
  that do not carry the load (section 8.2); say so wherever the ratios appear.
- **Signature checking is the per-round cost that matters at large n**
  (section 8.7): about n² checks per round. Do not attribute any n=50 effect
  to payload amplification.
- **Narwhal latency figures measured with its default configuration at
  moderate load must never be cited as its performance** (section 8.2). They
  appear in comparisons B and C, marked †, as default-configuration values.
  Never quote the B or C latency ratios against Narwhal (38.8×, 23.3×, ...) as
  the gap between the protocols; they are upper bounds.
- **Narwhal's latency is not dominated by its delivery-acknowledgement wait.**
  That claim was withdrawn after tracing (section 8.5).
- **The n=50 deadlock of inline Sailfish is a 10-machine testbed property**,
  not a protocol property.
- **The 9,456 ms figure at 1,000 tx/s is a load-generator artefact.** Any
  table containing it is not to be used.
