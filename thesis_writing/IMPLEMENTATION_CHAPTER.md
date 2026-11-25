# Chapter 6 — Implementation: a section-by-section guide

This file tells you what to write in chapter 6 and where each fact comes from.
It follows the structure of the implementation chapter in André Santos's
dissertation (*Probabilistic Chained Blockchain Consensus*, FCUL, chapter 6),
which the user is using as a model. That chapter has six sections:
initialization, architectural overview (with a task/channel figure), data
structures (with a UML figure), the VRF, garbage collection, and challenges.
We keep that order and adapt each section to our system. We add two sections
that system did not need: the separation into traffic planes, and the
baselines and instrumentation.

**Authorities, unchanged:**
- `THESIS_CONTEXT.md` § "Chapter 6 — Implementation (as built)" holds the
  facts and the "as-built gaps".
- `PSEUDOCODE.md` holds the algorithms with source line references.

This guide does not replace either file. It arranges their content into
sections and adds what they lack: the task structure, the data structures,
initialization and garbage collection. Where this file and those two
disagree, they win; tell the user.

**Figures.** Three figures are provided as screenshots for Overleaf; the user
adds them. Reference them as Figure 6.1, 6.2 and 6.3, and use the captions
given below. Do not describe anything in the prose that a figure shows and
the text below does not state.

**Rules that still apply:**
- One protocol: describe the code as it is, never as a sequence of changes.
- Write q or n − f for the quorum.
- Naming (user, 30 October): the broadcast of this protocol is **APRBC**, and
  the figures say so. Figure 6.2 and the structure names below use the APRBC
  spelling (`APRBCSailfish`, `APRBCMessage`, `APRBCDag`), although the source
  code still spells them `PRBC…`. Paths and variables such as
  `network/prbc_message.rs` and `PRBC_SAMPLE_C` are real names, so they stay.
  Never write "PRBC-orig".

---

## Opening (½ page)

Model it on André's opening: what the chapter covers, the language, and why.

- **Language and repository.** Rust. One Cargo workspace with two crates:
  - `shared`: environment loading, keys, transaction generator;
  - `sparse_bullshark`: the protocols.
- **One binary, several protocols.** The binary selects the protocol at
  start-up from the `PROTOCOL` variable (`main.rs`):
  - `prbc_sailfish`: ours;
  - `sailfish`: the Sailfish baseline, run with inline payload or with
    digests.

  The same networking, keys, transaction generator and measurement code
  therefore serve both protocols, so a difference between them is a protocol
  difference and not an implementation difference. Say this: it is the main
  reason the comparison against Sailfish is fair.
- **Narwhal.** The Narwhal-based Sailfish baseline is the authors' own
  implementation (nibeshrestha/sailfish), run unmodified (§6.8).
- **Why Rust.** The same reason André gives: speed with memory and
  concurrency safety, which matters for a long-running process with many
  concurrent tasks.
- **Main libraries:**
  - Tokio: multi-threaded asynchronous runtime;
  - ed25519-dalek: signatures;
  - sha2: hashes;
  - bincode with serde: wire format.
- **Size.** `prbc_sailfish.rs` is about 3,600 lines; the whole workspace is
  about 7,800. Use these numbers or leave size out; do not round them up.

---

## 6.1 Initialization

What a process has before the protocol starts (`shared/src/initializer.rs`,
`prbc_sailfish.rs` `connect`):

- **Configuration file.** `nodes.csv` gives every process's id, host and
  port, plus an optional fault-injection behaviour (§6.8). Each process reads
  the same file.
- **Keys.**
  - Ed25519 key pairs.
  - The public keys are in `public_keys.toml`, known to every process.
  - Each process's private key is passed in an environment variable,
    `PRIVATE_KEY_<id>`.
  - André does the same; say so if useful.
- **Command line.** The process's id, the transaction size in bytes, and the
  maximum number of transactions per batch.
- **Protocol parameters.** These are environment variables:
  - the offered load;
  - the minimum gap Δ between proposals;
  - the round and recovery timeouts;
  - the retention window R;
  - the sampling constant C.

  The full list is in `THESIS_CONTEXT.md` § "Configuration surface". Put it in
  a table in this chapter or in chapter 7, not both.
- **Connection handshake.** This differs from André's, so describe it
  exactly.
  - Every process opens **three** TCP connections to every other process, one
    per traffic plane (§6.3).
  - On each connection the dialler writes:
    - its id,
    - the plane number (one byte),
    - a fresh 32-byte nonce,
    - its Ed25519 signature over the nonce.
  - The listener checks the signature against the claimed id's public key.
    It rejects an unknown id, a bad signature, or a second connection for the
    same (peer, plane).
  - A process starts the protocol once it has accepted all 3(n − 1) incoming
    connections and its own 3(n − 1) outgoing ones are established.
  - TCP_NODELAY is set on every connection.
  - The connection authenticates the peer once. After that, messages are
    attributed to the peer by the connection they arrive on. The signatures
    the protocol needs (votes, vertices, no-votes, timeouts) are carried
    inside the messages and checked separately (§6.2).
- **Genesis.** Each process inserts a genesis vertex for round 0. It is
  certified and ordered from the start, so round-1 vertices have a parent.

Unlike André, there is no separate nonce broadcast before the protocol
starts: the signed nonce is part of each connection's handshake.

---

## 6.2 Architectural overview — **Figure 6.1**

**Caption:** *Tasks of one process. Messages from each peer arrive on three
separate planes, pass through one consensus task, and leave on the same
three planes. Each stacked box stands for n − 1 tasks, one per peer.*

**The figure is deliberately simple, so the prose must carry the detail.** It
shows one idea: many tasks handle the network, and exactly one handles the
protocol. Introduce it in this order.

1. **The idea first.** A process does two kinds of work: moving bytes and
   running the protocol. Moving bytes happens for every peer at once, so it
   gets many small tasks. Running the protocol needs a single consistent view
   of the state, so it gets one task. No lock protects the protocol state,
   because only that task touches it.
2. **Read the figure in the order of its numbers.** They give the order in
   which a message meets the tasks:
   - (1) reader tasks: the message comes in and is checked;
   - (2) consensus task: it decides what to do;
   - (3) sender tasks: the messages it produces go out.

   The three rows are the three traffic planes (§6.3): one TCP connection per
   peer per plane.
3. **Follow one message.** Use this example, adapted to the thesis's voice:

   > Suppose peer j sends a vote. (1) It arrives on the control connection
   > from j, where a reader task, dedicated to that connection, deserializes
   > it and checks its signature. The reader places the valid vote in the
   > control queue. (2) The consensus task takes it from the queue and records
   > it. If it is the q-th vote for that vertex, the vertex is certified. When
   > the consensus task produces a message of its own, such as its vote for a
   > vertex, it places the message in the outgoing control queue. (3) A sender
   > task serializes it once and writes the same bytes to the connection of
   > each peer.
   >
   > A batch follows the same route on the bottom row. The difference is
   > priority: the consensus task serves the control queue first, the
   > consensus-data queue second and the dissemination queue last, and it
   > takes a limited number of messages from each in every iteration. So a
   > backlog of batches cannot delay a vote.

4. **Then give the detail below**: the table, the queues and the loop.

**"Sender tasks" in the figure are two kinds of task** in the table below: one
dispatcher per plane (serializes each message once), and one writer per peer
per plane (writes to the socket). Say this in one sentence, so the reader can
match the figure to the table. "Each arrow is a queue" in the figure means
the bounded channels listed below. The figure lists only the main messages of
each plane; the full lists are in §6.3.

Each process runs on a multi-threaded Tokio runtime. Its tasks are:

| task | how many | what it does |
|---|---|---|
| **Reader** | 3(n − 1): one per peer per plane | Reads length-prefixed frames, deserializes them, and drops a message that arrived on the wrong plane. **Checks the signatures the message carries** (vote, vertex, no-vote; certificate votes are filtered). Drops a vote for a slot already certified locally without checking it. Passes the message to the consensus task over that plane's inbound channel. |
| **Consensus** | 1 | Owns every protocol data structure (§6.4); no other task reads or writes them. Event loop described below. |
| **Plane dispatcher** | 3: one per plane | Receives (destination, message) from the consensus task. **Serializes the message once** and hands the same frame to the writer task of each destination (one peer, a list, or all). |
| **Writer** | 3(n − 1): one per peer per plane | Writes frames to its socket in order. On the dissemination plane only, an optional bandwidth pacer (`NETWORK_MBPS`) spaces the writes; consensus traffic is never paced. |

**Channels.** All channels are bounded Tokio channels:
- 3 inbound channels, reader → consensus, capacity 1,024 each;
- 3 dispatch channels, consensus → dispatcher, capacity 1,024 each;
- one channel per writer, capacity 1,000 frames.

**The consensus task's loop** (`start`, about `prbc_sailfish.rs:2896`):
1. Wait, with `tokio::select!` set to *biased*, for the first message from
   the control channel, then the consensus-data channel, then the
   dissemination channel, or for a short idle tick. The tick is 50 ms, or
   shorter when the proposal gap Δ ends sooner.
2. Drain each inbound channel up to a fixed budget per iteration:
   - 256 control messages,
   - 64 consensus-data messages,
   - 16 dissemination messages.

   So a backlog of large batch frames can never starve votes and timeouts.
3. Advance the recovery and certificate-fetch timers.
4. Run the proposal step: advance the round if the rules allow it, build
   the batch, create, sign and broadcast the vertex. Then re-handle the
   proposals whose parents became certified.

**There is no separate timer task**, unlike André's design. The round
timeout is checked inside the loop: when the round cannot advance, the
process compares the time since the round started against the timeout. The
50 ms tick bounds how late that check can run.

**Why signature checks run on the reader tasks.** Each round, each process
checks about n² vote signatures (n vertices × n votes). Done one at a time in
the consensus task, that work limits the round rate at n = 50. On the reader
tasks the checks run in parallel, one task per peer, and the consensus task
only sees valid messages. `THESIS_CONTEXT.md` already asks for this to be
written as design rationale; this is where it goes.

**The one piece of shared state.** The set of slots this process has
certified is shared with the reader tasks (behind a read–write lock), so they
can drop late votes without checking them. About f of every n votes for a
vertex arrive after it is certified. Byte counters are shared atomics (§6.8).
Nothing else is shared.

**Transactions are generated inside the consensus task**, not submitted by
clients. As in André's implementation, the focus is the protocol, not client
interaction. When a process proposes, it builds its batch from the
transactions that arrived at the offered load since its previous batch (up
to the maximum). It sends the batch, then the vertex
(`THESIS_CONTEXT.md` § "One batch per vertex"). Transactions are padded to
the configured size and carry a unique id, so every batch has a distinct
digest. Each batch ends with a (source, sequence) tag, so even an empty
batch is unique.

**Execution is simulated.** An ordered vertex whose batch is present is
"executed": its transaction count is added to the throughput counter, and
the batch moves to the retention store (§6.6). There is no state machine,
and nothing is written to disk. André writes finalized blocks to a JSON
file; we do not. Say so in one sentence.

---

## 6.3 Traffic planes (new section; no counterpart in André's chapter)

This is our main architectural decision; give it its own section.

Each pair of processes is joined by three TCP connections, one per plane:

| plane | messages | size |
|---|---|---|
| Control | vote, timeout, no-vote, vertex recovery request, batch request, certificate request | a few hundred bytes |
| Consensus data | propose, vertex recovery response, certificate | a few KB (a vertex is a digest, edges and certificates, no payload) |
| Dissemination | batch, batch response | up to the batch size (256 KB at 500 × 512 B) |

**Rule.** The message type fixes the plane (`TrafficPlane::for_message`). A
reader drops a message that arrives on another plane.

**Reason.** TCP delivers in order. On a single connection, a vote queued
behind a 256 KB batch waits for the whole batch to be sent. Separate
connections give each plane its own send buffer and its own congestion
window. Together with the biased select and the drain budgets in the
consensus task (§6.2), this makes votes and timeouts independent of how much
payload is in flight.

**The consequence the protocol is built around.** The q digest votes for a
vertex often reach a process before the batch does, because they travel on a
faster plane. The process then certifies the vertex without its batch.
Normally the batch arrives shortly after. If it does not, recovery fetches it
(§6.5 and chapter 4's recovery figure). The counters in §6.8 show that the
first case is common and real fetches are rare. Present this as the planes
working as designed, not as an error path.

---

## 6.4 Data structures — **Figure 6.2**

**Caption:** *Main data structures of the implementation. Messages are
the variants of one enumeration; the process state is held by a single
`APRBCSailfish` structure owned by the consensus task.*

Follow André: say Rust has structures and enumerations rather than classes,
and that both hold data and methods.

**Shared types** (`shared` crate):
- `Node`: id, host, port, behaviour.
- `Environment`: this process, all processes, transaction size, maximum
  batch size, offered load.
- `TransactionGenerator`: makes padded transactions with unique ids.
- `Transaction`.

**`Vertex`** (`types/vertex.rs`):
- `round`, `source`;
- `block`: **one 32-byte batch digest**, never the payload;
- `edges`: strong edges, hashes of q vertices of round r − 1;
- `weak_edges`: hashes of older vertices, within the GC window, that are not
  otherwise reachable;
- `tc`: optional timeout certificate;
- `nvc`: optional no-vote certificate;
- `hash`: SHA-256 over all of the above. Each variable-length field is
  length-prefixed, and weak edges are sorted, so the hash is unambiguous and
  deterministic.

`signed_round` and `sample_proof` exist and are always empty. Mention them
only if you mention the VRF gap (§6.7).

**`APRBCMessage`** (`network/prbc_message.rs`): one enumeration with 11
variants. Group them by plane, as in the §6.3 table:
- Batch, BatchResp;
- Propose, Vote;
- Recovery, RecoveryResp, BatchRequest;
- CertRequest, Certificate;
- Timeout, NoVote.

**Domain-separated signing.** Each kind of signature covers its own tagged
byte string:
- a vote signs `"prbc-vote" ‖ round ‖ source ‖ hash`;
- a vertex signs `"prbc-vertex" ‖ hash`;
- a no-vote signs `"prbc-no-vote" ‖ round`.

So a signature made for one purpose can never be presented as another.

**`APRBCSailfish`** holds the process state. Do not list its 80 fields.
Describe it by role, as André describes his mappings:

| group | structures | role |
|---|---|---|
| DAG | `APRBCDag` (round → hashes, hash → vertex) | certified vertices, used for round advance, commit and ordering |
| Payload | `BatchStore` (digest → batch), `pending_on_batch` | batches held; proposals waiting for their batch before the vote |
| Votes and certificates | votes per (round, source, hash); `voted_hashes` (one vote per slot); `hash_committed` (slot → certified hash) with a per-round index | the APRBC vote phase and certification |
| Vote rule | `parked_on_parents`, `parent_waiters`, `cert_wanted` | proposals waiting for their parents to be certified locally; certificates being fetched |
| Rounds | timeouts per round, current timeout certificate, no-votes per round | round advance and leader skipping |
| Recovery | `RecoveryState` per hash (target: vertex or batch digest; the voter list; position; passes; next request time) | Figure 6 of `PSEUDOCODE.md` |
| Retention | `RetentionStore<Vertex>`, `RetentionStore<batch>` | delivered items kept R rounds for peers (§6.6) |
| Metrics | timestamps per vertex, counters | §6.8 |

**Like André's design, there is no separate blockchain or log structure.**
What is ordered is a set (`already_ordered`) plus counters. A vertex's
parents are found through its edges in the DAG.

---

## 6.5 Sampling (replaces André's "Verifiable Random Function")

André's §6.4 implements a VRF (sign a seed, hash the proof, seed a PRNG,
shuffle). **Our implementation has no VRF.** Describe exactly what it does
(`compute_sample_for_nodes`, about `prbc_sailfish.rs:81`):

1. Seed = SHA-256(batch digest ‖ salt). The salt is `"prbc_s1"` for S1, and
   `"prbc_s2" ‖ id` for member id's S2.
2. Each process id gets a score: the first 8 bytes of SHA-256(seed ‖ id).
3. The sample is the s ids with the lowest scores, where s = ⌈C·√n⌉ and
   C = 1.4 by default (`PRBC_SAMPLE_C`).

The sample depends only on the batch digest, so every process computes the
same S1 and S2 sets and can check that a relay came from someone in S1. No
proof is needed: anyone holding the digest can recompute the sample.

The cost is that the sample is predictable from the digest, and the digest
is known to the batch's sender before anyone else. **This is as-built gap 1
in `THESIS_CONTEXT.md`, and decision 2 in `README.md` is still open.** Write
it as that file says: either the design intends public recomputability, or
the VRF is unimplemented. Do not choose; leave `% DECISION` in the text.

Also state as-built gap 3 here: the sampling governs only batch relay. Votes
go to all parties.

---

## 6.6 Garbage collection

Same question as André's §6.5: the protocol runs indefinitely, so state must
be freed. We have **three windows**, each measured back from the last ordered
round:

| window | default | what is freed below it | why that is safe |
|---|---|---|---|
| DAG | 4 rounds | ordered vertices leave the DAG (unordered ones stay, so a later weak edge can still include them) and move to the retention store | ordering is done with them; the commit rule looks only at recent rounds |
| Vote records | 128 rounds | votes, one-vote-per-slot records, per-round certification index, timeouts, no-votes, edge records, received proposals | small; kept long so a late message for a recent slot is never mistaken for a new one |
| Retention | R = 50 rounds (`RETENTION_ROUNDS`) | retained vertices and batches; recovery and certificate fetches for older rounds are dropped | after R rounds no correct peer can still need them, unless it is so far behind it would need state transfer, which is not implemented |

- **Batches** leave the batch store when their vertex is executed. They go
  to the retention store, so peers can still recover them.
- **The weak-edge window** (GC depth = max(R, 4)) is also the bound on how far
  back a weak edge may point. That keeps every certificate a process may need
  still held by its voters. This is the role Narwhal's `gc_depth` plays (50
  by default, which is where R = 50 comes from).
- The boundary "R rounds behind needs state transfer" is already in
  `THESIS_CONTEXT.md` (Recovery). Repeat it here in one sentence, as the
  limit of the garbage collection, not as a flaw.

---

## 6.7 As-built gaps

Copy the five items from `THESIS_CONTEXT.md` § "As-built gaps", in its own
words and in its order:
1. no VRF (cross-reference §6.5);
2. timeout certificates are carried but not checked;
3. sampling only on the payload path;
4. recovery timing;
5. the two speed-only recovery limitations.

Keep the subsection short; the reasons are already in that file.

---

## 6.8 Baselines, fault injection and instrumentation

**Sailfish baseline in the same binary** (`sailfish.rs`):
- the Sailfish DAG and commit rule;
- reliable broadcast as a plug-in, a `ReliableBroadcast` trait with two
  implementations, Bracha and signed-vote (§ the signed-vote description the
  user already has);
- the commit rule counts 2f+1 *first messages*, not full deliveries, as in
  the Sailfish paper;
- `MEMPOOL_MODE=decoupled` replaces the inline payload with a batch digest,
  using the same `BatchStore`, so one binary measures both inline and
  digest-based Sailfish.

Note that this baseline's thresholds are 2f+1 (`EVALUATION_RESULTS.md`
status box).

**Narwhal-based Sailfish.** The authors' public implementation, run with its
own benchmark harness. We change nothing in its code; parameters are in
chapter 7.

**Fault injection** (`shared/src/domain/node.rs`, set per process in
`nodes.csv`). There are seven behaviours. Use this table; it supersedes the
four-row table in `THESIS_CONTEXT.md` § "Fault injection", which predates
Byz3–5:

| behaviour | what the process does |
|---|---|
| Ok | correct |
| Byz1 | sends its vertex to only 2f + 1 peers |
| Silent | never proposes |
| Byz2 | relays a batch with the right digest and a wrong body |
| Byz3 | sends its batch to only 2f + 1 peers |
| Byz4 | never answers recovery requests |
| Byz5 | Byz1, and its votes too go to only 2f + 1 peers (forces certificate fetches) |

**Instrumentation.** Every process prints one results block at the end of its
60-second window. The run scripts take the median across processes.
- **Latency.**
  - Consensus latency: vertex creation → ordering.
  - End-to-end latency: batch creation → ordering, own vertices only.
- **Throughput.** Transactions in executed batches, counted from each
  batch's payload, divided by 60 s.
- **Resources.**
  - Process CPU (one core and whole machine) and peak memory, from `/proc`
    (`utils/metrics.rs`).
  - Bytes sent and received per plane, counted at the writer and reader
    tasks.
- **Protocol counters.** For example "payload-lag events" (certified before
  the batch arrived) against "network recoveries" (real fetches). These are
  what §6.3 cites.

Chapter 7's methodology describes the machine-level monitor. Here, say only
that the in-binary counters exist and what they count.

---

## 6.9 Challenges

André's §6.6 is one honest paragraph; write ours the same way, generic and
in the present tense. **Do not tell a story of results that were later
changed (one-protocol rule).** The true challenges, all of which can be
stated without a before/after:

- **Asynchrony corner cases.** No message order is guaranteed, and a
  digest-only consensus path makes this worse: a process can hold the votes
  before the vertex, or the vertex before its batch. It can also see a
  vertex whose parents it has not certified. Each case needs a waiting state
  (parked proposals, pending batches, certificate fetches) and a way out of
  it.
- **Making the proof and the code agree.** Writing the correctness argument
  (chapter 5) and the implementation side by side forced the code to do
  exactly what the proof assumes:
  - votes bound to their slot;
  - signed vertices;
  - the vote rule;
  - leader skipping with no-vote certificates;
  - every correct party votes.

  Say that this was the hardest part. **Do not** say any result was measured
  without these rules.
- **CPU, not bandwidth, is the limit at n = 50.** Each round costs about n²
  signature checks. This shaped two parts of the implementation:
  - checking signatures on the reader tasks;
  - the minimum gap Δ between proposals.
- **Isolating the consensus path from payload.** This motivated the planes,
  the biased loop and the drain budgets.
- **Benchmarking a distributed system fairly.** Matching batch sizes and
  timers with the Narwhal baseline, and keeping runs from overlapping on the
  cluster. Chapter 7's threats-to-validity covers this; give it one sentence
  here and a cross-reference.
- **First experience with Rust and Tokio** (if the user agrees; André says
  this about himself, so ask before writing it).

---

## Figures (screenshots, added by the user)

| figure | shows | section |
|---|---|---|
| 6.1 | tasks of one process: readers, consensus task, senders, on three planes | 6.2 |
| 6.2 | data structures (UML-style) | 6.4 |
| 6.3 | lifecycle of one vertex and its batch at one process: received → waiting for batch / parents → voted → certified → executed and ordered → retained → freed | 6.3 and 6.6 |

**Caption for 6.3:** *Life of a vertex and its batch at one process. Votes
can certify a vertex before its batch arrives (dashed path); recovery then
fetches what is missing.*
