# Objectives 1 & 2 — why Narwhal's latency is higher and its network is lower

Objectives 1 and 2 of the "4 new objectives" set (see `CLAUDE.md`). Both were
blocked on Narwhal code access. Unblocked by cloning the actual baseline repo
(`nibeshrestha/sailfish`, public on GitHub) into a scratch directory and
reading the mempool/primary pipeline directly — not inferred from behavior,
read from source. Sibling docs: `PRBC_C_TESTING.md`, `OBJECTIVE4_TESTING.md`.

```bash
git clone --depth 1 https://github.com/nibeshrestha/sailfish.git
```

## The one-line answer

**Both objectives trace back to the same design choice.** PRBC and Narwhal
both face the same problem — a node may need to act on a vertex/header before
it has the referenced payload locally. **Both require the payload locally
before voting on it** — PRBC parks the propose in `pending_on_batch` until the
batch arrives (`prbc_sailfish.rs:1707-1724`). The difference is what *else*
they wait for. Narwhal adds a **delivery-ack quorum** before a digest is even
header-eligible, and pays for it in latency. PRBC adds **no acknowledgement
phase at all**, and instead spends network on a redundant S1/S2 relay layer
(`PRBC_C_TESTING.md`) so the payload is usually already present when the
propose lands, falling back to an asynchronous recovery fetch when it is not. Neither is "wrong" — they're opposite points on the same
trade-off curve, and this project's numbers show PRBC's side of that trade-off
wins for this workload.

> **Correction, 20 October 2026 — read before objective 1.** The two blocking
> points described below are real and correctly read from Narwhal's source.
> But the *measured* latency they were taken to explain was mostly something
> else. Tracing every sample transaction through Narwhal's own logs showed
> that, under its default configuration (`header_size` 50 B, `max_header_delay`
> 5,000 ms), digests waited a long time for the *next header*, because headers
> formed slowly at low and moderate load. With `header_size` 30 B and
> `max_header_delay` 1,000 ms, the acknowledgement path takes tens of
> milliseconds and Narwhal's end-to-end latency falls several-fold (n=50,
> 75k: 4,637 to 1,159 ms). The latency gap is therefore far smaller than this
> document's numbers imply, and it is not explained by the acknowledgement
> wait. Full evidence: `EVALUATION_RESULTS.md` sections 8.2 and 8.5. The network
> findings in objective 2 are unaffected.

## Objective 1 — why Narwhal's latency is higher (and erratic)

Two separate blocking points found in the source, stacked on top of the
DAG-BFT round logic both protocols share (both are Bullshark-family: leader
per round, order via causal history from a certified leader — `consensus/src/lib.rs`
`leader()` / `order_dag()` in Narwhal, `try_committing_prbc` /
`commit_causal_history_prbc` in ours; comparable in shape).

**1. Worker-level: batch dissemination blocks on a delivery quorum before a
digest is even eligible for a header.**

`worker/src/batch_maker.rs::seal()` broadcasts a sealed batch to the other
workers, then hands it to `QuorumWaiter` — not to the primary yet:

```rust
// worker/src/quorum_waiter.rs
// Wait for the first 2f nodes to send back an Ack. Then we consider the batch
// delivered and we send its digest to the primary (that will include it into
// the dag). This should reduce the amount of synching.
let mut total_stake = self.stake;
while let Some(stake) = wait_for_quorum.next().await {
    total_stake += stake;
    if total_stake >= self.committee.quorum_threshold() {
        self.tx_batch.send(batch).await...
        break;
    }
}
```

Only once 2f acks come back does the digest even reach the primary's
`Proposer` (`worker/src/primary_connector.rs`). This is a full network
round-trip — broadcast, then wait for the (n-f)th response — that sits
**before** the DAG round's own voting even starts. PRBC has no equivalent:
`accept_batch` broadcasts the payload and the vertex/propose referencing its
digest goes out immediately; nothing gates on delivery acks.

**2. Primary-level: processing (and therefore voting on) a header is
suspended entirely if the local node doesn't already have the referenced
payload.**

`primary/src/core.rs::process_header()`:

```rust
// Ensure we have the payload. If we don't, the synchronizer will ask our
// workers to get it, and then reschedule processing of this header once we
// have it.
if self.synchronizer.missing_payload(header).await? {
    debug!("Processing of {} suspended: missing payload", header);
    return Ok(());
}
// ... vote is only cast after this point
let vote = Vote::new(header, &self.name, &mut self.signature_service).await;
```

If even one referenced batch hasn't arrived yet, the header is dropped from
processing until the synchronizer fetches it and the caller re-triggers
processing — voting doesn't happen in the meantime. **PRBC does the same thing
at this point** (`prbc_sailfish.rs:1707-1724`): a propose whose batch is not in
the local `BatchStore` is parked in `pending_on_batch`, no vote is cast until
it arrives, and `start_recovery` is armed as the asynchronous fallback. The
asymmetry is not here — it is gate 1 above, which PRBC has no equivalent of,
plus the fact that PRBC's relay layer keeps the local-availability wait short
in the common case (measured: `Payload-lag events` ≈ `Payload post-quorum`,
with `Network recoveries` near zero).

**Why this also explains objective 4's non-monotonicity.** Both gates are
per-batch, per-node, and depend on the *specific* peers involved that round —
a single slow worker's ack, or a single missing batch on the path to
quorum, stalls that header's processing until it resolves. That's a
structural reason to expect exactly the kind of erratic, non-monotonic
latency `OBJECTIVE4_TESTING.md` found (16k reproducibly bad, 17k/18k/19k
clean, 30k fine, 50k/100k collapse) — tail-sensitive blocking points, not a
smooth function of aggregate load. PRBC's digest-only voting path has no
equivalent per-round blocking dependency on payload arrival, which lines up
with its measured latency being smooth and reproducible across its entire
tested range.

## Objective 2 — why Narwhal uses less network

`worker/src/batch_maker.rs::seal()`:

```rust
// Broadcast the batch through the network.
let (names, addresses): (Vec<_>, _) = self.workers_addresses.iter().cloned().unzip();
let bytes = Bytes::from(serialized.clone());
let handlers = self.network.broadcast(addresses, bytes).await;
```

`workers_addresses` is "the network addresses of the other workers that share
our worker id" — with `--workers 1` (our test config), that's every other
node's single worker: **one flat one-to-all broadcast, n-1 recipients, once.**
No resampling, no relay tier. Checked the header/vote/certificate path too
(`primary/src/core.rs`) — same pattern, one broadcast to `others_primaries`,
no redundant relay there either. **There is nothing in Narwhal's pipeline
structurally equivalent to PRBC's S1→S2 relay.**

This matches the math in `PRBC_C_TESTING.md` exactly: the fitted model there
found PRBC's Dissemination traffic is `73.7 + 7.393×sample_size²` Mbps, where
73.7 Mbps is independently derived as the bare one-to-all broadcast cost
(2,000 tx/s/node × 512B × 9 peers × 8 bits). That 73.7 Mbps base term **is**
what Narwhal's batch dissemination alone costs — Narwhal doesn't pay the
`7.393×sample_size²` term on top because it doesn't have the redundancy layer
that term measures. At PRBC's default setting (sample size 5), 71.5% of its
Dissemination traffic is exactly this extra insurance layer Narwhal skips.

**Confirmed live, not just structurally.** `monitor_cluster.py` run alongside
a Narwhal 20,000 tx/s run (matched to the `PRBC_C_TESTING.md` default-setting
reference point) measured **~67-70 Mbps average NIC Tx/Rx per machine** on all
9 non-node-0 hosts (node-0's 343 Mbps Rx peak is log-collection SCP traffic
after the run, not steady-state consensus traffic). PRBC's measured
Dissemination plane at the identical rate/settings is **258.4 Mbps per
node** — **~3.7× more network for PRBC at matched throughput.**

Three independent lines of evidence now agree: the code (no relay tier in
Narwhal's `batch_maker.rs`), the fitted model (73.7 Mbps calculated
bare-broadcast baseline, independent of this measurement), and the live NIC
reading (67-70 Mbps measured) all land on essentially the same number.
Objective 2 is closed — not just argued from source, but measured directly
against PRBC's own figure at the same workload.

```bash
# Terminal 1, from ~/Sparse_Bullshark on node-0 — avoid "node" anywhere in the
# command line (see gotcha below), so the manual per-run pkill loop doesn't
# catch this process when it SSHes into node-0 itself:
python3 scripts/cluster/monitor_cluster.py --hosts "10.164.0.12 10.164.0.6 10.164.0.11 10.164.0.8 \
  10.164.0.9 10.164.0.10 10.164.0.13 10.164.0.14 10.164.0.15 10.164.0.16" \
  --duration 85 --trim 5

# Terminal 2, from ~/sailfish/benchmark — kill stale processes then run at 20,000
```

## The trade-off, stated plainly

| | Handles "vertex ready before payload" by | Cost |
|---|---|---|
| **PRBC-Sailfish** | Waiting for the payload locally, but with no acknowledgement phase; redundant S1/S2 relay keeps that wait short | Network (3.5× the bare broadcast at default settings) |
| **Narwhal Sailfish** | Blocking: wait for 2f delivery acks before a digest is header-eligible; suspend header processing until payload is locally present | Latency (extra round-trips on the critical path, sensitive to whichever peer is slowest that round) |

Given this project's actual results — PRBC wins on latency by 4.6-7× at a
fixed throughput-under-budget comparison (`OBJECTIVE4_TESTING.md`), and by
2.6× at matched workload (`CLAUDE.md` main table) — paying in network to save
that much latency is a good trade for this benchmark's stated goal (show our
protocol's latency is better). It would be a worse trade if the thesis cared
primarily about network cost instead.

## Gotcha hit while measuring this

`monitor_cluster.py` got silently killed mid-run, twice, before the actual
cause was found. Not `run_cluster.py`'s own startup logic — the **manual**
per-run cleanup loop (`for h in <all 10 IPs>; do ssh $h "pkill -f node; ..."; done`)
includes node-0 itself in its host list, so node-0 SSHes into itself and runs
`pkill -f node` locally. `pkill -f` matches the **entire command line**, and
`--hosts-file shared/nodes_distributed.csv` contains the substring "node"
(from "**node**s_distributed") — enough to match and kill the monitor even
though its own filename didn't. Fix: pass `--hosts "<ip list>"` directly
instead of `--hosts-file`, so "node" never appears in the command line at all.

## Pending

- Optional: read `primary/src/synchronizer.rs` and `worker/src/synchronizer.rs`
  in full to characterize exactly how expensive a missing-payload recovery is
  in Narwhal (network cost, retry timing) — the rough Narwhal analogue of
  `RECOVERY_TESTING.md`, if a deeper mechanism-level comparison is wanted
  later.
