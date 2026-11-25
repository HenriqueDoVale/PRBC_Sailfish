# PRBC-Sailfish — pseudocode of the implemented protocol

Transcribed from `sparse_bullshark/src/consensus/prbc_sailfish.rs` (line numbers
in margin comments), not from design notes. Figure numbering follows the
Sailfish paper so the two can sit side by side in the evaluation chapter.

> **Updated 27 October 2026, twice.**
> 1. **Recovery (Figure 6) was rewritten.** A party that has a certified
>    vertex but not its batch fetches the batch; recovery cycles through the
>    voters until it succeeds; a responder needs no votes of its own; correct
>    parties keep delivered vertices and batches for R rounds.
> 2. **Four correctness fixes**, so that the code satisfies the safety and
>    liveness argument (table below). They change Figures 3, 4 and 5 and add
>    Figure 7. All line numbers are refreshed.
>
> **Updated 29 October:** a fifth fix, the last row of the table. Lines 48,
> 55, 57–59, 72–75, 100–102 and 271 changed in place; no line number moved.
>
> This history is for the writing agent only. The thesis describes the
> protocol as it is now (the "Now" column), as the protocol used throughout.

**The correctness fixes (second and third updates):**

| Before | Now |
|---|---|
| A party that certified a slot before it could vote never voted; Byzantine voters could send their votes to only some parties and leave the others one vote short, so Lemma 4.6 (validity) failed | A party that certifies first delivers at once and still votes once the vote rule holds (lines 48, 57–59, 100–102) |
| A vote signed the hash alone, so a faulty party could relabel an honest vote for one slot as a vote for another | A vote signs (round, source, hash) (line 76) |
| A vertex was unsigned; anyone could relay a vertex claiming any source | The source signs its vertex; it is checked before anyone votes (lines 38, 44) |
| Leaders were committed strictly in sequence; one leader that never proposed stopped ordering for good | Sailfish's rule: commit the latest directly supported leader, walk back, skip leaders with no strong path (Figure 5). A leader that skips its predecessor carries a no-vote certificate (lines 39–40, 126–129, 152, 172–173) |
| A party voted whatever the vertex referenced; ordering silently skipped parents it did not have | A party votes only for a well-formed vertex whose parents are all certified locally (lines 60–67, Figure 4); missing certificates are fetched (Figure 7); ordering waits until the whole history is present and orders it by (round, source) (Figure 5) |

**Differences from the earlier (≈5-month-old) pseudocode draft, summarised:**

| Earlier draft | As implemented |
|---|---|
| VRF sampling: `VRF_verify(v.proof_S1, P_i) < c√n/n` | Deterministic hash sampling over the **batch digest**; `sample_proof` is always empty in PRBC |
| `v.block` = a block of transactions | `v.block` = a **32-byte SHA-256 digest**; payload travels separately |
| One object broadcast (`decoupled_bcast(v,r)`) | **Two** objects relayed independently: `Batch` (payload) and `PRBCPropose` (vertex) |
| Voting gated by `CHECK_SEC_SAMPLE(v)` | **Every** party votes, once the vertex is well formed and its parents are certified locally; votes go to all. S2 is a relay set, never a voting set |
| Vote cast as soon as the block arrives | Vote **blocked** until the referenced batch is in `batchStore` |
| `certifiedHashes` + multicast `⟨request_block, h⟩` | Unicast recovery of the vertex, then of its batch, from the certificate's voters one at a time, checked against the hash and digest the requester already holds, repeated until it succeeds |
| `hashVotes[h]` keyed by hash alone | `prbcVotes[(round, source, hash)]` + `votedHashes[(round, source)]` equivocation guard |
| `v.nvc ← NVC_{r−1}` (no-vote certificate) | As in the draft and the Sailfish paper: a leader that does not point to the previous leader waits for q signed no-votes and carries them |

---

## Figure 1 — Local variables (party `P_i`)

```
struct vertex v:
    v.round        – round of v in the DAG
    v.source       – party that proposed v
    v.block        – a 32-byte SHA-256 batch digest        ▷ NOT the payload
    v.strongEdges  – hashes of vertices in v.round − 1
    v.weakEdges    – hashes of vertices in rounds < v.round − 1
    v.tc           – timeout certificate for v.round − 1 (if any)
    v.nvc          – no-vote certificate for v.round − 1 (leader vertices only)
    v.hash         – hash over every field above
a propose carries ⟨v, σ_v⟩, σ_v the source's signature over v.hash

struct batch b:
    b.digest       – SHA-256 over b.payload
    b.payload      – the transactions

DAG_i[]            – array of vertex sets, indexed by round
round ← 1
λ                  – load per party: INPUT_RATE / n transactions per second
accrued ← 0 ;  lastBatch ← start of the run
Δ                  – minimum gap between this party's proposals (MIN_PROPOSAL_GAP_MS)
lastProposal       – when this party last proposed
alreadyOrdered     ← {} ;  lastOrderedRound ← 0

▷ ── dissemination state ────────────────────────────────────────────────
batchStore[]       ← {}   ▷ digest → payload
seenBatches        ← {}   ▷ digests already verified (dedup)
forwardedBatches   ← {}   ▷ digests this party has already relayed
pendingOnBatch[]   ← {}   ▷ digest → proposals (p, v, σ_v) awaiting that payload

▷ ── voting state ───────────────────────────────────────────────────────
prbcVotes[]        ← {}   ▷ (round, source, hash) → {voter → signature}
votedHashes[]      ← {}   ▷ (round, source) → hash     ▷ equivocation guard
hashCommitted[]    ← {}   ▷ (round, source) → hash     ▷ reached QUORUM votes
certifiedSlot[]    ← {}   ▷ hash → (round, source)     ▷ the reverse map
prbcPayloads[]     ← {}   ▷ hash → full vertex, before it enters the DAG
knownEdges[]       ← {}   ▷ hash → strong-edge set (vertices voted on or executable)
edges[]            ← {}   ▷ hash → (round, strong, weak) of every vertex body held
parkedOnParents[]  ← {}   ▷ hash → proposal whose parents are not all certified here
parentWaiters[]    ← {}   ▷ missing parent → hashes of proposals waiting for it
released           ← {}   ▷ proposals to check again (their parent was certified)
executionReady     ← {}   ▷ hashes whose payload is verified locally
executionPending   ← {}   ▷ committed by consensus, payload not yet local

▷ ── round synchronisation ──────────────────────────────────────────────
timeoutStore[]     ← {} ;  currentRoundTC ← ⊥ ;  timeoutSent ← false
timeoutSuspended   ← {}   ▷ rounds whose leader is hash-committed
noVotes[]          ← {}   ▷ round r → {party → signature}: their round-(r+1)
                          ▷ vertex does not point to LEADER(r)

▷ ── recovery, certificate fetch, retention ─────────────────────────────
recoveryState[]    ← {}   ▷ hash → {round, target, voterList, nextIdx, passes,
                          ▷         nextAt, requestedFrom, asked}
                          ▷ target ∈ {VERTEX, BATCH(d)}
certWanted[]       ← {}   ▷ hash → {childRound, hints, attempts, nextAt}
retainedVertices[] ← {}   ▷ hash → vertex, kept R rounds after leaving DAG_i
retainedBatches[]  ← {}   ▷ digest → payload, kept R rounds after execution
R                         ▷ retention window, RETENTION_ROUNDS, default 50
T_rec                     ▷ recovery timeout, RECOVERY_TIMEOUT_MS, default 500 ms
```

---

## Figure 2 — Utilities

```
 1: procedure QUORUM()
 2:     return n − f                       ▷ q; = 2f + 1 when n = 3f + 1; f + 1 if REDUCED_QUORUM (CFT only)

 3: procedure SAMPLE(d, salt)              ▷ deterministic; |SAMPLE| = ⌈c·√n⌉, c = 1.4
 4:     return the ⌈c·√n⌉ parties selected by H(d ‖ salt)

 5: procedure IN_S1(d)                     ▷ is P_i a first-tier relay for digest d?
 6:     return P_i ∈ SAMPLE(d, "prbc_s1")

 7: procedure S2_OF(d)                     ▷ P_i's own second-tier set for d
 8:     return SAMPLE(d, "prbc_s2" ‖ i) \ {P_i}

 9: procedure LEADER(r)
10:     return P_(r mod n)

11: procedure LEADER_HASH_COMMITTED(r)
12:     return (r, LEADER(r)) ∈ hashCommitted

13: procedure GC_DEPTH()                   ▷ :824; how far below a vertex its weak edges reach
14:     return max(R, 4)

15: procedure STRONG_PATH(u, w)            ▷ :1463; w is a vertex of round r_w
16:     return true iff w is reachable from u along edges[·].strong,
17:            through vertices of rounds > r_w
```

Both sampling tiers are keyed on the **batch digest**, so a vertex and the
batch it references are relayed by the same set of parties.

Every signature covers its own tagged byte string (`prbc_message.rs` :13–30),
so a signature made for one purpose can never be presented as another:
`⟨"prbc-vote", r, s, h⟩` for a vote, `⟨"prbc-vertex", h⟩` for a vertex,
`⟨"prbc-no-vote", r⟩` for a no-vote. All three are checked on the receiving
peer's reader task (:113), in parallel, before the message reaches the
consensus loop.

---

## Figure 3 — Probabilistic dissemination

### Batch path (payload, own TCP plane)

```
18: procedure MAKE_BATCH()                                ▷ at proposal time, :890
19:     accrued ← accrued + λ · (now − lastBatch) ;  lastBatch ← now
20:     k ← min(⌊accrued⌋, maxBatch) ;  accrued ← accrued − k   ▷ k = maxBatch if no rate limit
21:     b ← k new transactions, tagged (i, sequence number) ;  multicast b to all parties
22:     if IN_S1(b.digest) then send b to S2_OF(b.digest) ;  batchStore[b.digest] ← b.payload

23: upon receiving batch b from p do                      ▷ :1901
24:     if b.digest ∈ seenBatches then return              ▷ dedup
25:     if H(b.payload) ≠ b.digest then return             ▷ integrity
26:     seenBatches ← seenBatches ∪ {b.digest}
27:     STORE_BATCH(b, relay = true)

28: procedure STORE_BATCH(b, relay)                       ▷ :1934
29:     if relay ∧ IN_S1(b.digest) ∧ b.digest ∉ forwardedBatches then
30:         forwardedBatches ← forwardedBatches ∪ {b.digest}
31:         send b to S2_OF(b.digest)                      ▷ exactly one relay hop
32:     batchStore[b.digest] ← b.payload
33:     for each (p', v, σ_v) ∈ pendingOnBatch[b.digest] do  ▷ release blocked votes
34:         HANDLE_PROPOSE(p', v, σ_v)
35:     pendingOnBatch[b.digest] ← ⊥
```

**Batching (lines 18–22).** Transactions are always available; a party
never waits for them. It builds its batch when it proposes, so rounds run as
fast as votes and certificates allow. The load decides only how many
transactions go in: those that arrived at the rate λ since the party's last
batch, at most `maxBatch` (the configured batch size, `--n-tx`), the rest
carried over. Faster rounds therefore mean smaller batches, and an unlimited
load means every batch is full. The tag makes every batch distinct, so two
vertices never share a digest.

**The minimum gap Δ (line 36).** Every round costs each party about n² vote
signature checks (n vertices, n votes each), whatever the batch size. So Δ
sets the round rate, and with it the batch size (about λ·Δ) and the CPU
spent per second. In the experiments Δ = n²/25 ms (4, 16, 36 and 100 ms at
n = 10, 20, 30 and 50), which keeps every machine at about half its CPU. A
vote for a slot the party has already certified is dropped before its
signature is checked (line 80); RECORD_VOTE would ignore it anyway (line
83). Neither changes what the protocol decides.

### Vertex path (consensus plane)

```
36: procedure BROADCAST_VERTEX(r)    ▷ :948; when MAY_ADVANCE_ROUND() holds and now ≥ lastProposal + Δ
37:     v ← CREATE_NEW_VERTEX(r) ;  round ← r + 1 ;  lastProposal ← now
38:     σ_v ← sign_i(⟨"prbc-vertex", v.hash⟩)
39:     if r > 1 ∧ ¬LEADER_HASH_COMMITTED(r − 1) ∧ LEADER(r) ≠ P_i then
40:         send ⟨noVote, r − 1, i, sign_i(⟨"prbc-no-vote", r − 1⟩)⟩ to LEADER(r)
41:     multicast ⟨propose, v, σ_v⟩ to all parties
42:     HANDLE_PROPOSE(P_i, v, σ_v)

43: upon receiving ⟨propose, v, σ_v⟩ from p do            ▷ reader task, :113
44:     if ¬verify(pk_{v.source}, ⟨"prbc-vertex", v.hash⟩, σ_v) then return
45:     HANDLE_PROPOSE(p, v, σ_v)

46: procedure HANDLE_PROPOSE(p, v, σ_v)                   ▷ :1657
47:     h ← v.hash
48:     if h ∈ prbcPayloads ∨ h ∈ parkedOnParents ∨ (h ∈ executionReady ∧ (v.round, v.source) ∈ votedHashes) then return
49:     if h ≠ HASH(v) then return                         ▷ hash binds every field
50:     if |v.block| ≠ 32 then return                      ▷ exactly one digest
51:     edges[h] ← (v.round, v.strongEdges, v.weakEdges)   ▷ authentic: the hash covers them

52:     if v.block ∉ batchStore then                       ▷ ★ payload precondition
53:         if h ∈ recoveryState ∧ recoveryState[h].target = VERTEX then
54:             SWITCH_TO_BATCH(h, v.block)                ▷ vertex now known (Fig. 6)
55:         pendingOnBatch[v.block] ← pendingOnBatch[v.block] ∪ {(p, v, σ_v)}   ▷ replaces an unsigned copy of v
56:         return                                         ▷ NO vote until payload is local

57:     if (v.round, v.source) ∈ hashCommitted then        ▷ quorum arrived first: deliver, still vote
58:         if hashCommitted[(v.round, v.source)] ≠ h then return
59:         ON_EXECUTION_READY(h, v) ;  if σ_v = ⊥ then return   ▷ ⊥: fetched by recovery, unsigned

60:     case CHECK_PARENTS(v) of                           ▷ ★ the vote rule, Figure 4
61:         INVALID:    return                             ▷ never vote for it
62:         MISSING(M):                                    ▷ wait for the parents' certificates
63:             for each m ∈ M do
64:                 parentWaiters[m] ← parentWaiters[m] ∪ {h}
65:                 WANT_CERTIFICATE(m, v.round, {p, v.source})       ▷ Figure 7
66:             parkedOnParents[h] ← (p, v, σ_v) ;  return
67:         READY:      skip

68:     if (v.round, v.source) ∈ votedHashes then
69:         if votedHashes[(v.round, v.source)] ≠ h then return   ▷ equivocation
70:     else
71:         votedHashes[(v.round, v.source)] ← h

72:     if h ∉ executionReady then                         ▷ else delivered already (line 59)
73:         if IN_S1(v.block) then
74:             send ⟨propose, v, σ_v⟩ to S2_OF(v.block)   ▷ same sample as the batch;
                                                            ▷ the source's signature, forwarded
75:         prbcPayloads[h] ← v ;  knownEdges[h] ← v.strongEdges
76:     σ ← sign_i(⟨"prbc-vote", v.round, v.source, h⟩)   ▷ bound to the slot
77:     multicast ⟨vote, v.round, v.source, h, i, σ⟩ to all parties
78:     RECORD_VOTE(i, σ, v.round, v.source, h)

79: upon receiving ⟨vote, r, s, h, j, σ⟩ do                ▷ :1975
80:     if (r, s) ∈ hashCommitted then return ;  if ¬verify(pk_j, ⟨"prbc-vote", r, s, h⟩, σ) then return   ▷ reader task, :113
81:     RECORD_VOTE(j, σ, r, s, h)

82: procedure RECORD_VOTE(j, σ, r, s, h)                   ▷ :1997
83:     if (r, s) ∈ hashCommitted then return
84:     prbcVotes[(r, s, h)][j] ← σ                        ▷ keyed by full context
85:     if |prbcVotes[(r, s, h)]| ≥ QUORUM() then
86:         ON_HASH_QUORUM(r, s, h, prbcVotes[(r, s, h)])
```

Lines 52–56 and 60–67 are the two preconditions of a vote: a party does not
vote for a digest it cannot yet resolve to a payload, nor for a vertex whose
parents it has not certified itself. Recovery (Figure 6) depends on the first:
every voter stored the batch before voting. Certificate fetch (Figure 7)
depends on the second: every voter held a certificate for each parent.

Certifying a slot does not end a party's part in it. If the q votes arrive
before the party can vote, it delivers the vertex at once (lines 57–59 and
100–102) and still votes once both preconditions hold; line 48 lets the
vertex through again for that. Byzantine voters may send their votes to only
some parties, so the others may need the vote of every correct party. A copy
of the vertex fetched by recovery (line 270) carries no source signature and
is never voted for; the source's own propose is, and line 55 keeps it when
both are waiting for the batch.

---

## Figure 4 — DAG construction

```
87: procedure ON_HASH_QUORUM(r, s, h, votes)               ▷ :1281
88:     if (r, s) ∈ hashCommitted then return
89:     hashCommitted[(r, s)] ← h ;  certifiedSlot[h] ← (r, s)
90:     certWanted[h] ← ⊥
91:     for each c ∈ parentWaiters[h] with c ∈ parkedOnParents do   ▷ check them again
92:         released ← released ∪ {parkedOnParents[c]} ;  parkedOnParents[c] ← ⊥
93:     parentWaiters[h] ← ⊥
94:     if s = LEADER(r) then
95:         timeoutSuspended ← timeoutSuspended ∪ {r}      ▷ no effect, see note
96:     if h ∉ DAG_i[r] then
97:         insert skeleton vertex ⟨r, s, h⟩ into DAG_i[r]
98:     if h ∈ prbcPayloads then
99:         ON_EXECUTION_READY(h, prbcPayloads[h])
100:    else if h ∈ parkedOnParents then                   ▷ vertex and batch here: deliver now;
101:        (·, v, ·) ← parkedOnParents[h]                 ▷ it stays parked, so the party still
102:        ON_EXECUTION_READY(h, v)                       ▷ votes once its parents are certified
103:    else if s ≠ i then
104:        d ← v.block if some (p, v, ·) ∈ pendingOnBatch has v.hash = h, else ⊥
105:        START_RECOVERY(r, h, keys(votes), d)           ▷ Figure 6
106:    TRY_COMMIT()

107: procedure ON_EXECUTION_READY(h, v)                    ▷ :1371
108:    if h ∈ executionReady then return
109:    executionReady ← executionReady ∪ {h}
110:    replace skeleton h in DAG_i[v.round] with the full vertex v
111:    knownEdges[h] ← v.strongEdges
112:    recoveryState[h] ← ⊥                               ▷ cancel any recovery
113:    TRY_COMMIT()
114:    if h ∈ executionPending then                       ▷ committed before payload
115:        executionPending ← executionPending \ {h}
116:        output a_deliver(batchStore[v.block], v.round, v.source)
117:        RETIRE_BATCH(v)

118: procedure RETIRE_BATCH(v)                             ▷ :1415
119:    retainedBatches[v.block] ← batchStore[v.block]     ▷ tagged with round v.round
120:    batchStore[v.block] ← ⊥

121: procedure MAY_ADVANCE_ROUND()                         ▷ :1048
122:    if round = 1 then return true
123:    r' ← round − 1
124:    if |{s : (r', s) ∈ hashCommitted}| < QUORUM() then return false
125:    if LEADER_HASH_COMMITTED(r') then return true
126:    if currentRoundTC ≠ ⊥ then
127:        if LEADER(round) ≠ P_i then return true
128:        noVotes[r'][i] ← sign_i(⟨"prbc-no-vote", r'⟩)  ▷ the leader's own no-vote
129:        return |noVotes[r']| ≥ QUORUM()                ▷ ★ wait for NVC_{r'} (Sailfish)
130:    if r' ∈ timeoutSuspended then return false          ▷ never reached, see note
131:    if ¬timeoutSent ∧ elapsed(roundStart) > τ then
132:        σ ← sign_i(r')
133:        multicast ⟨timeout, r', σ⟩ ;  HANDLE_TIMEOUT(i, r', σ)
134:        timeoutSent ← true
135:    return false

136: upon receiving ⟨timeout, r, σ⟩ from p do  HANDLE_TIMEOUT(p, r, σ)

137: procedure HANDLE_TIMEOUT(p, r, σ)                     ▷ :1149
138:    if r < round − 1 then return
139:    timeoutStore[r][p] ← σ
140:    if |timeoutStore[r]| ≥ QUORUM() ∧ currentRoundTC = ⊥ ∧ r = round − 1 then
141:        currentRoundTC ← ⟨r, timeoutStore[r]⟩

142: upon receiving ⟨noVote, r, j, σ⟩ from p do             ▷ :2442
143:    if ¬verify(pk_j, ⟨"prbc-no-vote", r⟩, σ) then return    ▷ reader task, :113
144:    if j = p then noVotes[r][j] ← σ

145: procedure CREATE_NEW_VERTEX(r)                        ▷ :1227
146:    v.round ← r ;  v.source ← i
147:    v.block ← MAKE_BATCH().digest                      ▷ digest only, 32 bytes
148:    v.strongEdges ← {hashCommitted[(r−1, s)] : (r−1, s) ∈ hashCommitted}
149:    v.weakEdges ← COMPUTE_WEAK_EDGES(r, v.strongEdges)
150:    v.tc ← currentRoundTC if ¬LEADER_HASH_COMMITTED(r−1) else ⊥
151:    v.nvc ← ⟨r−1, noVotes[r−1]⟩ if LEADER(r) = P_i ∧ ¬LEADER_HASH_COMMITTED(r−1)
152:            else ⊥
153:    v.hash ← HASH(v)
154:    return v

155: procedure COMPUTE_WEAK_EDGES(r, strongEdges)          ▷ :1180
156:    reachable ← BFS from strongEdges, following knownEdges ∪ weakEdges
157:    return sorted {h : (r'', s) ∈ hashCommitted, h = hashCommitted[(r'', s)],
158:                       0 < r'' ∧ r'' + 1 < r ∧ r'' + GC_DEPTH() ≥ r,
159:                       h ∉ reachable ∧ h ∉ alreadyOrdered ∧ h ∈ DAG_i}

160: procedure CHECK_PARENTS(v)                            ▷ the vote rule, :2234
161:    r ← v.round ;  if r < lastOrderedRound − 128 then return INVALID   ▷ vote record pruned
162:    if r = 1 then
163:        return READY if v.strongEdges = {genesis} ∧ v.weakEdges = ∅ else INVALID
164:    if some edge repeats ∨ |v.strongEdges| < QUORUM() then return INVALID
165:    M ← ∅ ;  S ← ∅
166:    for each e ∈ v.strongEdges do
167:        if e ∉ certifiedSlot then M ← M ∪ {e}
168:        else if certifiedSlot[e] = (r − 1, s) with s ∉ S then S ← S ∪ {s}
169:        else return INVALID                           ▷ wrong round, or a repeated source
170:    for each e ∈ v.weakEdges do
171:        if e ∉ certifiedSlot then M ← M ∪ {e}
172:        else if certifiedSlot[e].round ∉ [max(1, r − GC_DEPTH()), r − 2] then return INVALID
173:    if M ≠ ∅ then return MISSING(M)
174:    if v.source = LEADER(r) ∧ LEADER(r − 1) ∉ S ∧ ¬VALID_NVC(v.nvc, r − 1) then
175:        return INVALID                                ▷ skips the previous leader, no NVC
176:    return READY

177: procedure VALID_NVC(c, r)                             ▷ :2301
178:    return c ≠ ⊥ ∧ c.round = r ∧ |c.signatures| ≥ QUORUM()
179:           ∧ every (j, σ) ∈ c.signatures has verify(pk_j, ⟨"prbc-no-vote", r⟩, σ)
```

**Note on lines 94–95 and 130.** They have no effect. A round whose leader is
hash-committed already passes line 125, which returns before line 130 is
reached. The round advances on the leader's hash quorum alone, whether or not
the leader's vertex or batch has arrived. Do not describe the suspension as
doing work. The code keeps it (and Figure 6 still lifts it), but removing it
would change nothing.

**What the vote rule gives (lines 160–176).** A correct party votes for a
vertex only if it holds a certificate for every parent. So every certified
vertex has at least f+1 correct voters, and each of them held the vertex, its
batch (lines 52–56) and a certificate for every parent. Two consequences
carry the correctness argument:
- every parent of a certified vertex is itself certified, so the certified
  vertices form a DAG closed under parents;
- every certified vertex of round r ≥ 2 has strong edges to at least q
  distinct certified round-(r−1) vertices.

**The no-vote rule (lines 39–40, 126–129, 151, 174–175).** A party whose
round-(r+1) vertex does not point to `LEADER(r)` sends a signed no-vote for
r to `LEADER(r+1)`. That leader, if it has no certificate for `LEADER(r)`,
waits until it holds q no-votes and puts them in its vertex as `v.nvc`.
A correct party refuses to vote for a leader vertex that neither points to
the previous leader nor carries a valid NVC. This is what makes skipping a
leader safe (Figure 5).

---

## Figure 5 — Commit rule

```
180: procedure TRY_COMMIT()                                ▷ :1438
181:    anchor ← ⊥
182:    for r ← round − 1 down to lastOrderedRound + 1 do   ▷ latest directly supported leader
183:        if (r, LEADER(r)) ∈ hashCommitted ∧ DIRECT_SUPPORT(r) ≥ QUORUM() then
184:            anchor ← (r, hashCommitted[(r, LEADER(r))]) ;  break
185:    if anchor = ⊥ then return
186:    (r_a, h_a) ← anchor
187:    if ¬HISTORY_COMPLETE(h_a) then return              ▷ ★ never order with a gap
188:    chain ← [h_a] ;  cur ← h_a
189:    for r ← r_a − 1 down to lastOrderedRound + 1 do    ▷ walk back
190:        if (r, LEADER(r)) ∈ hashCommitted then
191:            h_ℓ ← hashCommitted[(r, LEADER(r))]
192:            if STRONG_PATH(cur, h_ℓ) then
193:                chain.append(h_ℓ) ;  cur ← h_ℓ
194:                                                       ▷ any other leader in between is skipped
195:    for each h_ℓ in chain, oldest first do COMMIT_CAUSAL_HISTORY(h_ℓ)
196:    lastOrderedRound ← r_a
197:    PRUNE()

198: procedure DIRECT_SUPPORT(r)                           ▷ :1509
199:    h_ℓ ← hashCommitted[(r, LEADER(r))]
200:    return |{s : (r+1, s) ∈ hashCommitted
201:                 ∧ h_ℓ ∈ knownEdges[hashCommitted[(r+1, s)]]}|

202: procedure HISTORY_COMPLETE(h_a)                       ▷ :1527
203:    complete ← true
204:    for each h reachable from h_a over edges[·].strong ∪ edges[·].weak,
205:          stopping at hashes in alreadyOrdered do
206:        if h ∉ certifiedSlot then                      ▷ not certified here
207:            complete ← false
208:            WANT_CERTIFICATE(h, round of the vertex that references h, {its source})
209:        else if h ∉ edges then                         ▷ certified, body still being
210:            complete ← false                           ▷ recovered (Figure 6)
211:    return complete

212: procedure PRUNE()                                     ▷ :1492, :1565
213:    for each ordered v ∈ DAG_i with v.round < lastOrderedRound − 4 do
214:        remove v from DAG_i
215:        if v.hash ∈ executionReady then retainedVertices[v.hash] ← v
216:    drop votes, pre-quorum payloads, edges and noVotes for rounds < lastOrderedRound − 128
217:    drop retainedVertices, retainedBatches, recoveryState, certWanted and
218:         parkedOnParents entries for rounds < lastOrderedRound − GC_DEPTH()

219: procedure COMMIT_CAUSAL_HISTORY(h_ℓ)                  ▷ :1610
220:    H ← {h reachable from h_ℓ over edges[·].strong ∪ edges[·].weak,
221:          stopping at hashes in alreadyOrdered}
222:    for each h ∈ H in order of certifiedSlot[h] = (round, source) do   ▷ deterministic
223:        alreadyOrdered ← alreadyOrdered ∪ {h}
224:        v ← DAG_i[h]
225:        if h ∈ executionReady then                      ▷ two-tiered delivery
226:            output a_deliver(batchStore[v.block], v.round, v.source)
227:            RETIRE_BATCH(v)
228:        else
229:            executionPending ← executionPending ∪ {h}   ▷ delivered on arrival, line 114
```

A round-`r` leader vertex is **committed directly** when q hash-committed
round-`(r+1)` vertices carry a strong edge to it. Hash-commitment plays the
role of Sailfish's "first message of the RBC": one broadcast plus one vote
round trip, no RBC.

**Why skipping is safe.** If any correct party commits the leader of round r
directly, every certified leader vertex of a later round has a strong path to
it, so the walk back (lines 189–193) never skips it:
- *round r+1:* it points to `LEADER(r)` or carries an NVC for r. An NVC is
  impossible here: its q no-voters and the q direct supporters overlap
  in at least f+1 parties, one of them correct, and a correct party never
  both points to `LEADER(r)` and sends a no-vote for r (line 39);
- *round r+2 or later:* its q strong edges into round r+1 overlap the
  q supporters in at least one vertex (one certified vertex per slot).

So every correct party orders the same leaders in the same order, and orders
each leader's history in the same (round, source) order (line 222). A leader
that never proposes is skipped by the next anchor's walk back instead of
stopping ordering.

**Why ordering waits (line 187).** Ordering needs the edges of every vertex
in the history, not the batches. A vertex is certified here or its
certificate is fetched (Figure 7); its body is here or recovered (Figure 6).
Batches can still arrive later: a vertex ordered without its batch is
delivered when the batch lands (line 114).

---

## Figure 6 — Recovery

Recovery is armed when a hash quorum forms for a vertex this party cannot yet
execute (Figure 4, lines 103–105): either the vertex is missing, or it is here
but parked waiting for its batch. It is cancelled the moment the propose or
batch lands (line 112), which is the common case.

```
230: procedure START_RECOVERY(r, h, voters, d)             ▷ :2461
231:    if h ∈ executionReady ∨ h ∈ recoveryState then return
232:    rot ← (i + h[0]) mod |voters|                      ▷ spread first choice
233:    if d = ⊥ then (target, nextAt) ← (VERTEX, now)     ▷ ask on the next tick
234:    else (target, nextAt) ← (BATCH(d), now + T_rec)    ▷ batch usually still in flight
235:    recoveryState[h] ← { round: r, target, voterList: rotate(voters, rot),
236:                         nextIdx: 0, passes: 0, nextAt,
237:                         requestedFrom: ⊥, asked: ∅ }

238: procedure SWITCH_TO_BATCH(h, d)                       ▷ vertex known, batch not; :446
239:    recoveryState[h].target ← BATCH(d)
240:    nextIdx ← 0 ;  passes ← 0 ;  asked ← ∅ ;  requestedFrom ← ⊥
241:    nextAt ← now + T_rec

242: upon every 50 ms tick do                              ▷ TICK_RECOVERY, :2518
243:    for each h ∈ recoveryState with now ≥ nextAt ∧ h ∉ executionReady do
244:        p ← next entry of voterList from nextIdx with p ≠ i ;  advance nextIdx
245:        if p = ⊥ then                                   ▷ a full pass, no valid answer
246:            nextIdx ← 0 ;  passes ← passes + 1          ▷ start over: never give up
247:            if passes = 1 ∧ DAG_i[h].source = LEADER(DAG_i[h].round) then
248:                timeoutSuspended ← timeoutSuspended \ {DAG_i[h].round}
249:            p ← next entry of voterList from nextIdx with p ≠ i ;  advance nextIdx
250:        nextAt ← now + T_rec · 2^min(passes, 3)         ▷ doubles per pass, up to 8×
251:        requestedFrom ← p ;  asked ← asked ∪ {p}
252:        if target = VERTEX then send ⟨recovery, h, i⟩ to p
253:        else send ⟨batchRequest, d, i⟩ to p             ▷ target = BATCH(d)

254: upon receiving ⟨recovery, h, q⟩ from p do             ▷ responder, :2031
255:    if q ≠ p then return                                ▷ no reflected responses
256:    v ← the full vertex with hash h from prbcPayloads,
257:         DAG_i (only if h ∈ executionReady) or retainedVertices
258:    if v ≠ ⊥ then send ⟨recoveryResp, v⟩ to p           ▷ no vote check

259: upon receiving ⟨batchRequest, d, q⟩ from p do         ▷ responder, :2128
260:    if q ≠ p then return
261:    b ← batchStore[d] or retainedBatches[d]
262:    if b ≠ ⊥ then send ⟨batchResp, d, b⟩ to p

263: upon receiving ⟨recoveryResp, v⟩ from p do            ▷ requester, :2076
264:    h ← v.hash
265:    if h ∉ recoveryState ∨ recoveryState[h].target ≠ VERTEX then return
266:    if p ∉ recoveryState[h].asked ∨ h ∈ executionReady then return
267:    if h ≠ HASH(v) ∨ |v.block| ≠ 32 then RETRY(h, p) ;  return
268:    edges[h] ← (v.round, v.strongEdges, v.weakEdges)
269:    if v.block ∉ batchStore then                        ▷ vertex recovered, batch not
270:        pendingOnBatch[v.block] ← pendingOnBatch[v.block] ∪ {(p, v, ⊥)}
271:        SWITCH_TO_BATCH(h, v.block) ;  return           ▷ unsigned: not voted on (line 59)
272:    ON_EXECUTION_READY(h, v)

273: upon receiving ⟨batchResp, d, b⟩ from p do            ▷ requester, :2162
274:    W ← {h ∈ recoveryState : target = BATCH(d) ∧ p ∈ asked}
275:    if W = ∅ ∨ d ∈ seenBatches then return
276:    if H(b) ≠ d then RETRY(h, p) for each h ∈ W ;  return
277:    seenBatches ← seenBatches ∪ {d}
278:    STORE_BATCH(⟨d, b⟩, relay = false)                  ▷ releases the parked vertex, line 33

279: procedure RETRY(h, p)                                 ▷ :2201
280:    if recoveryState[h].requestedFrom = p then          ▷ the one we are waiting on
281:        recoveryState[h].nextAt ← now ;  recoveryState[h].requestedFrom ← ⊥
```

### Four properties worth stating in prose

1. **The requester checks everything itself.** Recovery is armed only once
   the requester holds q votes for `h` (line 105). So it needs nothing else
   from the responder: a vertex is accepted if it hashes to `h` (line 267),
   and a batch if it hashes to the digest `d` inside that vertex (line 276).
   A responder therefore answers whenever it holds the item (lines 258 and
   262), without holding a quorum of votes itself. Until 27 October the
   responder had to hold a quorum of votes. Byzantine voters could send their votes
   only to the requester, leave every correct voter below quorum, and so
   keep all of them silent. That rule is gone.

2. **Some candidate always holds the data.** The candidates are the q
   voters, and at least q − f ≥ f+1 of them are correct. A party votes only after
   storing the batch and holding the vertex (lines 52–56). Correct parties
   keep both for R rounds after ordering (lines 213–218; R = 50 by default,
   the same role as Narwhal's `gc_depth`).

3. **Recovery never gives up inside that window.** It asks one voter at a
   time (lines 252–253). After a pass with no valid answer it starts over,
   doubling the wait up to 8 × `T_rec` (lines 245–250). A valid late answer
   from anyone already asked is accepted (lines 266 and 274). Recovery is
   dropped only when its round falls R rounds behind the last ordered round
   (lines 217–218). A party that far behind needs state transfer, which is
   out of scope, as it is in Narwhal.

4. **The vertex is fetched first, then the batch, on different timing.** A
   missing vertex is requested on the next tick (line 233). A missing batch is
   normally still travelling on the dissemination plane, so the first batch
   request waits `T_rec` (lines 234 and 241). In fault-free runs neither
   request usually leaves the party, because the propose or batch lands first
   and line 112 cancels the state.

**The guarantee these give.** If a correct party hash-commits a vertex `v`,
then after GST it eventually holds both `v` and its batch, provided it is
less than R rounds behind the other correct parties. In the first pass at
most f Byzantine voters are asked before a correct one, so recovery takes at
most about `f · T_rec` plus one round trip per item.

---

## Figure 7 — Certificate fetch

A party can see a hash referenced as a parent without having certified it
itself: Byzantine voters may have sent their votes to only some parties.
It then asks for the certificate, the q signed votes, which any party can
check and forward.

```
282: procedure WANT_CERTIFICATE(h, r_c, hints)             ▷ :2320
283:    if h ∈ certifiedSlot then return
284:    if h ∉ certWanted then
285:        certWanted[h] ← {childRound: r_c, hints: ∅, attempts: 0, nextAt: now + T_rec}
286:    certWanted[h].childRound ← max(certWanted[h].childRound, r_c)
287:    certWanted[h].hints ← certWanted[h].hints ∪ hints

288: upon every 50 ms tick do                              ▷ TICK_CERTIFICATES, :2343
289:    for each h ∈ certWanted with now ≥ nextAt do
290:        targets ← one party of hints \ {P_i} if attempts = 0, else all parties \ {P_i}
291:        attempts ← attempts + 1 ;  nextAt ← now + T_rec · 2^min(attempts, 3)
292:        send ⟨certRequest, h, i⟩ to targets

293: upon receiving ⟨certRequest, h, q⟩ from p do          ▷ responder, :2373
294:    if q ≠ p ∨ h ∉ certifiedSlot then return
295:    (r, s) ← certifiedSlot[h]
296:    if |prbcVotes[(r, s, h)]| ≥ QUORUM() then
297:        send ⟨certificate, r, s, h, prbcVotes[(r, s, h)]⟩ to p

298: upon receiving ⟨certificate, r, s, h, V⟩ from p do    ▷ requester, :2407
299:    V ← {(j, σ) ∈ V : verify(pk_j, ⟨"prbc-vote", r, s, h⟩, σ)}   ▷ reader task, :113
300:    if h ∉ certWanted ∨ h ∈ certifiedSlot ∨ |V| < QUORUM() then return
301:    if (r, s) ∈ hashCommitted then return               ▷ a second certificate for the
302:                                                         ▷ slot cannot exist
303:    prbcVotes[(r, s, h)] ← V
304:    ON_HASH_QUORUM(r, s, h, V)                          ▷ as if the votes had arrived

305: after handling each message do                        ▷ DRAIN_RELEASED, :2453
306:    for each (p, v, σ_v) ∈ released do HANDLE_PROPOSE(p, v, σ_v)
307:    released ← ∅
```

**Why the fetch succeeds.** A hash is wanted because a vertex references it
(line 65 or 208). If that referencing vertex is certified, at least f+1
correct parties voted for it, and each held a certificate for every parent
(Figure 4). They keep the votes for 128 rounds (line 216), longer than the
GC window that bounds how far below a vertex its parents lie (lines 158 and
172). The first request goes to one party that referenced the hash, because
it usually holds the certificate. If no certificate comes within `T_rec`,
the request goes to everyone, with the wait doubling up to 8 × `T_rec`, so
after GST some correct holder answers. In fault-free runs no request is sent:
the votes themselves arrive first (line 90 cancels the want).

**The guarantee it gives (totality).** If a correct party certifies a vertex,
every correct party eventually certifies it and, by Figure 6, holds its
vertex and batch, provided it is less than R rounds behind. Together with the
vote rule, the certificates and bodies of a leader's whole history become
available everywhere, so every correct party can pass line 187.

---

## Not implemented (present in the Sailfish paper, absent here)

- **Reliable broadcast.** Replaced wholesale by best-effort multicast plus the
  S1→S2 relay and the vote quorum. Non-equivocation comes from the source's
  signature and `votedHashes` (lines 44, 68–71); totality comes from
  certificate fetch and recovery (Figures 6 and 7) rather than from RBC.
- **Timeout certificates are carried but not checked.** `v.tc` is filled in
  (line 150) but no party verifies it in a received vertex. Safety does not
  rest on it: skipping a leader rests on the NVC, which is checked
  (lines 174–175).
- **State transfer.** A party more than R rounds behind cannot recover what
  it missed, as in Narwhal.
