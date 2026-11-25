# Thesis writing context — PRBC-Sailfish

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


**Last refreshed: 2 October 2026.** Supersedes the 25 September version, which
contained two factual errors about the implementation (see "Corrections"
below). If an older copy of this file is in an existing chat session, replace
it rather than amending it.

This file is for a **separate writing-assistant session** (a plain chat
session, not code-aware, no repo/cluster access — deliberately lightweight).
The job of that session is: the user provides raw content/notes on a given
chapter or section, and the assistant helps turn that into polished LaTeX
prose fitting the thesis's **existing structure** (table of contents below —
don't propose a new outline, slot into the one that exists). Pull exact
figures from this file and the sibling MD files rather than inventing or
approximating them.

**Upload at the start of that session:** everything in the
`thesis_writing/` directory, plus the preliminary report PDF. See that
directory's `README.md` for what each file is and the order to read them.
Deliberately excluded: `CLAUDE.md` (operational — commands, IPs, code
layout) and `RESULTS_INVENTORY.md` (the audit trail, including superseded
figures, which would actively mislead a writing session).

---

## Corrections to the 25 September version of this file

Three statements in the earlier version were wrong. They are corrected
throughout below, but called out here because they also appear in sibling
documents and in any prose already drafted from them.

**1. "PRBC never blocks — it votes on the digest immediately." This is false.**
PRBC *does* block on local payload availability. In `prbc_sailfish.rs`, a
received propose whose batch is not in the local `BatchStore` is parked in
`pending_on_batch` and no vote is cast until the batch arrives; the source
comment states that availability of the referenced batch is a prerequisite for
casting a vote. The correct statement of the asymmetry with Narwhal is:

> Both protocols require the payload locally before acting on it. Narwhal
> *additionally* blocks on a delivery-ack quorum — a worker waits for 2f
> acknowledgements before its digest is even eligible for a header — and its
> primary suspends header processing until the payload is present. PRBC has no
> delivery-ack phase; it instead pays redundant S1→S2 relay traffic to make
> local availability likely by the time the propose arrives, and falls back to
> an asynchronous recovery fetch when it is not.

> **Further correction, 20 October 2026.** The delivery-acknowledgement phase
> exists in Narwhal's code, but it is *not* what dominates its measured
> latency. Traced through Narwhal's own logs, the long pre-consensus stage was
> mostly waiting for the next header under its default configuration. Tuned
> (`header_size` 30 B, `max_header_delay` 1,000 ms), its acknowledgement path
> takes tens of milliseconds. Do not attribute Narwhal's latency to the
> acknowledgement wait anywhere in the thesis. See `EVALUATION_RESULTS.md`
> sections 8.2 and 8.5.

The same error appears in `OBJECTIVE1_2_ANALYSIS.md` (its one-line answer and
its objective-1 section). The measurement conclusions in that document are
unaffected — only the mechanism sentence is wrong.

**2. "PRBC uses verifiable random sampling (VRF-based)." The implementation
uses neither VRFs nor verifiable proofs.** Sampling is deterministic and
hash-derived: the S1 relay set is computed from the batch digest, and each
node's S2 set from the digest concatenated with its own node id, each of size
`⌈C·√n⌉` with C defaulting to 1.4. Any node can recompute any other's sample
from public data, so no proof is needed — and none is sent: the `sample_proof`
field on the vertex exists but is always empty. This is a real
design-versus-implementation gap and chapter 6 must state it rather than
describe the designed mechanism as though it were built. See "As-built gaps"
below.

**3. The batch-size methodology paragraph was wrong in both halves.** It said
the mismatch was "PRBC 500 tx, Narwhal 1,000" and that correcting it left
PRBC's case unchanged or stronger. In fact `--batch-size 256000` ÷ 512 B is
500 transactions, so Narwhal was also at 500; the actual finding was that
**PRBC's own `--n-tx 500` had never been tuned**, which was understating PRBC
throughput by roughly 2×. And after re-measuring on a clean cluster, Narwhal
improved more than PRBC did, so margins narrowed rather than held. The correct
version of this threats-to-validity paragraph is in "Chapter 7" below.

---

## Scope boundary — what this session does and does not know

This repo and the Claude Code session that produced this file cover the
**implementation and evaluation** of an already-designed PRBC-Sailfish:
running it, measuring it, reading its Rust/Python source, comparing it to
Narwhal Sailfish. It has **no knowledge of and no input on**:

- the theoretical design of PRBC (the sampling scheme as *designed*) —
  chapters 4–5. **Exception:** the correctness outlines for the protocol as
  implemented are now in `CORRECTNESS_OUTLINE.md` (section 4.8 and
  chapter 5),
- related work beyond what the preliminary report covers (below),
- the background chapter beyond the same source.

What this file **is** reliable for: chapters 1–3 (via the preliminary-report
material below), chapter 6 (Implementation) and chapter 7 (Evaluation).

---

## The thesis, properly scoped

**The contribution:** PRBC-Sailfish — a DAG-based BFT SMR protocol that
replaces the deterministic Reliable Broadcast in Sailfish's ordering kernel
with a **Probabilistic Reliable Broadcast (PRBC)**, using random
committee-based relay to disseminate each batch to O(√n) replicas per hop
instead of all n, with a recovery mechanism for the rare case where a replica
is missing a payload it needs. Implemented in Rust, evaluated on a GCP cluster
at n = 10, 20, 30, 50 against Narwhal Sailfish.

**The central claim, from the thesis abstract — carry this nuance, do not
flatten it into "PRBC wins":**

> Narwhal Sailfish achieves higher throughput at scale, since its ordering
> layer operates on lightweight digests and proceeds in parallel with
> dissemination. PRBC-Sailfish achieves significantly lower finalization
> latency for small-to-medium systems (10–30 replicas), since it avoids the
> batch-collection windows and multi-round dissemination inherent to the
> decoupled architecture. **This latency advantage narrows as the system
> scales**, since the quadratic-ish per-round message growth still present in
> probabilistic dissemination eventually dominates ordering time at larger
> replica counts.

**What the measurements say about each sentence** (`EVALUATION_RESULTS.md`
§8.1 and §8.3; at a fixed 100,000 tx/s, each protocol at its best
configuration, both measured from the moment a batch is ready):

- **Latency:** ours is 3.9× lower at n=20, 5.1× at n=30 and 2.7× at n=50.
  At n=10 the gap is far larger (11.9 against 473 ms), but most of Narwhal's
  time there is spent before consensus, unexplained, so do not lead with it.
  "Significantly lower latency for 10–30 replicas" is supported, and the
  advantage remains at 50.
- **"Narrows as the system scales":** only from 30 to 50 replicas (5.1× to
  2.7×); from 20 to 30 it grows. Say it is smaller at 50 than at 20–30, not
  that it narrows steadily.
- **Throughput:** the first sentence is not supported; write that maximum
  throughput is comparable (§8.1). Ours measured 15–22% higher at 10–30
  replicas and level at 50, but with batches of up to about 3,800
  transactions, while Narwhal was measured only with 500. See decision 5 in
  `README.md`.

---

## Chapter map (existing table of contents — treat as fixed)

1. **Introduction** — motivation, problem statement, contributions,
   organization. *Source: preliminary report §1, summarized below.*
2. **Background** — SMR, consensus, DAGs, blockchain, broadcast primitives,
   complexity metrics, responsiveness/finalization/block time. *Source:
   preliminary report §2, summarized below.*
3. **Related Work** — leader-based (ProBFT, Simplex, ProSimplex), Bullshark
   family (Bullshark, Sparse Bullshark, Shoal/Shoal++, Sailfish),
   uncertified-DAG family (Cordial Miners, Mysticeti, Mahi-Mahi), Tribes,
   final observations. *Source: preliminary report §3, below — except Tribes,
   which is not in that report and needs the user's own source.*
4. **Designing a new probabilistic broadcast** — initial ideas, problems,
   final PRBC design, optimizations, system model, protocol spec, complexity,
   correctness outline, comparison with Tribes. **Not covered here** — needs
   the user's design notes.
5. **ProSailfish** — PRBC + Sailfish: system model, differences from plain
   Sailfish, spec, complexity, correctness outline. **Not covered here**
   beyond as-built behaviour (chapter 6 material and `PSEUDOCODE.md`).
6. **Implementation** — architecture, data structures, challenges, "Narwhal
   vs. our implementation." *High overlap with this session.*
7. **Evaluation** — experimental setup, performance analysis. *This is where
   the data below goes.*
8. **Conclusion** — future work; the incentive-mechanism proposal belongs
   here.

---

# Chapters 1–3 source material (from the preliminary report)

Source: *Probabilistic DAG-Based BFT Protocols*, Henrique Costa Do Vale
(58168), Estudo Orientado, MEI, Faculdade de Ciências, Universidade de Lisboa.
Citation numbers below are that report's; full details in its bibliography.

## 1. The motivation chain (chapter 1)

The argument runs in four steps, and the thesis introduction should follow it:

1. **SMR is foundational, and consensus implements it.** Consensus guarantees
   Agreement (non-faulty processes decide the same value), Validity (the value
   was legitimately proposed), Termination (every non-faulty process
   eventually decides) [13].
2. **Traditional BFT SMR is leader-bound.** PBFT [8] and HotStuff [24] route
   proposals and vote collection through a single leader, which bottlenecks
   throughput. Leaderless designs such as ezBFT [3] remove the leader but pay
   in communication overhead.
3. **DAG-based BFT removes the bottleneck but is communication-expensive.**
   In Bullshark [23], Mysticeti [5], Sailfish [22], Shoal++ [2], Sparse
   Bullshark [19], Mahi-Mahi [14], BBCA [18], all participants propose
   concurrently and leadership is implicit. These protocols split into block
   *dissemination* and block *ordering*, and typically cost O(n³) to O(n⁴),
   largely because dissemination rests on consistent or reliable broadcast.
4. **ProBFT shows the way out.** ProBFT [4] (Avelãs, Heydari, Alchieri,
   Distler and Bessani, PODC 2024) replaces deterministic all-to-all
   communication with randomized sample-based dissemination: VRFs select
   probabilistic quorums of size O(√n), lowering Reliable and Consistent
   Broadcast from O(n²) to O(n√n) without compromising practical safety.

**The thesis goal, stated in the report:** reduce the communication complexity
of DAG-based BFT SMR by replacing traditional reliable or consistent broadcast
with counterparts that use proportionally small random committees, and
evaluate the result against state-of-the-art alternatives.

## 2. Background definitions (chapter 2)

These are stated in the report and can be used nearly verbatim.

**Timing models.** *Synchronous*: known upper bound Δ on message delay and
process execution time. *Asynchronous*: no timing assumptions; delays are
arbitrary. *Partially synchronous*: asynchronous for an arbitrary period, then
synchronous after an unknown Global Stabilization Time (GST).

**Fault models.** *Crash*: a process stops making progress. *Byzantine* [17]:
a process deviates arbitrarily, possibly adversarially controlled. Non-faulty
processes are *correct*.

**Complexity metrics.** *Message complexity*: number of messages exchanged.
*Communication complexity*: total bits exchanged. *Communication steps*:
number of sequential communication phases to complete one instance. Fewer
steps correlates with *responsiveness* — proceeding at actual network speed
rather than at a conservative worst-case bound.

**Broadcast primitives,** categorized by which of three properties they give:

- *Validity*: if a correct process broadcasts m, every correct process
  eventually delivers m.
- *Agreement*: if a correct process delivers m, every other correct process
  eventually delivers m.
- *Integrity*: every correct process delivers at most one message, and only if
  it was genuinely broadcast by the sender.

*Best-effort broadcast* gives Validity and Integrity but not Agreement — with
a faulty sender, some correct processes may deliver and others not. *Byzantine
consistent broadcast* gives Validity, Integrity, and a weaker agreement: any
two correct processes that deliver, deliver the *same* message, but some may
deliver nothing. *Byzantine reliable broadcast* gives all three even under
Byzantine faults.

**SMR properties** [21]: *Initial State* (all non-faulty processes start
identically), *Determinism* (same state + same input ⇒ same output and next
state), *Coordination* (commands processed in the same agreed order).

**Probabilistic consensus** [4] relaxes two of the three: *Validity* (the
decided value satisfies an application predicate), *Probabilistic Agreement*
(two non-faulty processes decide differently only with a probability depending
on the number of Byzantine processes and quorum sizes), *Probabilistic
Termination* (every non-faulty process eventually decides with probability 1).
**This is the definition PRBC-Sailfish's safety argument sits inside** and
chapter 2 should set it up deliberately for that reason.

**DAG**: vertices plus directed edges, no cycles. In DAG-based consensus,
blocks reference multiple predecessors, permitting concurrent proposals;
protocol rules then flatten the graph into a total order.

## 3. Related work (chapter 3)

### Bullshark [23] — the certified-DAG reference point

Separates DAG construction (all communication) from ordering (purely local —
a validator interprets its own copy of the DAG). Rounds are numbered; each
replica proposes at most one vertex per round; a valid round-r vertex carries
edges to at least n−f round-(r−1) vertices. A vertex's *causal history* is
everything reachable from it. Certified DAGs guarantee **non-equivocation**
(no two correct replicas hold different vertices for one position) and **data
availability** (for any vertex in a correct replica's DAG, at least one correct
replica stored the proposal).

*Adding a vertex:* the proposer sends a signed Propose; each receiver checks
the n−f certificates and that it has not already voted for a different vertex
from that source in that round, then stores the proposal and returns a signed
Vote on the vertex hash; n−f matching votes form a certificate; the proposer
broadcasts the certificate; on receipt, a replica delivers the vertex.

*Ordering:* agree on a sequence of anchors, each anchor's parent being the
highest-round anchor in its causal history. **Commit rule:** commit anchor A
from round r on observing f+1 round-(r+1) vertices with an edge to A — f+1
suffices, rather than 2f+1, because the DAG itself guarantees
non-equivocation. Replicas use a timer for round advancement rather than
advancing eagerly, to preserve ordering liveness.

### Sparse Bullshark [19] (*DAGs for the Masses*) — the direct ancestor

Instead of referencing a full n−f quorum, a validator that has collected n−f
round-r blocks selects a random subset of size **D** and references only
those. D trades off communication, latency and security.

*Verifiable sampling:* a validator proves it saw the round-r quorum by
supplying an aggregated multi-signature over the round number and a bitset of
sending validators; that multi-signature seeds a PRNG which picks the D
parents. Any validator verifies by checking the multi-signature and re-running
the same deterministic draw. The commit rule rises from f+1 to n−f = 2f+1, so
that a committed anchor remains reachable from later anchors despite sparse
connectivity. Result: Θ(n³) → Θ(n² + d) at unchanged latency.

**This is the most important comparison point for chapter 4**, because it is
the other protocol that samples — and PRBC-Sailfish samples at a different
layer (payload relay, not parent selection) and, as built, without the
verifiable-proof machinery. That contrast is worth drawing explicitly.

### Sailfish [22] — the chosen substrate

Addresses the fast commit rule not reliably triggering in good-case
conditions, via **timeout certificates**: 2f+1 timeout messages, each saying a
replica did not receive the anchor in time. A valid vertex must carry either
an edge to the anchor or a valid TC — so a Byzantine replica proposing without
linking the anchor must prove at least f+1 correct replicas genuinely timed
out. This supports an anchor in every round without complex pipelining, giving
better latency than Bullshark. A multi-leader variant pipelines several
instances per round.

### Shoal / Shoal++ [2]

An optimization layer over Bullshark: *pipelining* (sequential single-shot
Bullshark instances, each terminating on its first committed anchor, the next
starting at r+1 — best case, an anchor per round) and *leader reputation*
(score-based leader election so a faulty leader is quickly dropped). Safety is
inherited from Bullshark per instance.

### Cordial Miners [16], Mysticeti [5], Mahi-Mahi [14] — the uncertified family

*Cordial Miners* is the foundation: an uncertified DAG using best-effort
broadcast instead of consistent broadcast, saving two message delays at the
cost of a more complex ordering algorithm; ordered in 3-round waves (leader,
vote, finalize). *Mysticeti* moves this to partial synchrony and adds
aggressive pipelining with k proposer slots per round, committing every round
in the good case. *Mahi-Mahi* targets Cordial Miners' throughput limit (at
most one leader block every five rounds) with a commit rule that commits
multiple blocks per asynchronous round; configurable for five-hop commit under
active asynchronous adversaries or four-hop under moderate conditions.

### The chained and probabilistic baselines

*Simplex* [9]: leader-based, propose-vote, extends a notarized chain;
responsive — advances on observing a notarized block rather than on fixed
timeouts, falling back to dummy blocks only on leader failure or stall. 2δ
notarization, 3δ finalization, but O(n²) all-to-all, and its theoretical
design transmits the full notarized chain in proposals.

*ProBFT* [4]: as in the motivation chain above — VRF-selected probabilistic
quorums of size O(√n) in the Prepare and Commit phases, O(n√n) overall,
safety and liveness with high probability under a static adversary.

*Probabilistic Simplex (ProSimplex)* [12] (dos Santos, MSc thesis, Universidade
de Lisboa, 2025): ProBFT's sampling applied to Simplex's Vote and Finalize
phases, reaching O(n√n) while keeping three-step latency. Responsive, handles
leader rotation inside its iterative structure with no separate view change,
and piggybacks probabilistic quorum certificates onto Propose messages so a
node that missed a probabilistic quorum can recover the proof and advance.
**Structurally the closest sibling to this thesis** — same idea, chained
substrate instead of a DAG one.

### The comparison table (report Table 1)

| Protocol | Sync | DAG | Comm. compl. | Latency (anchor / non-anchor) | BCast | Multi-leader |
|---|---|---|---|---|---|---|
| BBCA-Chain [18] | Partial | Uncertified | O(n⁴) | 3δ / 5.5δ | CBC | No |
| Bullshark [23] | Partial | Certified | O(n³) | 6δ / 12δ | RBC | No |
| Sparse Bullshark [19] | Partial | Certified | Θ(n²+d) | 6δ / 12δ | RBC | No |
| Mysticeti-C [5] | Partial | Uncertified | O(n⁴) | 3δ / 3δ | BEB | Yes |
| Shoal++ [2] | Partial | Certified | Θ(n³) / Θ(n²λ) | 4δ / 4δ | RBC | Yes |
| Sailfish [22] (Das et al. [11]) | Partial | Certified | O(n³) | 5δ / 9δ | RBC | Yes |
| Sailfish [22] (Abraham et al. [1]) | Partial | Certified | O(n⁴) | 3δ / 5δ | RBC | Yes |
| Mahi-Mahi [14] | Async / Rand async | Uncertified | O(n⁴) | 5δ / 4δ | BEB | Yes |

(Best case; for Shoal++ the first figure is with μ-sig, the second with τ-sig.
Mahi-Mahi: 5δ under asynchrony, 4δ under random asynchrony.)

### The report's own synthesis of limitations

*Certified DAGs* give strong safety but carry heavy communication; remedies
are a lighter broadcast primitive, weaker (probabilistic) communication models
to escape O(n³), fewer or no signature verifications, smaller vertices and
certificates, and more leaders / multiple execution modes. *Uncertified DAGs*
trade safety machinery for a lighter primitive, and are limited instead by
data availability and consistency.

## 4. The motivating experiment, and why the design looks as it does

An earlier Rust implementation of **monolithic** (full-payload-in-vertex)
Bullshark, Sparse Bullshark and Sailfish, benchmarked against Practical
Simplex. Setup: Dell PowerEdge R410, dual Intel Xeon E5520 at 2.27 GHz (16
hardware threads), 32 GB RAM, Gigabit Ethernet, Ubuntu 20.04; ten physical
machines, with n > 10 simulated by running several processes per machine.
Blocks of 1,000 or 10,000 transactions at 242 B or 992 B; n = 4, 7, 10, 34,
67, 100. **Different hardware from the current GCP cluster — do not compare
absolute numbers across the two.**

Findings:

- **Sailfish beat both Bullsharks**, peaking above 150,000 tx/s (≈152,000),
  about 10% over Bullshark (≈142,000) and 300–400% over Simplex, with lower
  latency from its 1-round commit rule.
- **Sparse Bullshark was slightly *worse* than dense Bullshark at small n.**
  In a monolithic architecture the bottleneck is O(n) payload traffic, not the
  O(1) metadata Sparse Bullshark optimizes, so the cost of sampling and proofs
  outweighed the saving. Larger transactions (992 B) cut absolute throughput
  by ~70–75% but left the ranking unchanged.
- **All monolithic DAG protocols hit a "bandwidth wall" at n ≥ 34**,
  collapsing there and effectively ceasing to function by n = 67–100, while
  Simplex — lower bandwidth per step — stayed stable. The report is careful
  that this is an artefact of the monolithic architecture, not of the DAG
  model.

**Why this motivated the current design.** The bandwidth wall is the explicit
justification for (a) decoupling dissemination from ordering so the consensus
layer carries only digests, and (b) probabilistic dissemination as an attack
on the quadratic broadcast cost itself rather than only on payload coupling.
The report names Narwhal as the archetype of (a). **This is the strongest
single narrative thread available for chapter 1 → chapter 7**: the preliminary
work found the wall, the thesis removes it two ways at once, and the current
evaluation measures both against the same baseline.

**Why Sailfish was chosen as substrate** (three reasons, usable almost
verbatim): (1) highest observed throughput of the candidates; (2) lower
finality latency from the 1-round commit rule versus Bullshark's 2-round rule;
(3) — the load-bearing one — its "leader-in-every-round" synchronization gives
coordinated advancement, which matters once probabilistic dissemination
introduces variance into message delivery; a protocol that races ahead
asynchronously was judged to risk destabilizing ordering under that
stochasticity.

---

# Chapter 6 — Implementation (as built)

`PSEUDOCODE.md` holds the algorithms transcribed from source with line
references; use it as the authority for anything algorithmic.

**Three-plane TCP.** `TrafficPlane { Control, ConsensusData, Dissemination }`,
each a separate TCP connection between every node pair with its own drain
budget (256 / 64 / 16). Control carries votes, recovery requests (for a
vertex or a batch) and timeouts; ConsensusData carries proposes and vertex
recovery responses; Dissemination carries batch payloads, including a batch
sent in answer to a recovery request. Rationale: a 256 KB payload on a shared
connection head-of-line-blocks the latency-critical vote traffic.

**Digest-only consensus path.** `Vertex.block` is exactly one 32-byte SHA-256
batch digest, enforced independently at the propose handler and the
recovery-response path. Vote messages are therefore constant-size regardless
of block size.

**Sampling.** The S1 relay set is derived by hashing the batch digest with a
fixed domain separator; each node's S2 set by hashing the digest with its own
node id. Size `⌈C·√n⌉`, C configurable (`PRBC_SAMPLE_C`), default 1.4 — giving
7 at n=20 and 8 at n=30. Deterministic and publicly recomputable.

**Commit path.** Votes reach a quorum q = n − f → the (round, source) pair is
hash-committed → `may_advance_round` requires q hash-committed vertices →
`try_committing_prbc` commits the leader once witnessed by q in r+1 →
`commit_causal_history_prbc` traverses **strong and weak** edges → execution on
payload verification.

**One batch per vertex, built when the party proposes** (`PSEUDOCODE.md`
lines 18–22). Transactions are always available; a party never waits for
them. When it proposes, it builds its batch from the transactions that
arrived at the offered load, λ = `INPUT_RATE` / n per party, since its
previous batch, up to the configured maximum (`--n-tx`), carrying any excess
to the next batch; with no rate limit every batch is full. Rounds therefore
run as fast as votes and certificates allow, and batch size follows the
round rate: faster rounds mean smaller batches. Each vertex carries exactly
one batch digest, whereas Narwhal's header carries a map of many digests,
decoupling its batch rate from its round rate.

**Minimum gap between proposals** (`PSEUDOCODE.md` line 36,
`MIN_PROPOSAL_GAP_MS`). A party proposes at most once every Δ. Each round
costs every party about n² vote-signature checks whatever the batch size, so
Δ sets the round rate, and with it the batch size (about the load per party
× Δ) and the CPU used. In every experiment Δ = n²/25 ms (4, 16, 36 and
100 ms at n = 10, 20, 30 and 50): each machine checks about 25,000 vote
signatures per second, about half its CPU (measured 50–58%). Narwhal's batch
delay plays the same role and is tuned per size too (`EVALUATION_RESULTS.md`
§8.2).

**Also as built:** Ed25519 signatures on votes, vertices and no-votes
(`PRBC_SIGS`, on by default; a vote signs the round, source and hash together);
timeout certificates for round advance; Sailfish commit on ≥2f+1 *first
messages* rather than full RBC delivery; a pluggable RBC layer (`bracha` or
`signed_vote`) used by the Sailfish baseline; `MEMPOOL_MODE=decoupled` so the
same binary runs Sailfish with inline payload or with digests.

**Vote-signature verification** happens on each peer's connection reader
task, before a vote reaches the consensus loop, so the checks run in parallel
across connections and stay off the consensus critical path; an invalid vote
is dropped there. Describe it this way in chapter 6, as how the
implementation works, with its reason: checking every vote's signature one at
a time in the consensus loop, about n² checks per round, would limit the
round rate at n=50 (`EVALUATION_RESULTS.md` §8.7). Present this as design
rationale, not as a change; no before/after figure, and no sentence about
which results came first. A vote for a slot the party has already certified
is dropped there without its signature being checked, since it would be
ignored anyway; about f of every n votes for a vertex arrive after it is
certified.

**Recovery** (rewritten 27 October; `PSEUDOCODE.md` Figure 6 is the
authority). A party that hash-commits a vertex it cannot execute asks the
vertex's q voters, one at a time, first for the vertex if it lacks it, then
for the batch by its digest. It checks the vertex against the hash and the
batch against the digest, both of which it already holds with q votes, so
it trusts nothing from the responder. Every voter stored the batch before
voting, so at least f+1 correct voters hold it. Correct parties keep
delivered vertices and batches for R rounds after ordering (`RETENTION_ROUNDS`,
default 50, the role Narwhal's `gc_depth` plays). Recovery never gives up
inside that window: after a full pass over the voters it starts over, waiting
twice as long each pass, up to 8 × `RECOVERY_TIMEOUT_MS`. **State the
guarantee for the implementation, not only the design:** a correct party that
hash-commits a vertex eventually holds the vertex and its batch after GST,
provided it is less than R rounds behind the other correct parties. Beyond
that it would need state transfer, which is not implemented (nor needed in
any experiment), the same boundary as Narwhal's. Chapter 6 should not list
"recovery fetches only the vertex" or "recovery can give up" as limitations:
both were fixed on 27 October. Do not mention that they were ever missing.

**Correctness fixes** (also 27 October, after the recovery rewrite;
`PSEUDOCODE.md` Figures 3–5 and 7 are the authority). Writing the
correctness argument exposed five places where the code did not do what the
proof needs (four on 27 October, the fifth on 29 October). All five are now
implemented. **In the thesis, present all five as part of the protocol, each
with its reason; never as fixes or changes**:

- **A vote is bound to its slot.** It signs (round, source, hash), not the
  hash alone, so an honest vote cannot be relabelled as a vote for another
  slot.
- **Only the source can fill its slot.** The source signs its vertex, and
  every party checks the signature before voting.
- **Leaders are skipped as in Sailfish.** The commit rule takes the latest
  leader with q direct supporters, walks back, orders every earlier leader
  it has a strong path to, and skips the rest. A leader that does not point
  to the previous leader must carry a no-vote certificate: q signed
  statements that their next vertex does not point to that leader. Before
  the fix, a leader that never proposed stopped ordering for good.
- **Totality.** A party votes only for a well-formed vertex (q strong
  edges into the previous round, weak edges within the GC window) whose
  parents it has all certified itself. So every certified vertex has f+1
  correct voters holding certificates for its parents, and a party that sees
  a parent it has not certified fetches the certificate. Ordering waits until
  a leader's whole history is certified and its vertices known, and orders it
  by (round, source), so every correct party orders the same vertices in the
  same order.
- **Every correct party votes.** A party that collects q votes before it can
  vote (its vertex or batch is still on the way) delivers at once, and still
  votes once the vote rule holds. Otherwise Byzantine parties could send
  their votes to only some parties and leave the rest one vote short.
  Because every correct party votes, a correct sender's vertex is certified
  everywhere (Lemma 4.6, rule (C6) in `CORRECTNESS_OUTLINE.md`).

The first four checks fire only when a party misbehaves or crashes. The
fifth adds one small vote whenever the votes outrun a vertex; it changed
nothing measurable, locally or on the 50-machine cluster. **No result in any file changes**; do not
revise any number because of them.

**Quorum size.** Every threshold (votes, round advance, timeout and no-vote
certificates) is q = n − f, the same threshold Narwhal uses; it equals 2f + 1
when n = 3f + 1. In the thesis write q or n − f whenever n is general.

## As-built gaps — state these in chapter 6, do not paper over them

1. **No VRF, no verifiable sampling.** Deterministic hash-derived sampling as
   above. The `sample_proof` field exists on the vertex and is always empty.
   Contrast with Sparse Bullshark's multi-signature-seeded PRNG, which the
   related-work chapter describes — the thesis should say plainly why the
   proof is unnecessary here (public recomputability) or acknowledge it as
   unimplemented, whichever the design intends.
2. **Timeout certificates are carried but not checked.** A vertex carries
   one when its round advanced on a timeout, but no party verifies it. Safety
   does not rest on it: skipping a leader rests on the no-vote certificate,
   which is checked. (The no-vote certificate itself is implemented since
   27 October; do not list it as missing.)
3. **Sampling governs payload relay, not the vote path.** PRBC votes are sent
   to all parties; the S1/S2 committees relay *batches*. So the O(n√n)
   argument applies to dissemination, and the consensus path's saving comes
   from carrying 32-byte digests rather than from sampling. Chapters 4–5 and 7
   must be consistent about which layer the complexity claim is about.
4. **Recovery timing.** `RECOVERY_TIMEOUT_MS` is the *retry* interval. A
   missing vertex is requested on the next tick (~50 ms) after recovery is
   armed. A missing batch is requested only after one `RECOVERY_TIMEOUT_MS`,
   because it is normally still in flight on the dissemination plane.
5. **Two recovery limitations remain, both about speed, not correctness.**
   A responder that lacks the item stays silent rather than saying so, and
   requests go to one voter at a time. With f Byzantine voters first in line,
   the first valid answer can take f × `RECOVERY_TIMEOUT_MS`.

---

# Communication cost — the three-way comparison

Material for the complexity discussion (chapters 4–5) and its empirical half
(chapter 7). **The counts below are derived analytically by reading the
dispatch sites in the source; the Mbps figures are measured live.** Keep that
distinction in the prose.

## Counting convention

Count **full-payload transmissions per broadcast instance** — one node
disseminating one block to the committee. Let `s = ⌈C·√n⌉` be the sample size,
C = 1.4 by default, giving s = 5, 7, 8, 10 at n = 10, 20, 30, 50. Vote and
digest traffic is counted separately because it is independent of block size.

## The three structures, as implemented

**Bracha RBC, inline payload** (`sailfish.rs` without `MEMPOOL_MODE=decoupled`):
the block travels in VAL, ECHO *and* READY, so every node re-forwards the full
payload to every node. Transmissions: `(n−1) + 2n(n−1)`.

**PRBC-Sailfish**: the originator broadcasts the batch once to all peers
(`prbc_sailfish.rs:922-926`), and each of the s nodes in S1 relays it to its own
S2 set of size s (`:1942-1966`). The propose is relayed through the same
S1→S2 structure (`:1810-1844`). Transmissions: `(n−1) + s(s−1)`.

**Narwhal**: `batch_maker.rs::seal()` performs one flat best-effort broadcast
to the other workers, with no relay tier anywhere in the pipeline.
Transmissions: `(n−1)`.

## Payload transmissions per broadcast

| n | Bracha RBC | PRBC-Sailfish | Narwhal | PRBC vs Bracha | PRBC vs Narwhal |
|---|---|---|---|---|---|
| 10 | 189 | 29 | 9 | 6.5× fewer | 3.2× more |
| 20 | 779 | 61 | 19 | 12.8× fewer | 3.2× more |
| 30 | 1,769 | 85 | 29 | 20.8× fewer | 2.9× more |
| 50 | 4,949 | 139 | 49 | 35.6× fewer | 2.8× more |

## The two statements, and why both are needed

**Against reliable broadcast the saving is asymptotic.** Bracha's forwarding
phase costs n² payload transmissions; PRBC's costs s² ≈ C²n, because only the
√n nodes in S1 forward and each sends to √n targets — the sender set and the
fan-out both shrink. Per broadcast that is **O(n²·|B|) → O(n·|B|)**; per DAG
round with n concurrent broadcasts, **O(n³·|B|) → O(n²·|B|)**. The ratio grows
linearly with n, which is why the table widens from 6.5× to 35.6×. This is
precisely the "bandwidth wall" the preliminary report measured at n ≥ 34 being
removed, and it should be written as the resolution of that earlier finding.

**Against Narwhal the cost is a constant factor, paid deliberately.** Narwhal
broadcasts each batch exactly once; PRBC sends roughly (1 + C²) ≈ 3 copies.
Measured at n=10 and 20,000 tx/s: PRBC's dissemination plane runs at
**258.4 Mbps per node against Narwhal's 67–70 Mbps**, a factor of ~3.7. This
agrees with the fitted model in `PRBC_C_TESTING.md`,
`73.7 + 7.393·s²` Mbps, whose constant term is independently derived as the
bare one-to-all broadcast cost. What the extra copies buy is local
availability: the payload is usually already present when the proposal
arrives, so a recovery fetch is almost never needed (`Payload-lag events` ≈
`Payload post-quorum`, `Network recoveries` near zero). That is the mechanism
behind the latency result.

**Both statements must appear together.** Quoting "3.7× more network than
Narwhal" without "an order of magnitude less than reliable broadcast" makes
the relay layer read as waste; quoting the second without the first hides a
real cost. Always name which baseline a claim is against.

## Caveat the prose must not blur

The saving above is in **bit** complexity. **Message** complexity is unchanged
at O(n²) per broadcast, because PRBC votes are sent to all peers
(`prbc_sailfish.rs:1862-1866`, `DispatchTarget::All`) rather than to a sample. Each
vote is a 32-byte digest plus signature, so this term only rivals the payload
term when n·d exceeds |B| — around n ≈ 8,000 at 256 KB batches — and it is
invisible in all measurements taken. It is still what distinguishes the
implemented protocol from a ProBFT-style O(n√n) agreement path, and chapters 4
and 6 must be consistent about that (see "As-built gaps").

# Chapter 7 — Evaluation

**All evaluation numbers live in `EVALUATION_RESULTS.md`, not here.** That
file is the single authority: testbeds, metrics and the latency
comparability method, the four comparisons, the supporting studies, the weak
cells, and the list of things that must not be overstated. Do not take an
evaluation figure from any other document, and do not estimate one — ask.

What remains in this file is context the results file does not carry:
implementation detail (above), fault injection, the correctness changes made
in review, the configuration surface, and how resources were measured.

## A threats-to-validity note that belongs in the prose

While investigating the network-cost gap, our `--n-tx` was found to have been
fixed at 500 throughout and never tuned, understating our throughput by
roughly 2×. Narwhal's `--batch-size 256000` is also 500 transactions at
512 B, so the two were matched on batch size by accident rather than design;
what was *not* matched was that Narwhal's batch delay had been swept and our
batch size had not. Correcting it brought us to throughput parity at every
committee size. The honest form: a tuning asymmetry in the baseline's favour
was found and removed, and it changed the throughput conclusion
substantially.

A second one. The Narwhal harness does not reliably terminate node processes
between runs; leftover processes competed for CPU and contaminated an unknown
subset of earlier measurements. The clearest symptom was Narwhal at 20 nodes
and 260k reading 62.3% of offered throughput, where a clean cluster gives
97.0%. Every point the headline comparison rests on was re-run on 1 and 15
October. Ours reproduced to within 0.4–4%; Narwhal's moved by 2–19% — an
asymmetry worth reporting in its own right.

## Fault injection

`NodeBehavior` in `shared/src/domain/node.rs` provides four modes:

| mode | behaviour |
|---|---|
| `Ok` | correct |
| `Byz1` | sends Propose to only 2f+1 peers instead of all |
| `Silent` | never creates or broadcasts its own vertex |
| `Byz2` | forwards a fake block body whose hash does not match |

`Byz1` is the fault used throughout the recovery investigation: withholding
the proposal from a minority is what forces honest nodes onto the recovery
path, which is how the hypergeometric model was exercised. `Byz2` tests that
S1→S2 relay tampering is detected rather than propagated. Full method and
results in `RECOVERY_TESTING.md`, which also documents the instrumentation
added and two infrastructure bugs found along the way.

## Design decisions worth explaining in chapter 6

Present these as design decisions of the protocol, each with its reason,
rather than as incidental implementation detail. (They were added after
supervisor review; that history is not thesis content.)

- a **leader payload guard** in `try_committing_prbc`, so a leader is not
  committed on a payload the node cannot verify;
- **`weak_edges`** added to `Vertex` and traversed in
  `commit_causal_history*`, so vertices reachable only weakly are still
  ordered rather than dropped;
- **Ed25519 vote signatures** (`PRBC_SIGS`, on by default), making a vote
  attributable rather than merely counted;
- **timeout-certificate round advance**, matching Sailfish's liveness rule;
- **Sailfish commits on ≥2f+1 *first messages*** rather than on full RBC
  delivery (`first_messages` / `record_first_message`) — a latency-relevant
  correction to the baseline implementation, and one that makes the baseline
  *stronger*, which is worth saying explicitly.

## Configuration surface (reproducibility)

| variable | effect |
|---|---|
| `PROTOCOL` | `prbc_sailfish` / `sailfish` / `sparse` / `dense` |
| `INPUT_RATE` | aggregate offered tx/s (0 = unlimited) |
| `MEMPOOL_MODE=decoupled` | digest-carrying vertices instead of inline payload |
| `RBC_MODE` | `bracha` (default) or `signed_vote`, Sailfish only |
| `PRBC_SIGS=off` | disables Ed25519 vote signatures |
| `PRBC_SAMPLE_C` | overrides C in `s = ⌈C·√n⌉`, default 1.4 |
| `--n-tx` (run scripts) | maximum transactions per batch; the batch size itself follows the load |
| `MIN_PROPOSAL_GAP_MS` | minimum gap Δ between a party's proposals; n²/25 ms in every experiment (`--min-gap-ms`) |
| `ROUND_TIMEOUT_MS` | round timeout, default 500 |
| `RECOVERY_TIMEOUT_MS` | recovery *retry* interval, default 500; also the wait before the first batch request |
| `RETENTION_ROUNDS` | rounds a delivered vertex and batch are kept for recovery, default 50 |
| `REDUCED_QUORUM=on` | f+1 instead of n − f — **CFT, not BFT-safe**, experiments only |
| `NETWORK_MBPS` | dissemination-plane bandwidth pacer |

`EXECUTION_DURATION = 60` seconds is a compile-time constant in both consensus
files. Any result quoting `REDUCED_QUORUM=on` must state that it is not
Byzantine-safe.

## How resources were measured

Two independent layers, and chapter 7's methodology section should describe
both because the combination is what answers "is this data point protocol
behaviour or a saturated testbed?"

**Per process, in-binary** (`utils/metrics.rs`): a `ResourceMeter` started
with the 60-second window reports process CPU as a percentage of one core and
of the machine, user and system CPU seconds, peak RSS, and machine core count.
PRBC additionally reports per-plane byte tallies (Control / ConsensusData /
Dissemination TX and RX) and derived Mbps.

**Per machine, externally** (`monitor_cluster.py`): SSH-samples every VM's
`/proc/stat`, `/proc/net/dev`, load average and memory at 1 Hz, then reports
CPU average and peak, NIC Tx/Rx average and peak, peak as a share of the GCP
egress cap, and a resource-bound verdict. This is the only resource view
available for the Narwhal baseline, since it is external to the binary, and
it is what caught the co-location contention and confirmed the 67–70 Mbps
figure quoted in the communication-cost section.

## Terminology — resolve this before drafting

The table of contents names chapter 5 **"ProSailfish"**, while every other
document, the abstract and the code call the protocol **"PRBC-Sailfish"**.
Pick one and use it everywhere. Related: the broadcast primitive is "PRBC"
(Probabilistic Reliable Broadcast) and the protocol built on it is the
composite name — keep those two distinguishable in the prose, since chapter 4
is about the primitive and chapter 5 about the composition.

## What `PSEUDOCODE.md` contains

Seven figures transcribed from the implementation with source line references
in the margin: local variables, utilities, probabilistic dissemination (batch
path and vertex path separately), DAG construction (including the vote rule
and the no-vote rule), the commit rule, recovery, and certificate fetch. It also carries a list of differences from an earlier hand-written
draft, and a closing section listing what the Sailfish paper specifies that
this implementation does not have. Use it as the authority for anything
algorithmic in chapters 5 and 6, in preference to prose descriptions
elsewhere.

## Not a result — future work only

A design discussion, never built or measured, on an economic mechanism to
punish a Byzantine leader that triggers excessive recoveries: reward for
committed blocks, a fee on the proposer per recovery its block causes,
escalating penalties for sustained misbehaviour, and a symmetric statistical
check so Byzantine requesters cannot frame an honest proposer. Chapter 8
material. **Never present as experimental.**

---

## Open items still needed from the user

1. **Tribes** (ToC §3.8 and the chapter 4 comparison) — not in the preliminary
   report, no source available to this session.
2. **Chapters 4–5 content** — PRBC's formal design, system model, complexity
   argument and correctness proofs. Entirely outside this session.
3. **Whether the n=10 deep-dive becomes a supporting subsection of chapter 7
   or a separate thread** — still undecided; ask before assuming a structure.
4. **Re-measured n=10 numbers** before any n=10 comparison figure goes into
   the thesis.
5. **Whether the sampling design was meant to be VRF-based**, and if so
   whether the deterministic implementation is a deliberate simplification or
   an unfinished piece. This changes how chapters 4 and 6 should read.

## How the writing session should work

- **Format:** LaTeX. The table of contents is fixed — slot into it.
- **Workflow:** the user supplies raw notes for a section; the job is turning
  them into prose, not originating claims or restructuring the thesis.
- **No citation or related-work research** — the material above is what is
  available.
- **No code or cluster access, by design.** If a number is needed that is not
  in these files, ask rather than estimate.
- **Carry the scale-dependent framing.** The advantage narrows with committee
  size and is gone at n=50, where the two are level; say so wherever a
  headline figure appears.
- **Distinguish measured from argued.** The pre-consensus split is measured;
  the explanation for Narwhal's load-dependence is not. Keep that line visible
  in the prose.
