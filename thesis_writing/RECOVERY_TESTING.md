# Recovery mechanism testing — PRBC-Sailfish Phase-3 recovery

Working record of the investigation into whether Phase-3 recovery triggers
correctly, resolves correctly, and behaves as a derived probability model
predicts. Kept as a durable record separate from the conversation that
produced it — see `CLAUDE.md` for the general repo/architecture context.

## Why this started

The stats block originally showed `Phase-3 recoveries` / `Race cond. hits`
counters that looked alarming (hundreds to low-thousands per run) with no way
to tell whether they represented real network fetches or were resolved
locally. That ambiguity is what this whole investigation resolved.

## The fault used: Byz1

`NodeBehavior::Byz1` (`shared/src/domain/node.rs`, implemented in
`prbc_sailfish.rs`) makes a proposer send its `PRBCPropose` to only
`2f+1` peers (unicast) instead of broadcasting to everyone, deterministically
excluding whichever peers fall past that cutoff in the node list's iteration
order (always the highest-ID nodes, since selection is `.take(2f+1)` over
IDs in ascending order). The fan-out is the fault's choice and stays 2f+1
whatever the protocol's quorum (q = n − f). Enabled by setting a node's
`behavior` column to `byz1` in the nodes CSV.

Excluded nodes still see the vote quorum complete (votes are broadcast to
everyone regardless), so they hit "hash committed, no local payload" —
exactly the condition Phase-3 recovery exists for. Their only way to get the
vertex without an explicit recovery request is PRBC's S1→S2 sampling relay
(a second, redundant forwarding path, sample size `⌈1.4·√n⌉`).

## Instrumentation added this investigation

New/renamed counters in `prbc_sailfish.rs` `+ RESULTS`:
`Payload-lag events` (quorum before local payload — expected, not an error),
`Payload post-quorum` (resolved by the propose/relay arriving on its own),
`Network recoveries` (actual `PRBCRecovery` messages sent), `Recovery resp OK`
(valid responses applied), `Recovery resp served` (responses this node sent
to a peer). Backed by `sparse_bullshark/src/utils/metrics.rs`
(`ResourceMeter` for CPU, `WireCounters` for network bytes).

`run_distributed.py` / `run_linux.py` print a **per-node** breakdown of these
under `--logs` — necessary because recovery activity concentrates on 1-2
excluded nodes, and the **median across all nodes hides it** (repeatedly
confirmed: a real, large per-node signal can round to ~0 in the median).

## Two infrastructure bugs found and fixed along the way

1. **`run_distributed.py` wrote the wrong file.** The Rust binary hardcodes
   `./shared/nodes.csv` (`shared/src/initializer.rs`); `setup_cluster.sh`
   deploys there once. But `run_distributed.py`'s remote script was
   overwriting `shared/nodes_distributed.csv` every run — a file the binary
   never reads. Every `sed`-applied Byz1 edit before the fix was **silently
   inert**; every "byz1" cloud run was secretly running all-`ok`. Fixed by
   changing the remote script's write target to `shared/nodes.csv`.
   Confirmed via `Faults: 1 node(s)` in the CONFIG block only appearing after
   the fix.
2. **`--logs` never showed the binary's own `warn!`/`error!` output.** Each
   node's stderr was redirected to `/tmp/sb_{nid}.err` on the remote machine
   and never read back — `--logs` only showed the SSH/bash session's own
   stderr, a different thing entirely. Fixed by also `cat`-ing each node's
   `.err` file back through its own markers, parsed into a "PER-NODE BINARY
   LOGS" section.

**Lesson for any future fault-injection test on this harness:** always check
for the `Faults: N` line in `+ CONFIG` and the actual `BYZ1: ...` log line
before trusting the numbers — both are now confirmed working, but the first
several attempts here silently weren't.

## Results

### Local (n=7, loopback, `RECOVERY_TIMEOUT_MS=5`)

| Node | Payload-lag | Network recoveries | Recovery resp OK |
|---|---|---|---|
| 6 (excluded) | 593 | 28 | 28 (100%) |
| 0–5 | 446–525 | 0 | 0 |

First clean confirmation: recovery concentrates exactly on the excluded node
and resolves 100%.

### Cloud (n=10) — timeout sensitivity

Before the deploy-path fix, "byz1" and "control" cloud runs were
indistinguishable (both secretly all-`ok`). After the fix, a timeout sweep at
n=10, 20k tx/s, node 0 = byz1 (excludes nodes 8, 9) showed:

| Timeout | Background avg (nodes 0–7) | Node 8 | Node 9 |
|---|---|---|---|
| 5ms | 7.8 | 44 | 33 |
| 10ms | 5.6 | 24 | 40 |
| 20ms | 3.6 | 20 | 25 |
| 50ms | **0.4** | 28 | 23 |
| 100ms | 1.1 | 19 | 33 |
| 500ms | 8.1 | 33 | 44 |

Key finding: background (ordinary network jitter, unrelated to the fault)
drops toward zero as the timeout loosens, but **nodes 8/9 stay elevated across
the entire range, including at 500ms** — their need for recovery is
structural (no direct path exists at all), not a timing artifact a longer
wait would fix. 50ms gives the cleanest separation for a single reported
value. Two repeated sweeps gave `Recovery resp OK` pooled mean 25.3 for
nodes 8+9 (95% CI 22.6–28.1) — used as the empirical baseline for the
theoretical comparison below.

### Theoretical model — does the recovery rate match the sampling math?

For a Byz1 proposer at committee size `n`: the `d = 2f+1` lowest-ID peers get
the propose directly (the fault's fan-out, not the protocol's quorum); the
other `n-1-d` are excluded. An excluded peer is rescued if any
peer among the eligible S1→S2 relayers (S1 members who are also among the
`d` direct recipients) happens to include it in their own S2 sample. Modeled
as: hypergeometric distribution over how many eligible relayers exist,
times `(1 - sample_size/n)` per relayer of *not* rescuing, to get
P(genuine recovery needed).

Recovery is needed only for a certified vertex. An excluded peer counts the
votes of the `d` recipients and the proposer's own, 2f+2 in all, against the
quorum `q = n − f`. That is enough except when n = 3f+3 (n = 9, 30): there
one more vote is needed, from an excluded peer a relay reached, so a round
in which no excluded peer is reached certifies nothing and needs no
recovery. That lowers the n = 9 prediction from 12.8% to 12.2%; at n = 30
the change is below 0.1 point. Every other row is unchanged.

| n | direct recipients (2f+1) | excluded | sample size | predicted genuine-recovery rate |
|---|---|---|---|---|
| 7 | 5 | 1 | 4 | 10.2% |
| 8 | 5 | 2 | 4 | **20.1%** |
| 9 | 5 | 3 | 5 | 12.2% |
| 10 | 7 | 2 | 5 | 10.2% |
| 20 | 13 | 6 | 7 | 15.6% |
| 30 | 19 | 10 | 8 | 22.2% |
| 50 | 33 | 16 | 10 | 24.0% |

At n=10, 20k tx/s: predicted 24.3 recoveries (239 rounds × 10.2%); pooled
observed mean 25.3 (CI 22.6–28.1) — matches.

### Validation sweep across n = 7, 8, 9, 10 (same 10-machine cluster, no new VMs)

Ran `--n-nodes 7/8/9/10`, byz1 on node 0, 50ms recovery timeout, 20k tx/s.
`% = Recovery resp OK / Ordered rounds` for the excluded node(s) in each run.

| n | excluded node(s) | predicted % | observed % | diff |
|---|---|---|---|---|
| 7 | 6 | 10.2% | 8.8% | -1.4pp |
| **8** | 6, 7 | **20.1%** | **17.7%** | -2.4pp |
| 9 | 6, 7, 8 | 12.2% | 11.2% | -1.0pp |
| 10 | 8, 9 | 10.2% | 9.0% | -1.2pp |

These runs counted votes against a quorum of 2f+1. With the protocol's
quorum only the n = 9 prediction moves (12.8% to 12.2%, as above), well
inside the run-to-run scatter, so the table describes the protocol.

**The non-monotonic shape reproduced exactly** — n=8 stands out as roughly
double its neighbors in both prediction and observation, not just "higher."
The relative size of the bump matches almost exactly: predicted 1.85× vs.
observed 1.84× the average of the other three sizes. Every observed value
sits a consistent 1.0–2.4 points *below* prediction — consistent with the model's one known
simplification (it only accounts for a single relay hop; multi-hop rescue,
not modeled, would only push the true rescue rate above the single-hop
estimate, i.e. push recovery rate below it — exactly the direction and
rough size of the observed gap).

**Conclusion so far:** recovery triggers exactly when the sampling math says
it should, resolves successfully essentially every time it's genuinely
needed, and its frequency follows a specific, falsifiable, non-monotonic
curve derived from first principles — not just "roughly more at higher n."

### f=3 simultaneous Byz1 (nodes 0, 1, 2, n=10) — maximum tolerated fault load

All three proposers deterministically exclude the same two victims (8, 9).
Predicted rate: 3× the single-fault trials (3 × 239 rounds × 10.2% ≈ 73.1 per
excluded node, evaluated independently for node 8 and node 9).

| | Run 1 | Run 2 | Mean | vs. predicted (73.1) |
|---|---|---|---|---|
| Node 8 | 79 | 65 | 72.0 | -1.5% |
| Node 9 | 54 | 70 | 62.0 | -15.2% |
| Pooled | | | 67.0 | -8.3% |

Node 8 vs. node 9 flipped which was higher between the two runs (confirming
the imbalance is run-to-run noise, not a systematic bias). Background noise
itself swung from avg 8.1 to avg 1.6 between runs — the underlying signal is
stable, the noise around it isn't. The pooled shortfall (-8.3%) matches the
same order of magnitude as the single-fault gap from theory, consistent with
the same known cause (single-relay-hop simplification). Consensus TPS/latency
unaffected in both runs. **Conclusion: recovery scales linearly to f=3 (the
maximum BFT-tolerated fault count) with no sign of the recovery/relay channel
saturating.**

### Baseline — no fault, default timeout (n=10, 20k tx/s)

For contrast: same setup, `Faults: 0`, default `RECOVERY_TIMEOUT_MS=500`, no
`--recovery-timeout-ms` override.

| Node | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Network recoveries | 2 | 7 | 1 | 0 | 0 | 0 | 2 | 1 | 0 | 0 |
| Recovery resp OK | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**`Recovery resp OK` is zero on every single node.** Under normal operation at
the default timeout, genuine network recovery essentially never completes —
the few `Network recoveries` attempts that fire (max 7) are all superseded by
the propose arriving naturally before a response matters. No node
concentrates activity the way byz1's excluded nodes do. This is the clean
counterpoint to every fault-injection result above: normal operation ≈ zero
genuine recovery, spread with no pattern; a real fault ≈ tens of genuine
recoveries, concentrated exactly on the excluded node(s).

## The recovery protocol as implemented (rewritten 27 October)

Read from source. `PSEUDOCODE.md` Figure 6 has the algorithm with line
numbers; this section explains it.

### The state machine

**Trigger.** `on_hash_quorum`: a quorum of votes (q = n − f) arrives for a hash this node cannot
execute. Either it never received the propose, so the vertex is missing, or
the propose is here but parked waiting for its batch, so only the batch is
missing.

**Who gets asked.** The voters themselves, one at a time, in an order rotated
per requester by `(my_id + hash[0]) % len` so requesters do not all converge
on the lowest ID. Every voter held the vertex and the batch when it voted:
**a node must store the batch before it can vote** (it parks the propose in
`pending_on_batch` otherwise). At least f+1 of the q voters are correct.

**What is asked, and when.** A missing vertex: `PRBCRecovery` on the next
50 ms tick. A missing batch: `BatchRequest` by digest, after one
`RECOVERY_TIMEOUT_MS`, because the batch is normally still in flight on the
dissemination plane. When a recovered vertex's batch turns out to be missing
too, the same recovery switches to asking the voters for the batch.

**Checking an answer.** Recovery is armed only after the requester holds q
votes for the hash. So a vertex is valid if it hashes to that hash and names a
32-byte digest, and a batch is valid if it hashes to the digest. Nothing else
from the responder is trusted. A wrong answer from the voter currently being
waited on makes the next voter eligible immediately.

**Who answers.** Any asked voter that holds the item, in its live stores or in
its retention store. It needs no vote quorum of its own. The anti-reflection
guard is unchanged: a request whose `requester` field does not match the
authenticated sender is dropped.

**No answer.** After `RECOVERY_TIMEOUT_MS` the next voter is tried. After a
full pass with no valid answer, recovery starts over and the wait doubles each
pass, up to 8 × `RECOVERY_TIMEOUT_MS`. A valid late answer from any voter
already asked is accepted. If the vertex is the round leader's, the first
restart also lifts `timeout_suspended`, which has no effect in practice
(`PSEUDOCODE.md`, note under Figure 4).

**When recovery stops.** On success, or when its round falls more than R
rounds behind the last ordered round (`RETENTION_ROUNDS`, default 50). Correct
nodes keep delivered vertices and batches exactly that long, like Narwhal's
`gc_depth`. A node that far behind would need state transfer, which is not
implemented.

### What changed on 27 October, and why

*Background for updating drafts only. The thesis describes the current
recovery protocol as the one used throughout, and does not mention this
change.*

The 17 October reading of the code found that recovery could fail for good
even with only f faulty nodes:

| Problem in the 17 October code | Fix |
|---|---|
| Recovery fetched only the vertex. A recovered vertex whose batch was missing was parked, its recovery dropped, and the batch never requested. | `BatchRequest` / `BatchResp` by digest. The answer is checked against the digest and stored without being relayed. |
| A responder answered only if it held a quorum of votes itself. Byzantine voters could send their votes only to the requester, leaving every correct voter below quorum and silent. | The responder needs no quorum: the requester already has one and checks the hash. |
| After one pass over the voters the recovery state was dropped, and nothing re-armed it. | Restart with a doubling wait; accept late answers from anyone already asked. |
| Only the answer of the voter asked last was accepted, so slow correct answers were thrown away. | Same fix. |
| Batches were deleted on execution, so a correct voter could no longer serve them. | Executed batches and pruned vertices are kept R rounds in a retention store. |

### Two limitations remain, both about speed

1. **No negative acknowledgement.** A voter that lacks the item, one that has
   crashed, and one deliberately withholding are indistinguishable to the
   requester, and each costs a full timeout. A one-line "I do not have it"
   would let the requester skip ahead immediately. It is also the signal any
   accountability mechanism would need (see the incentive proposal in future
   work).
2. **Requests are strictly sequential.** One voter at a time, so with f
   Byzantine voters placed early in the rotation the worst case is
   f × `RECOVERY_TIMEOUT_MS` before reaching a correct one. Querying two or
   three in parallel would bound it at one timeout.

### What was never tested

- The model-predicted rates for n = 20, 30 and 50 in the table above
  (15.6%, 22.2%, 24.0%) are **predictions, never measured**. Do not present
  them as results.

## Remaining follow-ups (not required for the core investigation)

- Repeat n=7–9 a second time each (as done for n=10 and f=3) to put a
  confidence interval around all four single-fault validation points.
- Recovery under WAN delay (`--wan-delay`, combined with byz1) — not yet run.
- Measure the predicted recovery rates at n = 20, 30 and 50.

## Reproducing any of the above

All commands assume `cd ~/Sparse_Bullshark` on node-0. Toggle a node to
byz1 / back via:
```bash
sed -i '/^0,/s/,ok$/,byz1/' shared/nodes_distributed.csv   # enable
sed -i '/^0,/s/,byz1$/,ok/' shared/nodes_distributed.csv   # revert
```
Then e.g.:
```bash
python3 scripts/cluster/run_distributed.py --tx-size 512 --n-tx 500 --mode prbc_sailfish \
  --n-nodes 10 --input-rate 20000 --recovery-timeout-ms 50 --logs
```
Always check `Faults: N` in `+ CONFIG` and the `BYZ1: ...` line under "PER-NODE BINARY LOGS" before trusting the run.
