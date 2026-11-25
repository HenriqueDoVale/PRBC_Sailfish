# Results inventory — every benchmark number on record

Compiled 15 October 2026. **Collation only — nothing here is new analysis.**
Every figure is copied from a named source. Where two sources disagree about
the same cell, both are shown and the conflict is listed in §7.

Purpose: decide what goes in the evaluation chapter, and find what is missing
or needs re-running before it can be used.

---

## 1. Testbeds — three of them, not comparable to each other

| ID | Description | Used by |
|---|---|---|
| **T1** | Single machine, 48 vCPU, loopback networking | earliest n=10/20 data |
| **T2** | **10 machines**, GCP europe-west4-a, 8 vCPU / 8 GB. `n2d-highcpu-8` except one `e2-highcpu-8` (.6). Density: 1 node/machine at n=10, 2 at n=20, 3 at n=30, **5 at n=50** | most of Jul–Aug 2026 |
| **T3** | **50 machines**, GCP **N2**, 8 vCPU each, **1 node per machine at every n**. (N2D quota capped at 100 vCPU = 12 nodes; switched to N2 after a 400-vCPU increase) | Sep–Oct 2026 |

**T2 vs T3 is the single most important distinction in this document.** On T2
the node count rises by packing more nodes onto the same ten machines, so
every T2 scaling curve mixes protocol scaling with per-node resource
contention. On T3 it is a clean 1:1 mapping. Numbers must never be compared
across testbeds.

All runs everywhere: 512 B transactions, 60 s measurement window, 0 injected
faults, LAN, unless stated.

---

## 2. Protocol variants

| Short name | What it is |
|---|---|
| **PRBC-orig** | Original PRBC-Sailfish. Full 256 KB payload carried inline in every consensus message. O(n²) payload traffic. |
| **PRBC-T1** | PRBC-orig + Tier 1 CPU optimizations (Arc broadcast, batch Ed25519 verify, sample caching, HashSet edges). Same architecture. |
| **PRBC-T2** | PRBC-T1 + Tier 2 (event-loop drain, multicast dispatch, hash-only DAG index, vertex moves, frame-auth skip). Same architecture. |
| **PRBC-C3** | PRBC-T2 + "Change 3" commit rule (commit on ≥2f+1 Proposes instead of hash-quorums). |
| **APRBC** | The current protocol. 3-plane TCP (Control / ConsensusData / Dissemination), batch broadcast *before* vertex creation, vertex carries only a 32-byte digest, voting gated on local batch availability, vote key (round, source, hash), equivocation guard. |
| **Sailfish-inline** | Our Sailfish with payload inline, `RBC_MODE=signed_vote`. Also called "Sailfish SV-RBC". |
| **Narwhal** | `nibeshrestha/sailfish` baseline, run through its own harness. |

> **Attribution to resolve:** you call the APRBC changes "Hasan's"; the
> *Stable Benchmark Summary* artifact labels the same change set
> "Professor's optimizations (Aug 2026)". `CLAUDE.md` records the branch as
> `origin/prbc-performance-improvements` (Hasan's, `b9735e1`). Decide which
> attribution the thesis uses.

---

## 3. Source index

| Source | Date | Testbed | Covers |
|---|---|---|---|
| **A1** — artifact *Consensus Protocol Benchmark Results* (`8xEkT4Ay…`) | 28 Jul | T1 + T2 | PRBC-orig/T1/T2/C3, Sailfish-inline, Narwhal; peak + stable; Tier 1 & 2 optimization studies; quorum experiment; bandwidth analysis |
| **A2** — artifact *Stable Benchmark Summary* (`BMRnxwBf…`) | 12 Aug | T2 | PRBC-orig vs APRBC vs Narwhal vs Sailfish-inline, n=10/20/30/50 |
| **A3** — artifact *PRBC vs Narwhal Campaign* (shared) | — | T2 | APRBC vs Narwhal, n=10/20/30/50, 3 reps, + resource + amplification |
| **A4** — artifact *WAN Latency Experiment* (`Et4U4SjS…`) | 12 Aug | T2 (n=10) | APRBC vs Sailfish-inline at 0/50/100 ms RTT |
| **A5** — artifact *Latency Re-measured* (`VSyjK8iM…`) | 1 Oct | T3 | current APRBC vs Narwhal |
| **M1** — `THIS_WEEKS_WORK.md` | Sep–Oct | T3 | ceiling sweeps both protocols, batch-size sweeps, matched comparisons, pacing fix |
| **M2** — `RECOVERY_TESTING.md` | Sep | T2 (n=7–10) | recovery rate vs hypergeometric model |
| **M3** — `PRBC_C_TESTING.md` | Sep | T2 (n=10) | `PRBC_SAMPLE_C` sweep, cost and benefit |
| **M4** — `OBJECTIVE4_TESTING.md` | Sep | T2 (n=10) | TPS under a 1000 ms latency budget |
| **M5** — `OBJECTIVE1_2_ANALYSIS.md` | Sep | T2 (n=10) | network cost, code-level mechanism |

Artifacts *This Week's Work* and *Past Week's Work* duplicate M1–M5 and add
no numbers. *Thesis Research Plan* and *thesis_context.md* contain no results.

---

## 4. Testbed T1 — single machine, 48 vCPU, loopback

Source A1. **PRBC variant here is PRBC-orig/T2 era, not APRBC.**

### Peak, n=10

| Protocol | Input | Peak TPS | Cons. latency | CPU | Bottleneck |
|---|---|---|---|---|---|
| PRBC | 400,000 | 137,325 | 80.9 ms | ~60% | protocol (round rate) |
| Sailfish-inline | 100,000 | 98,258 | 112.6 ms | 90–95% | CPU (sig verify) |
| Narwhal | 300,000 | 143,206 | 3,000 ms | 40–50% | input queue / clients |

### Stable, n=10

| Protocol | Input | Stable TPS | Cons. latency | CPU |
|---|---|---|---|---|
| PRBC | 100,000 | 99,825 | 106.6 ms | 29–33% |
| Sailfish-inline | 75,000 | 77,250 | 133.9 ms | 60–67% |
| Narwhal | 100,000 | 97,833 | 301 ms | ~15% |

Also T1: quorum experiment, n=20 at 100,000 → 97,792 TPS at 2f+1; f+1 "≈
identical". 

---

## 5. Testbed T2 — 10 machines (density rises with n)

### 5.1 A2 — the four-protocol table (the closest thing to comparison A and B)

All at each protocol's own ceiling. Cons. = consensus latency.

| n | PRBC-orig TPS / cons / e2e / input | APRBC TPS / cons / e2e / input | Narwhal TPS / cons / e2e / input | Sailfish-inline TPS / cons / input |
|---|---|---|---|---|
| 10 | 146,500 / ~69 ms / ~98 ms / unlimited | 136,900 / 71.3 ms / 163 ms / 140k | 192,400 / ~706 ms / ~3,800 ms / 200k | 92,825 / 90.2 ms / 90k (18.6 rnd/s) |
| 20 | 79,667 / ~256 ms / ~312 ms / 80k | 119,317 / 165.9 ms / 228 ms / 120k | 167,631 / ~1,070 ms / ~3,050 ms / 176k | 19,458 / 907 ms / 20k (2.1 rnd/s) |
| 30 | 69,475 / ~442 ms / ~531 ms / 70k | 89,508 / 330.7 ms / 423 ms / 90k | 123,200 / ~1,500 ms / ~3,400 ms / 125k | 13,100 / 1,943 ms / 14k (0.9 rnd/s) |
| 50 | 29,183 / ~1,684 ms / ~1,935 ms / 30k | 59,175 / 863 ms / 1,101 ms / 60k | 44,035 / ~1,038 ms / ~1,800 ms / 50k | **deadlocked, 0 runs** |

Run counts and spreads (A2 footnote):
- PRBC-orig: 10n 3 runs unlimited (~144–149k, 1.5% var); 20n 3 runs (±25 TPS); 30n 3 runs identical rounds; 50n 3 runs identical TPS.
- APRBC: 10n 136,650 / 136,900 / 136,908 (<0.2%); 20n 119,000 / 119,317 / 119,342 (<0.3%), cons 165–176 ms, e2e 224–261 ms; 30n 89,500 / 89,508 / 89,508, cons 330–331 ms, e2e 423 ms; 50n 59,175 ×3 (**0% variance**), cons 863 ms, e2e 1,099–1,110 ms.
- Narwhal: 10n mean of 4 (~192–197k); 20n mean of 4 (166–169k); 30n mean of 3 (<0.3%); 50n mean of 3 (43–44k).
- Sailfish-inline: 10n 92,825 ×3; 20n 19,350 / 19,458 / 19,458; 30n 12,700 / 13,100 / 13,108; 50n **deadlocked at all rates**.

APRBC vs PRBC-orig, as A2 states it: TPS −7% at n=10, **+50%** at n=20, **+29%** at n=30, **+103%** at n=50. Consensus latency ~same / −35% / −25% / −49%.

### 5.1b Sailfish-inline round rate (same A2 runs)

rounds/s: n=10 **18.6**, n=20 **2.1**, n=30 **0.9**, n=50 **deadlock**.
Cross-check: rounds/s x n x 500 reproduces the A2 TPS column exactly
(18.6x10x500 = 93,000 vs 92,825 measured), confirming these are the T2 runs.

**Sailfish-inline was never run on T3.** `THIS_WEEKS_WORK.md` contains no
inline/signed_vote runs at all. Comparison A therefore rests entirely on the
contended 10-machine testbed.

### 5.2 A3 — the campaign (APRBC vs Narwhal, 3 reps)

Ceiling = highest input with η ≥ 0.95.

| n | Protocol | Ceiling input | Delivered TPS | Cons. latency | E2E latency |
|---|---|---|---|---|---|
| 10 | APRBC | 140,000 | 138,008 | 70.1 ms | 141.9 ms |
| 10 | Narwhal | 200,000 | 199,680 | 868 ms | 3,008 ms |
| 20 | APRBC | 135,000 | 129,133 | 154.7 ms † | 441.6 ms † |
| 20 | Narwhal | 176,000 | 170,683 | 1,406 ms | 3,548 ms |
| 30 | APRBC | 90,000 | 89,492 | 331.1 ms | 426.7 ms |
| 30 | Narwhal | 126,000 | 122,286 | 1,378 ms | 3,178 ms |
| 50 | APRBC | 66,000 | 63,467 (**1 run**) | 797.9 ms | 1,056.2 ms |
| 50 | Narwhal | 54,000 | 52,711 | 1,141 ms † | 2,166 ms † |

† A3's own latency section gives different values for these two cells:
APRBC n=20 → 195.6 ms cons / 245.7 ms e2e; Narwhal n=50 → 1,063 ms cons /
1,739 ms e2e. A3 does not reconcile them.

A3 latency ratios (its own table): n=10 12.4× cons / 21.2× e2e; n=20 7.2× /
14.4×; n=30 4.2× / 7.4×; n=50 1.3× / 1.6×.

**A3 bistability warning:** APRBC at n=50 reached 63,467 **once in seven
attempts**. The other six: 57,250 / 42,742 / 42,825 / 42,825 / 36,567 /
21,925. Three runs at 60,000 offered gave 59,175 TPS, 865.4 ms cons,
1,115.2 ms e2e.

**A3 Narwhal n=50 note:** five of eleven sweep runs had η > 1 (up to 1.051).
Two runs at 55,000 gave 983 and 1,125 ms consensus latency.

### 5.3 A3 — resource use (monitor_cluster.py, 1 Hz)

| n | Protocol | CPU avg | CPU peak | NIC Tx avg | NIC Tx peak | % NIC cap | Verdict |
|---|---|---|---|---|---|---|---|
| 10 | APRBC | 9–18% | 30–40% | 779–1,496 Mbps | 2,087–2,740 | 13–17% | clean |
| 10 | Narwhal | 18–20% | 52–59% | 697–735 | 839–864 | 5% | clean |
| 20 | APRBC | 27% | 48–62% | 2,065–2,080 | 3,013–3,955 | 19–25% | clean |
| 20 | Narwhal | 31–35% | 78–87% | 1,151–1,314 | 1,691–1,741 | 11% | 1 orchestrator |
| 30 | APRBC | 42% | 69–73% | 2,511–2,540 | 3,820–4,482 | 24–28% | clean |
| 30 | Narwhal | 39–42% | 93–99% | 1,323–1,393 | 1,841–1,975 | 12% | 2 machines + orch. |
| 50 | APRBC | 46–47% | 74–87% | 2,062–2,064 | 3,128–3,278 | 20% | 1 e2 machine |
| 50 | Narwhal | 52–58% | **100%** | 703–778 | 982–1,094 | 6–7% | **all 10 machines** |

Cores per 10k tx/s (APRBC / Narwhal): 0.99/0.80, 2.17/1.55, 3.75/2.68,
8.51/**10.99**.

A3 caveat: at n=50 Narwhal runs ten processes per machine vs APRBC's five, so
the 100% CPU is partly a testbed floor.

### 5.4 A3 — amplification (bytes on wire ÷ useful bytes)

| n | \|S\| | APRBC predicted | APRBC measured | Narwhal predicted | Narwhal measured |
|---|---|---|---|---|---|
| 10 | 5 | 30 | 26.0 | 9 | 8.7 |
| 20 | 7 | 56 | 50.9 | 19 | 18.3 |
| 30 | 8 | 72 | 69.2 | 29 | 26.7 |
| 50 | 10 | 110 | 114.1 | 49 | 45.9 |

Formulas written before the runs. Narwhal within 6%, APRBC within 13%.

### 5.5 A1 — PRBC-orig/T2 era on T2, peak and stable

Peak:

| n | PRBC input / TPS / cons / CPU | Sailfish-inline input / TPS / cons / CPU | Narwhal input / TPS / cons / CPU |
|---|---|---|---|
| 20 | 100k / 80,625 / 290.1 ms / 67–72% | 50k / 25,558 / 875.5 ms / ~98% (T1 values) | 200k / 191,946 / 1,402 ms / 40–80% |
| 30 | 700k / 63,217 / 554.3 ms / 85–90% | 10k / 5,992 / 6,051 ms / ~99% | 75k / 70,903 / 1,083 ms / ~65% |
| 50 | 30k / 29,042 / 1,912 ms / 84–90% | 5k / 3,225 / 14,301 ms / ~100% | 65k / 59,479 / 1,154 ms / 60–80% |

Stable:

| n | PRBC input / TPS / cons | Sailfish-inline input / TPS / cons | Narwhal input / TPS / cons |
|---|---|---|---|
| 20 | 100k / 80,625 / 290.1 ms | 25k / 25,450 / 848.6 ms | 150k / 145,912 / 1,447 ms |
| 30 | 700k / 63,217 / 554.3 ms | 5k / 4,725 / 6,648 ms | 51k / 49,377 / 1,456 ms |
| 50 | 20k / 19,450 / 1,747 ms | 5k / 3,225 / 14,301 ms | 50k / 48,870 / 1,132 ms |

### 5.6 A1 — optimization studies

Tier 1 (n=20, 100k): TPS 79,125 → 76,967 (≈same), CPU ~90% → 67% (−23 pp),
latency 294.9 → 302.9 ms. **n=50 (30k): zero measurable effect** — TPS
29,075 → 29,042, CPU 83–90% → 85–88%, latency 1,903 → 1,912 ms.

Tier 2 (n=20, 100k): 76,967 → **80,625** TPS (+4.8%), latency 302.9 → 290.1
ms (−4.2%). n=30: baseline 39,500 → **63,217** TPS (+60%), latency 871.9 →
554.3 ms (−36%), CPU ~98% → 85–90%. n=50: again **zero change**.

Change 3 (commit on ≥2f+1 Proposes): n=20 80,625 → 79,292 TPS, 290.1 →
294.4 ms (+1.5%); n=50 29,042 → 29,042, 1,912 → 1,930 ms (+0.9%). **No
detectable improvement** — predicted ~1 RTT saving is below the measurement
floor (variance ±5.8 ms at n=20, ±38.2 ms at n=50).

Additional A1 rate points:

| n | input | TPS | latency | CPU | note |
|---|---|---|---|---|---|
| 20 | 50,000 | 49,658 | 433.1 ms | ~45% | low-load, headroom |
| 20 | 85,000 | 79,125 | 295.3 ms | 68–79% | near ceiling |
| 20 | 100,000 | 79,292 | 294.4 ms | 68–79% | saturated |
| 30 | 60,000 | 59,425 | 578.0 ms | 81–89% | peak |
| 30 | 65,000 | 43,625 | 554.4 ms | 90–95% | **over — TPS drops** |
| 50 | 30,000 | 29,042 | 1,930 ms | 84–88% | peak |
| 50 | 33,000 | 18,208 | 1,792 ms | 93–100% | **crash, 10/50 nodes** |

### 5.7 A1 — bandwidth per transaction

| n | PRBC TPS / NIC MB/s / KB-per-tx | Narwhal TPS / NIC MB/s / KB-per-tx | ratio |
|---|---|---|---|
| 20 | 79,842 / 505 / **6.5** | 177,710 / 260 / **1.5** | 4.3× |
| 30 | 60,383 / 540 / **9.2** | 72,629 / 228 / **3.2** | 2.9× |
| 50 | 29,042 / 413 / **14.6** | 60,728 / 215 / **3.6** | 4.1× |

### 5.8 A1 — quorum experiment (`REDUCED_QUORUM`)

| n | env | input | 2f+1 | f+1 | verdict |
|---|---|---|---|---|---|
| 20 | T1 | 100,000 | 97,792 TPS | ≈ identical | no improvement |
| 30 | T2 | 25,000 | ~25,000 stable | more crashes | unstable |
| 50 | T2 | 10,000 | 9,793 TPS | ≈ identical | no improvement |
| 50 | T2 | 30,000 | 29,075 TPS | **10/50 nodes crash** | safety violation |

All with 0 actual Byzantine faults.

### 5.9 A4 — WAN, n=10, APRBC vs Sailfish-inline (consensus latency, ms)

| rate | APRBC LAN | 50 ms RTT | 100 ms RTT | Sailfish LAN | 50 ms RTT | 100 ms RTT |
|---|---|---|---|---|---|---|
| 1k | 9,456 | 9,482 | 9,510 | 9,024 | 9,513 | 9,390 |
| 5k | 1,900 | 1,907 | 1,926 | 1,794 | 1,882 | 1,951 |
| 10k | 950 | 955 | 961 | 892 | 911 | **1,165 ⚠** |
| 15k | 634 | 639 | 643 | 593 | 601 | **1,889 ⚠** |
| 20k | 475 | 480 | 487 | 442 | 451 | **2,666 ⚠** |

⚠ = saturated. Delivered TPS at 100 ms RTT — APRBC: 842 / 4,842 / 9,842 /
14,842 / **19,842**. Sailfish: 925 / 5,083 / 5,808 / 4,192 / **3,025**.

Note: at LAN, Sailfish-inline is *slightly faster* than APRBC at every rate.

### 5.10 M2 — recovery validation (n=7–10)

Timeout sweep, n=10, 20k, node 0 = Byz1 (excludes nodes 8, 9):

| timeout | background avg (0–7) | node 8 | node 9 |
|---|---|---|---|
| 5 ms | 7.8 | 44 | 33 |
| 10 ms | 5.6 | 24 | 40 |
| 20 ms | 3.6 | 20 | 25 |
| 50 ms | **0.4** | 28 | 23 |
| 100 ms | 1.1 | 19 | 33 |
| 500 ms | 8.1 | 33 | 44 |

Model vs measurement:

| n | excluded | predicted % | observed % | diff |
|---|---|---|---|---|
| 7 | 6 | 10.2% | 8.8% | −1.4 pp |
| 8 | 6, 7 | **20.1%** | **17.7%** | −2.4 pp |
| 9 | 6, 7, 8 | 12.8% | 11.2% | −1.6 pp |
| 10 | 8, 9 | 10.2% | 9.0% | −1.2 pp |

Predicted rates also computed for n=20 (15.6%), n=30 (22.2%), n=50 (24.0%)
— **not measured**.

### 5.11 M3 — `PRBC_SAMPLE_C` sweep, n=10

Cost:

| C | sample | Dissem. Mbps | CPU (machine) | Cons. latency | E2E latency |
|---|---|---|---|---|---|
| 0.5 | 2 | 103.3 | 1.3% | 475.8 ms | 485.2 ms |
| 0.8 | 3 | 140.3 | 1.6% | 476.0 ms | 486.4 ms |
| 1.0 | 4 | 192.1 | 1.9% | 476.0 ms | 486.9 ms |
| **1.4** | 5 | **258.4** | 2.4% | 476.2 ms | 487.9 ms |
| 1.8 | 6 | 340.1 | 3.0% | 476.1 ms | 488.2 ms |
| 2.2 | 7 | 435.6 | 3.7% | 476.2 ms | 489.6 ms |
| 3.0 | 10 | 813.1 | 5.9% | 477.0 ms | 493.1 ms |

Benefit (recoveries):

| C | sample | predicted | node 8 | node 9 | avg | ratio |
|---|---|---|---|---|---|---|
| 0.5 | 2 | 176.5 | 183 | 165 | 174.0 | 0.99× |
| 0.8 | 3 | 116.7 | 128 | 111 | 119.5 | 1.02× |
| 1.0 | 4 | 61.6 | 70 | 70 | 70.0 | 1.14× |
| 1.4 | 5 | 24.3 | 22 | 17 | 19.5 | 0.80× |
| 1.8 | 6 | 6.4 | 8 | 9 | 8.5 | 1.33× |
| 2.2 | 7 | 0.9 | 1 | 1 | 1.0 | 1.11× |
| 3.0 | 10 | 0.0 | 1 | 1 | 1.0 | — |

Fitted: dissemination = `73.7 + 7.393 × sample²` Mbps. Verdict: C=1.8 costs
+30% network for a 65% cut in recovery need.

### 5.12 M4 — TPS under a 1000 ms E2E budget, n=10

APRBC: 1k 9,456 ✗ / 5k 1,900 ✗ / 8k 1,198.7 ✗ / 9.6k 1,000.2 borderline /
10k 950 ✓ / 15k 634 ✓ / 20k 475 ✓ / 80k 137.8 ✓ / 110k 108.0 ✓ / **130k 98.3
✓** / 140k 147.9 ✓ (past ceiling) / 150k 280.8 ✓ (oversaturated).

Narwhal: 1k 2,966 ✗ / 5k 2,385 ✗ / 10k 1,696 ✗ / 15k 652 ✓ / **16k 1,250 /
1,837 / 1,703 ✗ (all 3)** / 17k 433 ✓ / 18k 641 ✓ / **19k 635 / 747 / 1,020
(2/3 ✓)** / **20k 1,228 / 453 / 1,275 (1/3 ✓)** / 30k 473 ✓ / 50k 4,200 ✗ /
100k 3,642 ✗.

Answer: APRBC ~136–138k tx/s; Narwhal ~19–30k. **4.6–7×.**

### 5.13 M5 — network, n=10 at 20k matched

APRBC dissemination **258.4 Mbps/node** vs Narwhal **67–70 Mbps/machine** —
**~3.7×**.

---

## 6. Testbed T3 — 50 machines, 1 node per machine

### 6.1 M1 — APRBC ceiling sweep (`MAX_BATCH_DELAY_MS` disabled, 500-tx)

n=10, ceiling ≈ 120–125k:

| input | η | E2E |
|---|---|---|
| 100,000 | 99.8% | 131–132 ms |
| 120,000 | 95.9% | 366.7 ms |
| 130,000 | 92.1% | 838.6 ms |
| 150,000 | 83.4% | 1,501.2 ms |

n=20, ceiling ≈ 120–125k:

| input | η | E2E | Recovery resp served | Peak RSS |
|---|---|---|---|---|
| 80,000 | 99.6% | 310.2 ms | 3 | 78 MB |
| 100,000 | 99.7% | 265.2 ms | 1 | 82 MB |
| 120,000 | 96.95% | 395.2 ms | 1,921 | 510 MB |
| 125,000 | 95.34% | 604.4 ms | 2,675 | 680 MB |
| 130,000 | 93.08% | 823.3 ms | 3,312 | 817 MB |

n=30, ceiling ≈ 110–115k. Cross-check point: 110,000 → 106,433 TPS, η 96.76%,
E2E 552.5 ms, batches cached 302, RSS 552 MB. **Per-point sweep numbers were
never transcribed — they live only in terminal scrollback.**

n=50, ceiling ≈ 75k:

| input | TPS | η | E2E | Peak RSS | Batches cached |
|---|---|---|---|---|---|
| 65,000 | 64,175 | 98.7% | 1,000.0 ms | 146 MB | 102 |
| 70,000 | 69,175 | 98.8% | 946.8 ms | 152 MB | 102 |
| 75,000 | 74,167 | 98.9% | 903.2 ms | 155 MB | 101 |
| 77,500 | 72,750 | 93.9% | 888.2 ms | 252 MB | 570 |
| 77,500 (repeat) | 65,692 | 84.8% | 875.0 ms | 462 MB | 1,417 |
| 80,000 | 72,300 | 90.4% | 929.5 ms | 352 MB | 918 |
| 80,000 (repeat) | 72,292 | 90.4% | 911.2 ms | 343 MB | 924 |
| 100,000 | 40,225 | 40.2% | 2,413.2 ms | 2,018 MB | 7,060 |

Summary: n=10 ~120–125k, n=20 ~120–125k (flat), n=30 ~110–115k, n=50 ~75k.
All four cross-checked with `monitor_cluster.py`: CPU 17–22% avg, NIC 7–12%
of cap — **not testbed-limited at any n**.

### 6.2 M1 — Narwhal ceiling sweep (matched 256,000 B batches, 50 ms delay)

n=10, ceiling ≈ 275k:

| rate | TPS | η | cons | E2E |
|---|---|---|---|---|
| 150,000 | 148,976 | 99.3% | 202 ms | 2,530 ms |
| 200,000 | 196,010 | 98.0% | 1,696 ms | 4,381 ms |
| 250,000 | 243,467 | 97.4% | 823 ms | 3,043 ms |
| 275,000 | 260,601 | 94.8% | 175 ms | 2,565 ms |
| 300,000 | 268,354 | 89.5% | 212 ms | 2,489 ms |

n=20, ceiling ≈ 250–255k:

| rate | TPS | η | cons | E2E |
|---|---|---|---|---|
| 200,000 | 198,503 | 99.3% | 761 ms | 3,049 ms |
| 250,000 | 238,879 | 95.6% | 546 ms | 2,784 ms |
| 260,000 | 162,006 | **62.3%** | 5,061 ms | 7,618 ms |
| 275,000 | 107,983 | 39.3% | 553 ms | 2,835 ms |

n=30, ceiling ≈ 250–260k:

| rate | TPS | η | cons | E2E |
|---|---|---|---|---|
| 200,000 | 197,878 | 98.4% | 297 ms | 1,593 ms |
| 230,000 | 225,872 | 98.2% | 358 ms | 2,041 ms |
| 250,000 | 241,016 | 96.4% | 475 ms | 2,041 ms |
| 260,000 | 234,399 | 90.2% | 392 ms | 2,063 ms |

n=50 batch-delay sensitivity:

| delay | effective batch | η | E2E |
|---|---|---|---|
| 50 ms | ~75 tx | ~85% | 585 ms |
| 400 ms | 500 tx | **98.7%** | 5,043 ms |

n=50 rate sweep with full batches (delay 400), ceiling ≥200k:

| rate | TPS | η | E2E |
|---|---|---|---|
| 75,000 | 74,050 | 98.73% | 5,043 ms |
| 100,000 | 99,126 | 99.13% | 3,735 ms |
| 125,000 | 123,809 | 99.05% | 2,120 ms |
| 150,000 | 148,031 | 98.69% | 848 ms |
| **175,000** | **172,314** | 98.47% | **785 ms** ← min |
| 200,000 | 194,695 | 97.35% | 1,145 ms |

### 6.3 M1 — the batch-size discovery and the governing model

`ceiling = rounds_max × n_tx × n`:

| n | n_tx | rounds_max | predicted | measured |
|---|---|---|---|---|
| 10 | 500 | 24 | 120k | ~120k |
| 10 | 1,000 | 19.2 | 192k | 191,983 |
| 10 | 2,000 | 11.6 | 232k | 232,033 |
| 10 | 4,000 | 6.2 | 248k | 248,000 |
| 50 | 500 | 3.0 | 75k | 74,167 |
| 50 | 2,000 | 1.5 | 150k | 146,700 |

n=10 batch-size sweep:

| n_tx | ceiling | best compliant point |
|---|---|---|
| 500 | ~120k | 110k @ **125.8 ms** (η 99.6%) |
| 1,000 | ~192k | 175k @ 169.8 ms (η 99.3%) |
| 2,000 | ~232k | 200k @ 277.9 ms (η 99.7%) |
| 4,000 | **~248k** | 250k @ 465.8 ms (η 99.2%) |

n=50 batch-size sweep:

| n_tx | rate | TPS | η | rounds/s | E2E |
|---|---|---|---|---|---|
| 500 | 75,000 | 74,167 | 98.9% | 3.0 | 903.2 ms |
| 2,000 | 100,000 | 96,700 | 96.7% | 1.0 | 2,452.7 ms |
| 2,000 | 150,000 | 146,700 | 97.8% | 1.5 | 1,796.2 ms |
| 2,000 | 200,000 | 64,567 | **32.3%** | 0.7 | 1,476.2 ms |

Revised ceilings, both tuned:

| n | n_tx | APRBC | Narwhal | APRBC as % |
|---|---|---|---|---|
| 10 | 4,000 | ~248k | ~275k | 90% |
| 20 | 2,000 | ≥225k | ~250k | ≥90% |
| 30 | 2,000 | ≥200k | ~250k | ≥80% |
| 50 | 2,000 | ~150k | ≥200k | ≤75% |

### 6.4 M1 — the matched-settings latency curve (500-tx both sides)

| n | rate | APRBC E2E | Narwhal E2E | ratio | TPS parity |
|---|---|---|---|---|---|
| 10 | 100,000 | 131.5 ms | 4,054 / 5,789 ms | **30.8–44.0×** | ~100% |
| 20 | 120,000 | 395.2 ms | 3,570 ms | **9.0×** | 97.6% |
| 30 | ~110,000 | 552.5 ms | 3,904 ms | **7.1×** | 96.4% |
| 50 | 75,000 | 903.2 ms | 5,043 ms | **5.6×** | 100.2% |

### 6.5 M1 — each protocol at its own best

| n | rate | APRBC | Narwhal | winner |
|---|---|---|---|---|
| 10 | 200k | 277.9 ms | 4,381 ms | APRBC **15.8×** |
| 10 | 250k | 465.8 ms | 3,043 ms | APRBC **6.5×** |
| 20 | 225k | 507.6 ms | 1,587 ms (η 94.8%) | APRBC **3.1×** |
| 30 | 200k | 843.7 ms | 1,593 ms | APRBC **1.89×** |
| 50 | 150k | 1,796 ms | 848 ms | **Narwhal 2.1×** |

### 6.6 A5 / M1 — 1 October clean-cluster re-measurement

Matched config, n=20, 120,000 offered, 500-tx both:

| | TPS | η | cons | E2E |
|---|---|---|---|---|
| APRBC | 116,508 | 97.1% | 171.6 ms | **393.7 ms** |
| Narwhal (delay 200) | 116,484 | 97.1% | 1,146 ms | **3,488 ms** |

Each at best:

| n | rate | APRBC | Narwhal | result |
|---|---|---|---|---|
| 20 | 120k | 394 ms (500 tx) | 3,169 ms (50 ms) | APRBC 8.05× |
| 20 | 260k | 911 ms (2000 tx) | 2,611 ms (50 ms) | APRBC 2.87× |
| 30 | 230k | 803 ms (2000 tx) | 1,657 ms (50 ms) | APRBC 2.06× |
| 50 | 75k | 906 ms (500 tx) | 5,043 ms (400 ms) | APRBC 5.6× |
| 50 | 150k | 1,796 ms (2000 tx) | 848 ms (400 ms) | Narwhal 2.1× |
| 50 | 200k | 2,774 ms (4000 tx) | 1,145 ms (400 ms) | Narwhal 2.4× |

Latency split:

| | n | rate | cons | E2E | pre-consensus |
|---|---|---|---|---|---|
| APRBC | 20 | 120k | 171.6 | 393.7 | 222 ms |
| APRBC | 30 | 230k | 552.0 | 802.5 | 250 ms |
| APRBC | 20 | 260k | 338.1 | 911.2 | 573 ms |
| Narwhal | 20 | 120k (200 ms) | 1,146 | 3,488 | 2,342 ms |
| Narwhal | 20 | 120k (50 ms) | 1,032 | 3,169 | 2,137 ms |
| Narwhal | 20 | 260k | 358 | 2,611 | 2,253 ms |
| Narwhal | 30 | 230k | 355 | 1,657 | 1,302 ms |
| Narwhal | 30 | 260k | 436 | 1,681 | 1,245 ms |

Clean-cluster throughput: APRBC 250,567 (n=20 @260k), 227,033 (n=30 @230k);
Narwhal 252,146 (n=20 @260k, η 97.0%), 243,488 (n=30 @260k, η 93.3%).

Before/after the cluster cleanup:

| point | before | after | change |
|---|---|---|---|
| APRBC n=20 120k 500tx | 395.2 ms | 393.7 ms | −0.4% |
| APRBC n=30 230k 2000tx | 793 ms | 802.5 ms | +1.2% |
| APRBC n=20 260k 2000tx | 950 ms | 911.2 ms | −4.1% |
| Narwhal n=20 120k 50 ms | 3,300 ms | 3,169 ms | −4.0% |
| Narwhal n=20 120k 200 ms | 3,570 ms | 3,488 ms | −2.3% |
| Narwhal n=30 230k 50 ms | 2,041 ms | 1,657 ms | **−18.8%** |
| Narwhal n=20 260k η | **62.3%** | **97.0%** | +34.7 pts |

### 6.7 M1 — batch-pacing fix (`MAX_BATCH_DELAY_MS`)

n=50, 20,000 offered, 500-tx:

| | tx/block | TPS | cons | E2E | rounds/s |
|---|---|---|---|---|---|
| disabled | 500 | 19,175 | 2,490.7 ms | 2,693.9 ms | 0.8 |
| cap 500 ms | 200 | 19,670 | 1,010.5 ms | **1,175.7 ms** | 2.0 |

Local verification (n=7, loopback, 1,000 tx/s): disabled 300 tx/block,
3,932.1 ms E2E, 950 TPS → cap 500 ms, 71 tx/block, **950.0 ms**, 962 TPS.
Cap 5000 ms: not engaged, identical to disabled.

---

### 6.8 — 15 October runs (T3, clean cluster)

Eleven runs. All on the 50-machine cluster, 1 node per machine, 500-tx
batches, `MAX_BATCH_DELAY_MS` disabled unless stated.

**APRBC n=30 ceiling — now fully bracketed. Ceiling ~112k, hard capacity ~109k.**

| input | TPS | eta | cons | E2E | rounds/s | peak RSS | batches cached |
|---|---|---|---|---|---|---|---|
| 100,000 | 99,192 | 99.2% | 303.8 ms | 417.4 ms | 6.6 | 219 MB | 97 |
| 110,000 | 106,433 | 96.8% | — | 552.5 ms | — | 552 MB | 302 |
| 115,000 | 108,142 | **94.0%** | 282.8 ms | 815.5 ms | 7.2 | 720 MB | 649 |
| 120,000 | 109,167 | 91.0% | 282.2 ms | 1,194.0 ms | 7.3 | 908 MB | 921 |

Delivered throughput flattens (106k → 108k → 109k) while queues grow
monotonically — a hard capacity ceiling, not a soft threshold. The 110,000
row is the one pre-existing point; the other three are new.

**Governing model check at n=30** (it had none before): 7.3 rounds/s x 500 x
30 = **109,500 predicted** vs **109,167 measured** — 0.3%.

**n=10 post-cleanup verification — both protocols reproduce.**

| | pre-cleanup | 15 Oct | delta |
|---|---|---|---|
| APRBC n=10 @100k | 131–132 ms, eta 99.8% | 99,842 TPS, eta 99.8%, cons 96.0 ms, **E2E 131.4 ms**, 20.0 rounds/s | exact |
| Narwhal n=10 @250k | 243,467, cons 823 ms, E2E 3,043 ms | **241,077**, eta 96.4%, cons 926 ms, **E2E 3,328 ms** | TPS −1.0%, E2E +9% |

APRBC n=10 detail: payload-lag 3,448, network recoveries **0**, batches
cached 22, peak RSS 52 MB, dissemination 1,330.9 Mbps, machine CPU 17.6%.

**Sailfish-inline on T3 — first clean-hardware data for this protocol.**

Ceiling probe:

| n | input | TPS | eta | cons | rounds/s | network TX | machine CPU | peak RSS |
|---|---|---|---|---|---|---|---|---|
| 10 | 90,000 | 85,842 | 95.4% | 97.3 ms | 17.2 | 6,679 Mbps | 60.8% | 86 MB |
| 20 | 40,000 | 41,142 | 102.9% | 433.9 ms | 4.1 | 6,630 Mbps | 54.3% | 230 MB |
| 30 | 30,000 | 1,925 | 6.4% | 534.3 ms | 0.1 | 592 Mbps | 5.0% | 238 MB |
| 50 | 20,000 | 15,608 | 78.0% | 4,369.5 ms | 0.8 | 5,595 Mbps | 43.5% | 644 MB |

> **The n=30 @ 30,000 row is an invalid run — do not use it.** Nine ordered
> rounds in 60 s at one tenth the network and one tenth the CPU of its
> neighbours, and a *larger* committee (n=50) did eight times better. A
> stall, not a measurement. Superseded by the 20,000 row below.

Matched-load curve at 20,000 tx/s:

| n | TPS | eta | cons latency | rounds/s | network TX | machine CPU | peak RSS |
|---|---|---|---|---|---|---|---|
| 10 | 20,600 | 103% | 445.0 ms | 4.1 | 1,600 Mbps | 13.3% | 118 MB |
| 20 | 20,458 | 102% | 926.5 ms | 2.1 | 3,324 Mbps | 25.0% | 264 MB |
| 30 | 20,258 | 101% | 1,357.8 ms | 1.4 | 4,907 Mbps | 38.9% | 476 MB |
| 50 | 15,608 | 78% | 4,369.5 ms | 0.8 | 5,595 Mbps | 43.5% | 644 MB |

### 6.8b Three findings from the 15 October runs

**1. The 20,000 tx/s curve is pacing-limited, not capacity-limited.**
Measured round rate matches the generator's batch-formation rate
`500 x n / rate` at every committee size:

| n | measured rounds/s | pacing limit |
|---|---|---|
| 10 | 4.1 | 4.0 |
| 20 | 2.1 | 2.0 |
| 30 | 1.4 | 1.33 |
| 50 | 0.8 | 0.8 |

Delivered throughput confirms it — 103% / 102% / 101% at n=10/20/30. Only
n=50 (78%) hit a genuine limit. **Consequence: a fixed-20k round-rate
comparison between the two protocols measures the transaction generator, not
either protocol.** This is also a fifth validation of the pacing model, on a
second and independent protocol.

The protocol-controlled part is latency *above* the collection window:

| n | window | inline latency | overhead above window |
|---|---|---|---|
| 10 | 250 ms | 445 ms | 195 ms |
| 20 | 500 ms | 927 ms | 427 ms |
| 30 | 750 ms | 1,358 ms | 608 ms |
| 50 | 1,250 ms | 4,370 ms | **3,120 ms** |

Against APRBC at n=50 / 20k with the cap engaged (200-tx batches, 500 ms
window, 1,010.5 ms consensus): overhead **510 ms**, at 19,670 TPS. So at
n=50, APRBC's overhead is **~6x lower** at **1.26x** the throughput.

**2. Sailfish-inline does NOT deadlock at n=50 on clean hardware.** It ran at
0.8 rounds/s and delivered 78% of a 20,000 tx/s offered load. The deadlock
recorded on the 10-machine testbed (A2) was substantially the 5-nodes-per-
machine packing, not the protocol. **The motivation claim must be softened
accordingly** — the wall is real but milder than the contended data implied.

**3. The inline wall is network, not CPU.** Per-node TX scales linearly with
committee size — roughly 160 Mbps per member at 20k (1,600 / 3,324 / 4,907
Mbps at n=10/20/30). Extrapolating, n=50 needs ~8 Gbps to keep up; it
delivered 5,595 Mbps and fell to 78% throughput, with machine CPU at only
43.5%.

**Still unknown:** Sailfish-inline ceilings at n=20 (>40k), n=30 (>20k) and
n=50 (~15k). Deprioritised — see §9.

## 7. Conflicts and suspect values — resolved

Decisions taken 15 October. Each item states the resolution to apply when
writing, not just the problem.

**1. A2 and A3 give different numbers for the same T2 cells.**
*Not* disagreeing measurements — different ceiling criteria at different
input rates (A2 n=20 at a 120k ceiling, A3 at 135k). Where they share an
input rate they agree to 0.8% (n=10 @140k) and 0.02% (n=30 @90k).
**Resolution: A2 is the single source for all protocol comparisons; A3 is
used only for resource use (§5.3) and amplification (§5.4).** Do not average
them — the mean would correspond to no run at any input rate.

**2. A3 contradicts itself.** Its main table gives APRBC n=20 as 154.7 ms
consensus / 441.6 ms E2E; its latency section gives 195.6 / 245.7 ms for the
same cell. Narwhal n=50 likewise: 1,141/2,166 vs 1,063/1,739. Never
reconciled on the page. **Resolution: follows from #1 — take both cells from
A2, cite no latency figure from A3.**

**3. APRBC n=50 on T2 is bistable** — 63,467 once in seven attempts, the
other six 21,925–57,250. **Resolution: report as an environment limitation,
not a protocol property.** Ten machines running five nodes each could not
sustain a 50-node committee reproducibly; that is the finding, and it is what
motivated moving to 50 physical machines. See #4.

**4. All T1 and T2 n=50 figures are dropped.** Both protocols, all variants.
The 10-machine testbed at five nodes per machine produced bistable throughput
(#3), a baseline reporting eta > 1 in five of eleven runs, and deadlocks
across several configurations (#15). **Resolution: comparisons A, B and C
cover n=10/20/30 only, with a short statement that n=50 exceeded what that
testbed could support — which is the justification for the 50-machine
cluster and for comparison D.** n=50 results come from T3 exclusively.

**5. Two "30-node" runs on T2 were actually 20-node runs** (`setup_cluster`
not re-run). Invalidates the 59,467 TPS figure and the Change-3 n=30
comparison. Source: A1, testbed T2. **Resolution: do not estimate the missing
row.** Change 3 measured −1.7% at n=20 and 0% at n=50, both inside noise; the
"no measurable effect" conclusion already stands on two valid points.

**6. Narwhal n=20 @260k on T3 read eta 62.3%** — stale processes.
**Resolution: resolved by re-test, 1 Oct, eta 97.0%.** Only the points re-run
on 1 and 15 October are cited.

**7. Historical Narwhal n=50 data used `--max-batch-delay 50`**, forcing
~75-tx batches and pinning eta at ~85% by configuration. **Resolution: not
usable as a ceiling measurement, but kept as evidence of batch-delay
sensitivity** — it shows Narwhal also degrades under small batches (85%)
where PRBC collapses harder (3.5%) at the same setting. Cite it for that
comparison only; ceilings come from the delay-400 sweep.

**8. Narwhal variance is large where measured** — 43% at n=10 @100k, 51% at
n=50 @175k, and 983 vs 1,125 ms at n=50 @55k. Most cells are single runs.
**Resolution: deferred.** Select the results to report first, then repeat
only those that carry weight.

**9. PRBC's ceiling differs between testbeds — two effects pulling opposite
ways, state both.**

*Hardware, visible at n=10.* Both testbeds run one node per machine at n=10,
so density is ruled out. The ceiling still **fell ~11%**, from ~136–138k on
T2 to ~120–125k on T3. The only variable is the machine type: T2 used
`n2d-highcpu-8`, T3 uses `n2` at 8 vCPU. T3's machines are measurably slower
for this workload.

*Density, dominant at n >= 20.* T2 packs 2/3/5 nodes per machine where T3
uses one. This outweighs the hardware penalty: T3's n=20 ceiling is ~120k
against T2's ~80k — **50% better on slightly weaker machines**, because a
node with a whole machine beats two sharing one.

**Resolution: attribute the n=10 drop to the n2d → n2 change and the n >= 20
rise to density; say that the two effects oppose each other, and never put
figures from the two testbeds in one table.**

**10. ~~n=30 T3 sweep never transcribed.~~ RESOLVED 15 Oct** — full bracket
re-run and recorded (§6.8). Ceiling ~112k, hard capacity ~109k.

**11. The 9,456 ms at 1,000 tx/s** is the batch-pacing artefact, confirmed
and since fixed. **Resolution: every table containing it predates the fix and
must be re-run or labelled as such.** See §9.

**12. T2 n=30 peak figures are mutually inconsistent and are replaced.**
A1 records 60,000 → 59,425 TPS and 65,000 → 43,625 TPS marked "OVER, TPS
drops", yet also claims 63,217 TPS at both 600k and 700k input. 65k
collapsing while 700k succeeds cannot both be true, and two further runs at
this committee size were mislabelled 30-node (#5). **Resolution: replaced
wholesale by the T3 n=30 data in §6.8** — a fully bracketed sweep
(100k/110k/115k/120k), ceiling ~112k, hard capacity ~109k, with the
governing model matching to 0.3%. No T2 n=30 peak figure is cited.

**13. Sailfish-inline n=30 @30,000 on T3 (15 Oct) is an invalid run** — 9
rounds in 60 s, eta 6.4%, at one tenth the network and CPU of its
neighbours; the protocol stalled. **Resolution: do not cite. Superseded by
the 20,000 point.**

**14. eta exceeded 100%** at n=10/20/30 in the 20,000 matched-load runs
(101–103%), and in A3's Narwhal n=50 data (up to 1.051). A measurement-window
edge effect that recurs across both harnesses. **Resolution: one sentence in
the methodology section; harmless at this magnitude.**

**15. The A2 n=50 inline deadlock does not reproduce on clean hardware** —
T3 gives 0.8 rounds/s at 78% delivery. **Resolution: the 10-machine testbed
deadlocked across several configurations and protocols; this is a property of
that testbed, not of the protocol. Scope every deadlock claim to T2
explicitly.** Follows from #4.

## 8. Coverage against the four planned comparisons

### Comparison A — PRBC-orig vs our Sailfish, 10 machines (n=10/20/30)

| n | PRBC-orig | Sailfish-inline | status |
|---|---|---|---|
| 10 | ✅ A2 146,500 / ~69 ms | ✅ A2 92,825 / 90.2 ms | complete |
| 20 | ✅ A2 79,667 / ~256 ms | ✅ A2 19,458 / 907 ms | complete |
| 30 | ✅ A2 69,475 / ~442 ms | ✅ A2 13,100 / 1,943 ms | complete |
| 50 | ❌ dropped (§7.4) | ❌ dropped (§7.4) | testbed could not support it |

**Status: complete at n=10/20/30**, 3 runs per cell, single source (A2).

**Caveat, and a partial clean-hardware check (15 Oct).** Density rises
1/2/3/5 nodes per machine across these rows and inline Sailfish is
bandwidth-bound, so the widening gap is amplified by contention. §6.8 now
provides clean-hardware inline data at a matched 20,000 tx/s load across all
four committee sizes, which supports the direction but shows the collapse is
**milder** than the T2 rows suggest — notably, n=50 does not deadlock. Use
T2 for comparison A as planned, and cite §6.8 as the check that the effect
is not purely a packing artifact.

### Comparison B — PRBC-orig and Sailfish vs Narwhal, 10 machines (n=10/20/30)

| n | PRBC-orig | Sailfish-inline | Narwhal | status |
|---|---|---|---|---|
| 10 | ✅ | ✅ | ✅ 192,400 / ~706 ms | complete |
| 20 | ✅ | ✅ | ✅ 167,631 / ~1,070 ms | complete |
| 30 | ✅ | ✅ | ✅ 123,200 / ~1,500 ms | complete |
| 50 | ❌ dropped (§7.4) | ❌ dropped (§7.4) | ❌ dropped (§7.4) | testbed could not support it |

**Status: complete at n=10/20/30** from A2 (§7.1). Folds into comparison C
as the "before" state rather than standing as its own section.

### Comparison C — APRBC vs Narwhal, 10 machines (n=10/20/30)

| n | APRBC | Narwhal | status |
|---|---|---|---|
| 10 | ✅ A2 136,900 / 71.3 ms | ✅ A2 192,400 / ~706 ms | A2 only (§7.1) |
| 20 | ✅ A2 119,317 / 165.9 ms | ✅ A2 167,631 / ~1,070 ms | A2 only (§7.1, §7.2) |
| 30 | ✅ A2 89,508 / 330.7 ms | ✅ A2 123,200 / ~1,500 ms | A2 only; A3 agrees to 0.02% |
| 50 | ❌ dropped (§7.4) | ❌ dropped (§7.4) | testbed could not support it |

**Status: complete at n=10/20/30** using A2 as the single source (§7.1).
n=50 is dropped and replaced by one paragraph on the testbed limit (§7.3,
§7.4), which is what motivates comparison D.

### Comparison D — APRBC vs Narwhal, 50 machines

| n | APRBC | Narwhal | status |
|---|---|---|---|
| 10 | ✅ sweep + **15 Oct verify** | ✅ sweep + **15 Oct verify** | complete and confirmed |
| 20 | ✅ sweep + 1 Oct | ✅ sweep + 1 Oct | complete and confirmed |
| 30 | ✅ **full bracket, 15 Oct** | ✅ sweep + 1 Oct | complete and confirmed |
| 50 | ✅ full sweep + batch sweep | ✅ delay-400 sweep | complete |

**Status: complete.** Every committee size now has both protocols measured
or verified on a cluster confirmed free of stale processes. This is the
dataset the evaluation chapter should be built on.

### Not covered by any of the four

- **T1 (single machine)** data — A1's n=10/20. Probably drop.
- **WAN** (A4) — you removed it from the thesis context; data exists if wanted.
- **Optimization studies** (Tier 1 / Tier 2 / Change 3) — a separate story
  about *why* APRBC looks as it does; not in any of the four comparisons.
- **Quorum experiment**, **recovery validation**, **`PRBC_SAMPLE_C` sweep**,
  **objective 4 budget framing**, **amplification**, **bandwidth per tx**,
  **resource/CPU** — all exist, none assigned to a comparison.

---

## 9. What is left to run

Updated 15 October, after eleven runs closed most of the earlier list.

### Done

- ~~n=30 APRBC sweep on T3~~ — complete, ceiling ~112k (§6.8).
- ~~n=10 on T3 post-cleanup, both protocols~~ — both reproduce (§6.8).
- ~~Sailfish-inline on clean hardware~~ — matched-load curve across all four
  committee sizes (§6.8).

### Still outstanding — one item that matters

**The 1,000–20,000 tx/s workload sweep with `MAX_BATCH_DELAY_MS` enabled.**
Five rates per protocol. This is the supervisor's literal stated experiment
and the table currently on record rests on the 9,456 ms pacing artefact that
has since been fixed. Higher priority than any remaining scaling run.

### Deliberately not running

- **C's n=50 (10-machine).** The bistability and the baseline's eta > 1 are
  the *result* — that testbed running out of capacity at 5 nodes per machine
  is what motivates the move to 50 machines. Report it, don't re-run it.
- **Sailfish-inline ceilings at n=20/30/50 on T3.** Would give a
  ceiling-vs-ceiling version of comparison A on clean hardware, but
  comparison A is deliberately scoped to the 10-machine environment and
  §6.8 already provides the sanity check. Diminishing returns.
- **Anything on the single-machine testbed (T1).** Superseded.
- **PRBC-orig rebuilt for T3.** Would isolate the broadcast primitive on
  clean hardware, but needs an old commit built and deployed to 50 machines.
  Only worth it if the isolation argument becomes central to chapter 4.

---

## 10. The four comparisons — selected results

Final cell selection, following the resolutions in §7. Every figure is
traceable to a source in §3. **Cells marked ⚠ are the weak ones** — usable,
but the first thing a reader will probe.

### Comparison A — does probabilistic broadcast beat reliable broadcast?

Testbed **T2** (10 machines), n = 10/20/30, each protocol at its own ceiling.
Both carry payload inline, both use Sailfish ordering — **the broadcast
primitive is the only difference**. Source: A2 throughout, 3 runs per cell.

| n | PRBC-orig TPS | cons. latency | Sailfish-inline TPS | cons. latency | TPS gain | latency gain |
|---|---|---|---|---|---|---|
| 10 | 146,500 | ~69 ms | 92,825 | 90.2 ms | **1.58×** | 1.31× |
| 20 | 79,667 | ~256 ms | 19,458 | 907 ms | **4.09×** | 3.54× |
| 30 | 69,475 | ~442 ms | 13,100 | 1,943 ms | **5.30×** | 4.40× |

Round rate, inline only: 18.6 → 2.1 → 0.9 /s.
Input rates: PRBC-orig unlimited / 80k / 70k; inline 90k / 20k / 14k.

**What it shows:** the advantage grows monotonically with committee size,
which is the direction the complexity argument predicts (RBC forwards n²
payload copies, PRBC forwards s² ≈ C²n).

⚠ Density rises 1 → 2 → 3 nodes per machine across these rows, and inline
Sailfish is bandwidth-bound, so part of the widening is contention. The
clean-hardware check is §6.8: the effect holds but is milder.

### Comparison B — where both sit against Narwhal

Same testbed, same rows, Narwhal added. Source: A2.

| n | PRBC-orig | Sailfish-inline | Narwhal | Narwhal TPS vs PRBC-orig | PRBC-orig latency vs Narwhal |
|---|---|---|---|---|---|
| 10 | 146,500 / ~69 ms | 92,825 / 90.2 ms | 192,400 / ~706 ms | 1.31× higher | **10.2× lower** |
| 20 | 79,667 / ~256 ms | 19,458 / 907 ms | 167,631 / ~1,070 ms | 2.10× higher | **4.18× lower** |
| 30 | 69,475 / ~442 ms | 13,100 / 1,943 ms | 123,200 / ~1,500 ms | 1.77× higher | **3.39× lower** |

Narwhal E2E on the same rows: ~3,800 / ~3,050 / ~3,400 ms.

**What it shows:** Narwhal leads throughput at every size; PRBC-orig leads
latency by 3.4–10×. This is the trade-off before the architecture change.

### Comparison C — what the architecture change bought

Same testbed. APRBC replaces PRBC-orig. Source: A2 only (§7.1).

| n | APRBC TPS | cons. | E2E | Narwhal TPS | cons. | E2E | TPS gap | cons. gap | E2E gap |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 136,900 | 71.3 ms | 163 ms | 192,400 | ~706 ms | ~3,800 ms | 1.41× N | **9.9× A** | **23.3× A** |
| 20 | 119,317 | 165.9 ms | 228 ms | 167,631 | ~1,070 ms | ~3,050 ms | 1.40× N | **6.5× A** | **13.4× A** |
| 30 | 89,508 | 330.7 ms | 423 ms | 123,200 | ~1,500 ms | ~3,400 ms | 1.38× N | **4.5× A** | **8.0× A** |

Against PRBC-orig on the identical testbed — the before/after that isolates
the change:

| n | TPS | cons. latency |
|---|---|---|
| 10 | −6.6% | +3.3% (slightly worse) |
| 20 | **+49.8%** | **−35.2%** |
| 30 | **+28.8%** | **−25.2%** |

**What it shows:** the change costs a little at n=10 and pays increasingly
from n=20 up. Narwhal's throughput lead narrows to a flat ~1.4× at every
size, while APRBC's latency lead stays 4.5–9.9× on consensus and 8–23× E2E.

### The n=50 gap — the bridge to comparison D

n=50 is absent from A, B and C by decision (§7.3, §7.4). At five nodes per
machine the 10-machine testbed could not sustain a 50-node committee:
APRBC was bistable (63,467 once in seven attempts, the rest 21,925–57,250),
Narwhal reported η > 1 in five of eleven runs, and inline Sailfish
deadlocked at every rate. **This is the limit of that environment and the
reason for the 50-machine cluster.** It is a finding, not a missing cell.

### Comparison D — APRBC vs Narwhal on 50 machines

Testbed **T3**, one node per machine at every size. All cells measured or
re-verified on a cluster confirmed free of stale processes.

**D1 — ceilings, matched 500-tx batches**

| n | APRBC | Narwhal |
|---|---|---|
| 10 | ~120–125k | ~275k |
| 20 | ~120–125k | ~250–255k |
| 30 | **~112k** (hard capacity 109k) | ~250–260k |
| 50 | ~75k | ≥200k (delay 400) |

**D2 — ceilings with each protocol tuned**

| n | APRBC (n_tx) | Narwhal | APRBC as % |
|---|---|---|---|
| 10 | ~248k (4,000) | ~275k | 90% |
| 20 | ≥225k (2,000) | ~250k | ≥90% |
| 30 | ≥200k (2,000) | ~250k | ≥80% |
| 50 | ~150k (2,000) | ≥200k | ≤75% |

**D3 — matched configuration, 500-tx batches both sides (the headline)**

Source: M1 §6.4 matched-settings curve, with n=10 and n=20 re-verified.
Adjustment adds **half the collection window** (`n_tx x n / rate / 2`) to
PRBC's E2E, so both figures span client-arrival to commit. Narwhal is
unmodified.

| n | rate | window | PRBC measured | PRBC adjusted | Narwhal E2E | ratio (adjusted) |
|---|---|---|---|---|---|---|
| 10 | 100k | 50 ms | 131.4 ms ✓15 Oct | **156.4 ms** | ⚠ 4,054 / 5,789 ms | 25.9–37.0× |
| 20 | 120k | 83 ms | 393.7 ms ✓1 Oct | **435.4 ms** | 3,488 ms ✓1 Oct | **8.0×** |
| 30 | 110k | 136 ms | 552.5 ms | **620.7 ms** | 3,904 ms | **6.3×** |
| 50 | 75k | 333 ms | 903.2 ms | **1,069.9 ms** | 5,043 ms | **4.7×** |

At n=20/120k delivered throughput differs by **24 tx/s (0.02%)** — 116,508
vs 116,484, both at η 97.1%. The cleanest single comparison on record.

⚠ The n=10 Narwhal cell predates the cleanup; its two runs differ by 43%.

**D3b — consensus latency, the independent cross-check**

Both protocols define this as "proposal object formed → committed", which is
genuinely analogous. It favours Narwhal, and reporting it is what makes the
E2E claim credible.

| n | rate | PRBC cons. | Narwhal cons. | favours |
|---|---|---|---|---|
| 20 | 120k | 171.6 ms | 1,146 ms | PRBC 6.7× |
| 20 | 260k | 338.1 ms | 358 ms | **tie** |
| 30 | 230k | 552.0 ms | 355 ms | **Narwhal 1.6×** |
| 30 | 260k | — | 436 ms | — |

**Why both metrics belong in the thesis.** They disagree, and the
disagreement is the finding: Narwhal's ordering is competitive — sometimes
better — while its end-to-end delivery is 4.7–8× slower. That localises the
entire difference to pre-consensus cost (D5), which is the delivery-ack
quorum. A reader who distrusts either metric is led to the same mechanism by
the other.

**D4 — each protocol at its own best setting**

| n | rate | APRBC | Narwhal | winner |
|---|---|---|---|---|
| 10 | 200k | 277.9 ms | 4,381 ms | APRBC 15.8× |
| 10 | 250k | 465.8 ms | 3,043 ms | APRBC 6.5× |
| 20 | 120k | 394 ms (500 tx) | 3,169 ms (50 ms) | APRBC 8.05× |
| 20 | 260k | 911 ms (2,000 tx) | 2,611 ms (50 ms) | APRBC 2.87× |
| 30 | 230k | 803 ms (2,000 tx) | 1,657 ms (50 ms) | APRBC 2.06× |
| 50 | 75k | 906 ms (500 tx) | 5,043 ms (400 ms) | APRBC 5.6× |
| 50 | 150k | 1,796 ms (2,000 tx) | 848 ms (400 ms) | **Narwhal 2.1×** |
| 50 | 200k | 2,774 ms (4,000 tx) | 1,145 ms (400 ms) | **Narwhal 2.4×** |

**D5 — where the latency difference sits** (consensus vs pre-consensus)

| | n | rate | cons. | E2E | pre-consensus |
|---|---|---|---|---|---|
| APRBC | 20 | 120k | 171.6 | 393.7 | **222 ms** |
| APRBC | 30 | 230k | 552.0 | 802.5 | **250 ms** |
| APRBC | 20 | 260k | 338.1 | 911.2 | **573 ms** |
| Narwhal | 20 | 120k | 1,146 | 3,488 | **2,342 ms** |
| Narwhal | 20 | 260k | 358 | 2,611 | **2,253 ms** |
| Narwhal | 30 | 230k | 355 | 1,657 | **1,302 ms** |
| Narwhal | 30 | 260k | 436 | 1,681 | **1,245 ms** |

Narwhal's *consensus* latency is competitive and sometimes lower. The whole
difference is pre-consensus — the delivery-ack quorum.

**What D shows:** throughput parity within 10–25% once both are tuned; APRBC
leads latency at n=10/20/30 by 2.1–44×; the ordering reverses at n=50 above
roughly 125k.

### Weak cells, in one place

| cell | why | fix |
|---|---|---|
| D3 n=10 Narwhal | pre-cleanup, 43% spread between two runs | one re-run at 100k |
| D4 n=50 @75k Narwhal | 5,043 ms sits on the untuned 5,000 ms header delay | one run with a lower header delay |
| D2 n=20/30 APRBC | lower bounds — still demand-driven, not saturated | push rate until η drops |
| A, all rows | density confound | §6.8 is the check; no fix planned |

---

## 11. 20 October — Narwhal tuning campaign (T3)

All runs on the 50-machine cluster, one node per machine, 512 B transactions,
60 s. Every Narwhal latency measured before this date used its default header
settings and is superseded for latency purposes (throughput unaffected).

### 11.1 Diagnosis at n=50, 75,000 tx/s, delay 400 ms

Stage split from Narwhal's own logs (`~/trace_narwhal.py`, means):

| config | fill | sealed to header | header to commit | E2E | E2E p90 | header interval | digests/header | delivered |
|---|---|---|---|---|---|---|---|---|
| default (run 1) | 168 | 1,876 | 2,476 | 4,520 | 8,937 | — | — | 91.4% |
| default (run 2) | 168 | 1,888 | 2,584 | 4,639 | 8,693 | 1,944 ms | 5.91 | 91.1% |
| header 30 B | 168 | 1,446 | 1,924 | 3,537 | 9,433 | 697 ms | 2.09 | 98.9% |
| header 30 B + delay 1 s | 168 | 230 | 765 | 1,163 | 1,808 | 501 ms | 1.52 | 97.8% |

Default at 150k for reference: fill 86, sealed to header 473, header to commit
722, E2E 1,281, header interval 389 ms, 2.35 digests/header, 99.1% delivered.

Tuned at 150k: E2E 599 ms but **92.8% delivered** — below threshold, invalid.
Tuning costs Narwhal throughput at high load.

n=10, 100k, delay 200, default (17 Oct): fill 22, sealed to header 2,455,
header to commit 1,401, E2E 3,879 ms.

### 11.2 Fixed 100,000 tx/s, best configuration each

| n | ours | Narwhal tuned | Narwhal default |
|---|---|---|---|
| 10 | 131.4 ms (500 tx) | 789 ms | 3,877 ms |
| 20 | 265.2 ms (500 tx) | 627 ms | — |
| 30 | 417.4 ms (500 tx) | 806 ms | — |
| 50 | 1,310.2 ms (1,000 tx) | 888 ms | 3,735 ms |

Ours at n=50 / 100k / 1,000-tx is a new run (20 Oct): 98,350 tx/s, consensus
1,013.9 ms, E2E 1,310.2 ms, 2.0 rounds/s. Amplification 147.4 against 139
predicted (ratio 1.06), closing the missing n=50 point.

### 11.3 Matched points re-run against tuned Narwhal

| n | rate | ours | Narwhal tuned | Narwhal default (before) |
|---|---|---|---|---|
| 10 | 100k | 131.4 ms | 789 ms | 3,877 ms |
| 20 | 120k | 393.7 ms | 572 ms | 3,488 ms |
| 30 | 110k | 552.5 ms | 712 ms | 3,904 ms |
| 50 | 75k | 903.2 ms | 1,159 ms | 4,637–5,043 ms |

### 11.4 Conclusions withdrawn by this campaign

- All latency ratios against default-configuration Narwhal (matched headline
  21.4× / 7.3× / 5.7× / 4.1×; comparisons B and C; each-at-best rows).
- Narwhal's latency dominated by its delivery-acknowledgement wait — it was
  header-formation waiting under the defaults.
- The fixed-latency-budget comparison (4.6–7×).
- Narwhal's load-dependence as an open anomaly — resolved as a configuration
  effect.

---

## 12. 21 October — ceiling table corrected from the run record

Re-read every pasted run output. Highest passing run (η ≥ 95%) per cell, T3:

| n | APRBC best batch | cons / E2E | Narwhal (default header) | cons / E2E |
|---|---|---|---|---|
| 10 | 248,000 @250k, 4,000 tx (300k: 79.6%) | 313.1 / 465.8 ms | 243,467 @250k (275k: 94.7%) | 823 / 3,043 ms |
| 20 | 250,567 @260k, 2,000 tx (higher untried) | 338.1 / 911.2 ms | 252,146 @260k clean (higher untried) | 358 / 2,611 ms |
| 30 | 227,033 @230k, 2,000 tx (higher untried) | 552.0 / 802.5 ms | 241,016 @252k (clean: 231k 94.3%, 261k 93.2%) | 475 / 2,041 ms |
| 50 | 193,400 @200k, 4,000 tx (higher untried) | 2,001.3 / 2,774.1 ms | 194,695 @200k, delay 400 (higher untried) | 611 / 1,145 ms |

Also n=50 4,000 tx @175k: 166,733 (95.3%), E2E 3,052.1 ms. The old D2 table
(~248k / ≥225k / ≥200k / ~150k vs ~275k / ~250k / ~250k / ≥200k) missed the
three APRBC runs above and used offered-rate estimates for Narwhal.
`EVALUATION_RESULTS.md` §8.1, §14, §15 and the ceilings artifact updated.

### 12.1 Tuned Narwhal at the ceiling rates (21 October)

`--header-size 30 --max-header-delay 1000`, batch 256,000 B, delay 50 ms, same rates as the default-settings ceiling runs:

| n | offered | cons TPS | η | cons | E2E | exec time | verdict |
|---|---|---|---|---|---|---|---|
| 10 | 250k | 241,800 | 96.7% over 20 s | 65 ms | 507 ms | **20 s** | invalid — commits span only 20 s of 60; rerun |
| 20 | 260k | 245,667 | **94.5%** | 149 ms | 463 ms | 62 s | below threshold by 0.5 pt; default gave 96.9% |
| 30 | 252k | 215,551 | **85.5%** | 290 ms | 421 ms | 62 s | fails; default gave 95.5% |

Tuning costs Narwhal throughput at n=20/30 high load, as at n=50/150k, but buys ~5× lower latency for 3–11% less delivered throughput. Ours at the same points: n=20 911.2–1,065.0 ms, n=30 802.5–1,063.4 ms.

## 13. 22 October — latency comparison method changed

Supervisors questioned the "+ full window" upper bound on our latency. Replaced: nothing is added to ours; Narwhal's batch-fill wait is subtracted from its E2E, so both run from batch ready. Fill = measured where traced, else `min(500 × n / rate, max_batch_delay) / 2` (matched the log at 22/25, 168/167, 86/83 ms). Headline at 100k: 131.4 vs 767 (5.8×), 265.2 vs 577 (2.2×), 417.4 vs 731 (1.8×), 1,310.2 vs 763 (Narwhal 1.7×). `EVALUATION_RESULTS.md` §3, §8.1, §8.3–8.6, §14, §15 and the headline artifact updated.

## 14. 22 October — what limits our round rate at n=50 (T3, 100k, 550-tx batches)

Target: ~275 ms rounds (3.6 rounds/s), the batch size that would beat tuned Narwhal's 763 ms from batch ready.

| run | TPS | η | rounds/s | cons | E2E | batches cached | verdict |
|---|---|---|---|---|---|---|---|
| 512 B, C 1.4 (current) | 24,970 | 25.0% | 0.9 | 575.0 | 778.2 | 8,021 | collapsed |
| 512 B, C 1.0 (s=8) | 49,436 | 49.4% | 1.8 | 653.8 | 1,389.8 | 5,520 | collapsed |
| 256 B, C 1.4 | 76,817 | 76.8% | 2.8 | 577.3 | 795.2 | 2,519 | fails |
| 256 B, C 1.0 | 70,913 | 70.9% | 2.6 | 571.7 | 768.6 | 3,180 | fails |
| 512 B, C 1.4, **vote sigs off** | 99,009 | **99.0%** | **3.6** | 550.6 | **694.0** | 116 | passes |

Only turning off vote-signature verification sustains the load; halving payload bytes or shrinking the sample helps but does not. Signature verification (every replica checks every vote, 2,500 Ed25519 checks per round at n=50, sequentially in the consensus loop, `prbc_sailfish.rs:1279-1284`) is the main limit on our round rate at n=50. Sigs off is a diagnostic, not a valid configuration. Failed runs collapse into a backlog, so their η does not measure distance from passing.

## 15. 22 October — vote signatures checked on reader tasks (commit 8aa66b4)

Build change only: vote signatures verified on each peer's reader task instead of in the consensus loop. Protocol unchanged. Outputs labelled `vote sigs: on, checked on readers`. T3, 100k tx/s, 512 B.

| n | batch | TPS | rounds/s | cons | E2E | before (old build) |
|---|---|---|---|---|---|---|
| 10 | 500 | 99,842 | 20.0 | 95.2 | 127.2 ms | 131.4 ms |
| 20 | 500 | 99,675 | 10.0 | 196.2 | 252.4 ms | 265.2 ms |
| 30 | 500 | 99,508 | 6.7 | 297.9 | 386.0 ms | 417.4 ms |
| 50 | 550 | 99,009 | 3.6 | 548.8 | 705.2 ms | 1,310.2 ms (1,000-tx; 550 collapsed at 25%) |

n=50 matches the sigs-off diagnostic (694.0 ms), so the change recovers nearly all of it.

Narwhal n=50, 100k, tuned (header 30 B, delay 1,000 ms, batch delay 400), traced: consensus 541 ms, E2E 744 ms, 98,945 tx/s. Trace means: client→sealed 123.5 ms (estimate was 125), sealed→header 79.2, header→commit 549.0; header interval 283 ms, 1.14 digests/header. From batch ready: 744 − 123.5 = 620.5 ms (trace sealed→commit 628 ms). The 20 Oct run of the same configuration gave E2E 888 ms (763 from batch ready): run-to-run spread 16%.

n=50 verdict: ours 705.2 ms against Narwhal 621–763 ms across two runs — level within Narwhal's variance.

n=50, 500-tx, 100k, new build: 99,175 tx/s (99.2%), 4.0 rounds/s, consensus 499.1 ms, **E2E 651.2 ms**, batches cached 102, 1 network recovery. Predicted ~640 ms. With this, all four headline points use 500-transaction batches, matching Narwhal's. Against Narwhal from batch ready: 621 ms (22 Oct, fill measured) → Narwhal 1.05× faster; 763 ms (20 Oct, fill estimated) → ours 1.17× faster. Level.

**Presentation decision, 22 October:** all §8.1 maximum-throughput cells are presented as ceilings, without ≥. For the record: bracketed by a failing higher rate are ours at n=10 (300k failed) and Narwhal at n=10 (275k, 94.7%) and n=30 (261k, 93.2%). Not bracketed, so highest passing rate tried: ours at n=20 (260k), n=30 (230k) and n=50 (200k); Narwhal at n=20 (260k) and n=50 (200k).

## 16. 27 October — recovery rewrite, local checks only

**Not for the thesis.** The user is keeping the Google Cloud recovery results;
these one-machine runs only checked that the rewrite did not break anything.
Kept out of the writing pack on purpose.

### 16.1 Do the earlier recovery results still hold?

Yes. Every result above used `Byz1`, which withholds the vertex and never the
batch, and in those runs every responder already held a quorum. The change
does not touch that path, with one exception: a vertex that arrives before its
batch no longer triggers a vertex request. It now waits for the batch, which
removes a few redundant background requests.

Local check on one machine, n=7 (excluded node 6), 20,000 tx/s, 500-tx
batches, `RECOVERY_TIMEOUT_MS=50`. Old = commit `8aa66b4`, new = this change.
Model prediction for n=7: 10.2% of rounds.

Excluded node 6, three runs per build, 320 ordered rounds each:

| run | old build: requests / vertices recovered | new build: requests / vertices recovered |
|---|---|---|
| 1 | 49 / 40 | 31 / 29 |
| 2 | 37 / 34 | 30 / 27 |
| 3 | 37 / 28 | 34 / 32 |
| **mean recovered** | **34.0 (10.6% of rounds)** | **29.3 (9.2% of rounds)** |

The model predicts 32.6 (10.2%). Both builds are within run-to-run noise of
it and of each other. Throughput was 18,617 tx/s and E2E 357–359 ms in every
run of both builds. The new build wastes fewer requests (2–3 per run against
3–9), consistent with it now accepting a slow answer instead of discarding it
and asking the next voter. It also no longer fetches a vertex it already holds
while the batch is in flight, which can only lower its count slightly.

Fault-free, the two builds are indistinguishable: 18,675 vs 18,617 tx/s,
E2E 358.0 vs 358.7 ms. Background requests on the other nodes fall from 0–7
to 0–1 per node, which is the parked-vertex case above.

### 16.2 The new fault modes (local, n=7, same settings)

`Byz3` sends its own batch to only 2f+1 peers (the batch counterpart of
`Byz1`); `Byz4` never answers a vertex or batch request. Both are otherwise
correct.

| fault | run | node 6 was missing | requests | recovered | left pending | node 6 blocks executed (all-node median) |
|---|---|---|---|---|---|---|
| node 0 `Byz3` | 1 | batches | 17 | 17 | 0 | not recorded |
| node 0 `Byz3` | 2 | batches | 18 | 18 | 0 | 2,234 (2,234) |
| node 0 `Byz1`, node 1 `Byz4` | 1 | vertices | 34 | 25 | 0 | not recorded |
| node 0 `Byz3`, node 1 `Byz4` | 1 | batches | 12 | 10 | 0 | not recorded |
| node 0 `Byz3`, node 1 `Byz4` | 2 | batches | 19 | 17 | 0 | 2,234 (2,234) |

Throughput 18,617–18,675 tx/s and E2E 355–358 ms in every run, the same as
fault-free. Requests beyond the number recovered are the ones sent to the
mute node 1, which timed out and moved on.

- **Batch recovery works.** Under `Byz3`, node 6 never received node 0's
  batches directly. Every one it did not get through the S1→S2 relay it
  fetched, and nothing was left pending. Execution TPS equals consensus TPS,
  so every committed vertex was executed. Before 27 October there was no
  path for this: those vertices would have stayed parked.
- **Failover works.** With node 1 mute, node 6's requests that went to node 1
  timed out and moved to the next voter; every recovery still completed.
- **No restarts were needed.** With at most f faulty nodes and a synchronous
  network some correct voter answers in the first pass, so the restart path
  is a backstop for asynchrony. It did not fire in these runs.
- **Retention cost.** `Batches retained` ≈ 50 rounds × 7 batches ≈ 350,
  about 90 MB at 256 KB per batch. At n=50 and 100k tx/s it would be about
  640 MB per node. Not yet measured on the cluster.

## 17. 27 October — correctness fixes, local checks only

Four changes so the code satisfies the correctness argument (not yet
committed or run on the cluster):

1. Vote signatures cover (round, source, hash), not the hash alone.
2. The source signs its vertex; receivers check it before voting.
3. Sailfish leader skipping: a leader that does not point to the previous
   leader carries a no-vote certificate, and the commit rule walks back from
   the latest directly committed leader, skipping leaders with no strong path.
   Before, one crashed node stopped ordering for good.
4. A process votes only when every parent is certified locally, fetches
   missing certificates, and never orders a history with a gap; each history
   is ordered by (round, source).

Local, n=7, 20,000 tx/s, 500-tx batches. Baseline before the change: 18,617
tx/s, E2E 358 ms fault-free.

| run | consensus TPS | E2E ms | ordered rounds | notes |
|---|---|---|---|---|
| fault-free | 18,617 | 355.1 | 320 | 0 skips, 0 parent waits, 0 cert requests |
| node 6 `silent` (before the change) | 208 | — | 5 | ordering stopped at the silent node's first leader round |
| node 6 `silent` | 15,958 | 437.0 | 320 | 45 leaders skipped (320/7); TPS = 6/7 of fault-free |
| node 0 `byz1`, `RECOVERY_TIMEOUT_MS=50`, 3 runs | 18,617–18,675 | 355.2–355.5 | 320–321 | node 6: 36/29/37 requests, 22/21/33 recovered (mean 25.3; 27 Oct build 29.3, old build 34.0) |
| nodes 0, 1 `byz5`, `RECOVERY_TIMEOUT_MS=50` | 18,675 | 359.0 | 321 | node 6 fetched 684 certificates with 684 requests; 55 vertices recovered; all blocks executed |
| node 0 `byz1` + node 5 `silent` | 15,908 | 437.4 | 319 | every node skipped the same 45 leaders; node 6 recovered 27 |
| fault-free, `PRBC_SIGS=off` | 18,617 | 354.4 | — | |

`byz5` (new, test only): `byz1`, and its votes too go to only 2f+1 peers. Two
of them leave node 6 unable to certify their vertices from votes alone, which
is the case certificate fetch exists for.

The Byz1 recovered count is lower on average than both earlier builds, but
the spread (21–33) overlaps both, and requests (how often recovery was
needed) are unchanged. Fault-free throughput is identical.

### 17.1 Cluster confirmation (commit 0bd734f, 50-machine cluster)

100,000 tx/s, 500-tx batches, fault-free, the §8.3 headline settings:

| n | E2E before | E2E now | TPS before | TPS now |
|---|---|---|---|---|
| 10 | 127.2 ms | 126.7 ms | 99,842 | 99,842 |
| 50 | 651.2 ms | 650.2 ms | 99,175 | 99,175 |

Leaders skipped, parent waits, certificate requests and invalid vertices
were 0 at both sizes: the new checks never fired. The headline tables hold
for this build. First cluster measurement of retention memory: peak RSS
852 MB per node at n=50 (2,501 batches retained), 196 MB at n=10.

### 17.2 28 October — quorum changed to n − f

The code used q = 2f + 1 for every n. That is n − f only when n = 3f + 1
(n = 7, 10). At n = 20, 30 and 50 two quorums of 2f + 1 can overlap in
Byzantine parties only, so the protocol tolerated 5, 7 and 15 Byzantine
parties instead of 6, 9 and 16, and waited for 13 / 19 / 33 votes where
Narwhal waits for 14 / 21 / 34. Now q = n − f for every threshold. A second
small fix: a party never votes for a round whose vote record is pruned
(128 rounds behind), so it cannot vote twice for a slot.

Local, n = 8 (q 5 → 6), 20,000 tx/s, 500-tx batches:

| run | consensus TPS | E2E ms | ordered rounds | leaders skipped |
|---|---|---|---|---|
| fault-free | 19,675 | 390.1 | 296 | 0 |
| node 7 `silent` | 17,100 | 445.2 | 294 | 36 |

n = 10 is unaffected (q = 7 either way). The §8.3 points at n = 20, 30 and
50 were measured with the smaller quorum and need rerunning (old: 252.4,
386.0, 651.2 ms E2E).

### 17.3 Cluster rerun with quorum n − f (28 October, 50-machine cluster)

100,000 tx/s, 500-tx batches, fault-free, the §8.3 settings. CONFIG showed
`quorum: n-f = 14 / 21 / 34`.

| n | E2E before (q = 2f+1) | E2E now (q = n − f) | change | TPS before | TPS now | vs Narwhal from batch ready |
|---|---|---|---|---|---|---|
| 20 | 252.4 ms | 255.1 ms | +1.1% | 99,675 | 99,675 | 577 / 255.1 = 2.26× (was 2.29×) |
| 30 | 386.0 ms | 388.8 ms | +0.7% | 99,508 | 99,508 | 731 / 388.8 = 1.88× (was 1.89×) |
| 50 | 651.2 ms | 657.1 ms | +0.9% | 99,175 | 99,175 | Narwhal 1.06× (was 1.05×) |

All new counters 0. Every change is within run-to-run variation (the same
n = 50 configuration gave 650.2 and 651.2 ms on two days). The headline
ratios round to the same values: 2.3×, 1.9×, level. Other n = 20/30/50
results (sweeps, ceilings) were measured with q = 2f + 1 and not rerun; on
this evidence the quorum moves latency by about 1%.

### 17.4 29 October — a process that certified first still votes (local)

The writing agent found that Lemma 4.6 (validity) did not hold: a process
that collected q votes before it could vote delivered and never voted, so
Byzantine voters sending only to it could leave every other correct process
one vote short (n=4: A, B, C correct, D Byzantine; C certifies from A, B, D
before its batch lands; A and B wait at 2 votes forever). Fix: such a
process delivers and still votes once the vote rule holds; recovered
(unsigned) vertices are not voted for. New counter `Votes post-quorum`.

Local, n=7, 20,000 tx/s, gap 2 ms, same session, pre-fix = commit 81af777:

| run | ordered rounds | E2E | TPS | node 6 certificates fetched (requests) |
|---|---|---|---|---|
| fault-free, pre-fix | 12,114 | 12.8 ms | 19,996 | 0 |
| fault-free, fix | 14,714 | 10.6 ms | 19,996 | 0 |
| nodes 0, 1 `byz5`, `RECOVERY_TIMEOUT_MS=50`, pre-fix | 2,917 | 43.4 ms | 19,980 | 9,018 (14,248) |
| nodes 0, 1 `byz5`, `RECOVERY_TIMEOUT_MS=50`, fix | 5,430 | 24.4 ms | 19,965 | 4,880 (11,200) |

Fault-free: no cost (`Votes post-quorum` = `Payload-lag events`, 10,541 per
node). Under `byz5`, node 6 no longer fetches certificates for correct
processes' vertices, only for the two `byz5` processes' own, and the round
rate nearly doubles.

Cluster confirmation, 50-machine cluster, n=50, 100k tx/s, gap 100 ms, the
§18.1 headline settings: E2E **227.4 ms** (headline 226.1, +0.6%), consensus
latency 215.9 ms, TPS 99,558 (99,489), 9.8 rounds/s (9.8), avg batch 203.5 tx
(203.4), machine CPU 52.8% (49.9%), peak RSS 548 MB. `Votes post-quorum`
1,905 per node, about 6% of the 29,400 vertices; cert requests, parent
waits, invalid vertices 0. Within run-to-run variation: the headline tables
stand.

### 17.5 29 October — the quorum and the Byz1 recovery runs

Byz1 sends its vertex to the 2f+1 lowest-ID peers (`lowest_peers`), not to a
quorum, so the relay model is unchanged by q = n − f. The quorum only gates
certification: excluded peers hold 2f+2 votes (recipients + proposer), enough
unless n = 3f+3, where a relay-reached excluded peer must vote too. Model
with q = n − f: 10.2 / 20.1 / **12.2** / 10.2% at n = 7/8/9/10 (12.8% before
at n = 9), 15.6 / 22.2 / 24.0% at n = 20/30/50. Bump ratio 1.85× predicted vs
1.84× observed. The n = 7–10 sweep still describes the protocol.

## 18. 28 October — batches built at proposal time (supervisor's request)

Alysson: "You are artificially making our latency results worse … Make
infinite transactions available and just control how many are added to
batches according to load." Until now a generator made one full batch every
`n_tx × n / rate` and a proposal waited for it, so the round rate equalled the
batch fill rate (20 rounds/s at n=10 and 4 at n=50, at 100k tx/s: exactly
the 50 ms and 250 ms fills).

Now (default): a party builds its batch when it proposes. Transactions are
always available; the batch holds the transactions that arrived at
`INPUT_RATE / n` since the party's last batch, at most `--n-tx`, the rest
carried over. Every batch carries a (source, sequence) tag, so digests never
repeat (empty batches did, which stalled the first version at 1k tx/s). A
batch retired by another vertex's execution still counts as present.
Throughput is now counted from each executed batch's real transaction count.
`BATCH_MODE=paced` restores the old generator.

Local, n=7, `--n-tx 500`:

| run | rounds/s | avg batch | consensus TPS | E2E ms |
|---|---|---|---|---|
| paced (old), 20k | 5.3 | 500 | 18,617 | 355.5 |
| new, 20k | 54.8 | 52 | 19,956 | 54.9 |
| new, 1k | 57.2 | 2.5 | 998 | 52.7 |
| new, 20k, node 6 `silent` | 11.9 | 240 | 17,048 | 179.5 (101 leaders skipped) |

Every PRBC latency result before this section was measured with paced
batches and has to be re-measured on the cluster before it is used.

### 18.1 Cluster, 28 October — what limits rounds once batches no longer pace them

With batches built at proposal time and nothing else limiting the round rate,
rounds ran as fast as the CPU allowed. Each round costs about n² vote-signature
checks per machine whatever the batch size. At n=30, 100k: 49.9 rounds/s,
67-tx batches, E2E 59.2 ms, but CPU 88% (`htop`: all 8 cores ~90%). At n=50
the machines saturated: 67,712 tx/s (68%), ordering behind the DAG, and one
run hung. Two code paths also grew with the length of the run (the
weak-edge search walked back to round 1; the commit walk back was quadratic
in the backlog); both fixed, same results. Before that fix n=30 ran 11.4
rounds/s, 265.6 ms.

Fix: a minimum gap between a party's proposals (`MIN_PROPOSAL_GAP_MS`,
`--min-gap-ms`), and votes for already-certified slots dropped on the reader
tasks without a signature check. Sweep, 100k tx/s, `--n-tx 500`:

| n | gap | rounds/s | avg batch | E2E | CPU (machine) | TPS |
|---|---|---|---|---|---|---|
| 50 | 50 ms | 18.6 | 107 | 133.0 ms | 82.2% | 99,722 |
| 50 | 100 ms | 9.8 | 204 | 227.6 ms | 49.7% | 99,591 |
| 50 | 150 ms | 6.5 | 304 | 333.0 ms | 37.5% | 99,224 |
| 30 | 20 ms | 45.3 | 74 | 56.5 ms | 78.2% | 99,876 |
| 30 | 50 ms | 19.4 | 172 | 114.0 ms | 41.1% | 99,770 |

Rule adopted: gap = n²/25 ms (each machine checks ~25,000 vote signatures/s,
about half its CPU). Headline, 100k tx/s, `--n-tx 500`:

| n | gap | rounds/s | avg batch | E2E | CPU | TPS |
|---|---|---|---|---|---|---|
| 10 | 4 ms | 215.6 | 46.4 | 11.9 ms | 57.8% | 99,975 |
| 20 | 16 ms | 59.1 | 84.6 | 39.2 ms | 54.7% | 99,923 |
| 30 | 36 ms | 26.6 | 125.1 | 84.8 ms | 51.3% | 99,830 |
| 50 | 100 ms | 9.8 | 203.4 | 226.1 ms | 49.9% | 99,489 |

Not yet comparable with Narwhal: its §8.3 figures used a 200 ms batch delay
(400 ms at n=50), which paces its rounds. It needs the same treatment (batch
delay at the same gap, CPU checked) before any ratio is claimed. Maximum
throughput for ours must also be re-measured (batch size now follows load;
`--n-tx` is only a cap).

### 18.2 28 October — maximum throughput (ours) and Narwhal at our pacing

Ours, gap n²/25 ms, `--n-tx 4000` as a cap only (batch size follows load):

| n | offered | delivered | % | rounds/s | avg batch | E2E | CPU |
|---|---|---|---|---|---|---|---|
| 10 | 250k | 249,636 | 99.9% | 48.0 | 520 | 60.1 ms | 39.5% |
| 10 | 300k | 297,787 | 99.3% | 8.1 | 3,700 | 360.0 ms | 35.8% |
| 20 | 260k | 259,154 | 99.7% | 17.0 | 763 | 172.6 ms | 43.8% |
| 20 | 310k | 298,565 | 96.3% | 4.0 | 3,797 | 750.6 ms | 38.8% |
| 30 | 230k | 228,925 | 99.5% | 15.0 | 511 | 198.9 ms | 51.3% |
| 30 | 280k | 277,597 | 99.1% | 6.9 | 1,348 | 434.0 ms | 42.2% |
| 50 | 200k | 198,483 | 99.2% | 8.1 | 490 | 342.4 ms | 57.5% |
| 50 | 240k | interrupted by hand (no result) | | | | | |

All passing rates are above the old ceilings (248,000 / 250,567 / 227,033 /
193,400) and Narwhal's (243,467 / 252,146 / 241,016 / 194,695). Upper bounds
not yet found.

Narwhal, tuned header settings (30 B, 1,000 ms), batch 256,000 B, 100k tx/s,
`--max-batch-delay` set to our gap. From batch ready = E2E − fill, fill =
min(500·n/rate, delay)/2 (§3):

| n | batch delay | delivered | consensus lat. | E2E | from batch ready | clients missed rate |
|---|---|---|---|---|---|---|
| 10 | 4 ms | 97.6% | 44 ms | 484 ms | 482 ms | 93× |
| 20 | 16 ms | 90.3% | 65 ms | 91 ms | 83 ms | 248× |
| 30 | 36 ms | 91.1% (of 102k) | 167 ms | 222 ms | 204 ms | 436× |
| 50 | 100 ms | 87.1% | 526 ms | 675 ms | 625 ms | 742× |

At our pacing Narwhal does not carry the load at n=20–50 and shows a ~440 ms
queue at n=10 (E2E 484 against consensus 44): these delays are too small for
it, so they are not its best configuration and not usable for the
comparison. They do show that its §8.3 latencies (200/400 ms delay) were far
from its best at n=20–30 (577 → 83, 731 → 204 ms).

Narwhal, same settings, double the delay (28 October):

| n | batch delay | delivered | consensus lat. | E2E | fill | from batch ready | clients missed rate |
|---|---|---|---|---|---|---|---|
| 10 | 8 ms | 99.0% | 42 ms | 477 ms | 4 ms | 473 ms | 79× |
| 20 | 32 ms | 99.2% | 76 ms | 170 ms | 16 ms | 154 ms | 237× |
| 30 | 72 ms | 98.2% (of 102k) | 202 ms | 468 ms | 36 ms | 432 ms | 341× |
| 50 | 200 ms | 98.2% | 512 ms | 773 ms | 100 ms | 673 ms | 750× |

Best passing Narwhal point per size so far (≥95% delivered, lowest latency
from batch ready): n=10 473 ms (8 ms; at 4–8 ms its E2E sits ~430 ms above its
consensus latency, so its n=10 best is probably at a larger delay, untested);
n=20 154 ms (32 ms); n=30 432 ms (72 ms; 36 ms gave 204 ms but only 91.1%);
n=50 621 ms (§8.3 run, 400 ms delay). Against ours (gap n²/25): 11.9 / 39.2 /
84.8 / 226.1 ms.

Our ceilings: runs above the passing rates (n=10 350k, n=30 330k, n=50 240k)
did not complete normally (reported by the user as "didn't run well"; no
output kept). The passing rates in §18.2 are taken as the ceilings.

Two more Narwhal runs (28 October):

| n | batch delay | delivered | consensus lat. (leader / non-leader) | E2E | fill | from batch ready |
|---|---|---|---|---|---|---|
| 10 | 32 ms | 99.4% | 278 ms (16 / 197) | 737 ms | 16 ms | 721 ms |
| 30 | 50 ms | 90.7% (of 102k) | 148 ms (64 / 123) | 202 ms | 25 ms | 177 ms |

Narwhal at its best passing configuration (≥95% delivered, lowest latency
from batch ready), against ours at gap n²/25:

| n | Narwhal delay | Narwhal from batch ready | Narwhal consensus | ours E2E | ratio |
|---|---|---|---|---|---|
| 10 | 8 ms | 473 ms | 42 ms | 11.9 ms | 40× |
| 20 | 32 ms | 154 ms | 76 ms | 39.2 ms | 3.9× |
| 30 | 72 ms | 432 ms | 202 ms | 84.8 ms | 5.1× |
| 50 | 400 ms (§8.3) | 621 ms | — | 226.1 ms | 2.7× |

Narwhal's E2E sits far above its consensus latency at every n=10 delay tried
(+440 / +435 / +459 ms at 4 / 8 / 32 ms) and erratically elsewhere (+26 to
+266 ms): time spent between the client and the header, not in consensus.
Untraced. Narwhal points below 95% delivered but with lower latency: n=20
16 ms 83 ms (90.3%), n=30 36 ms 204 ms (91.1%), n=30 50 ms 177 ms (90.7%).

