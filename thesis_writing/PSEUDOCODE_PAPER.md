# PRBC-Sailfish — pseudocode in the style of the Sailfish paper

Five figures for chapters 4 and 5. Figures 1–3 follow Sailfish's Figures 1–3
(Shrestha et al.) line for line where the protocol is the same. Figures 4 and 5
are new: the PRBC broadcast and recovery. `PSEUDOCODE.md` stays the detailed,
code-referenced version for the implementation chapter; this file is the
paper-level one.

**How to read the figures.** They are `diff` blocks, so most viewers colour them:
- **green, `+`**: a line PRBC-Sailfish adds, or our version of a line it changes;
- **red, `-`**: Sailfish's original text, shown just above the line that replaces
  it, or a Sailfish line the protocol drops (no line number);
- **uncoloured**: a line exactly as in Sailfish.

Line numbers are ours and run on across the five figures, as in the paper.
Figures 4 and 5 are entirely new. In the thesis, drop the red lines and show
the green ones shaded or marked, so readers see what PRBC-Sailfish adds.

**Notation.** n parties, at most f Byzantine, n ≥ 3f + 1, quorum q = n − f
(q = 2f + 1 when n = 3f + 1; Sailfish writes 2f + 1 because it assumes
n = 3f + 1). A broadcast instance has a tag τ = (r, p): round r, sender p.
H is SHA-256. L_r is the leader of round r, P_{r mod n}: leaders rotate.

---

## Figure 1 — Basic data structures

```diff
Local variables:
    struct vertex v:                                  ▷ The struct of a vertex in the DAG
        v.round       – the round of v in the DAG
        v.source      – the party that broadcast v
-       v.block       – a block of transactions
+       v.block       – the digest H(B) of a batch B of transactions
        v.strongEdges – a set of vertices in v.round − 1 that represent strong edges
        v.weakEdges   – a set of vertices in rounds < v.round − 1 that represent weak edges
        v.nvc         – a no-vote certificate for v.round − 1 (if any)
        v.tc          – a timeout certificate for v.round − 1 (if any)
+   σ_v – the source's signature on HASH(v), sent with v
    DAG_i[] – an array of sets of vertices (indexed by rounds)
-   blocksToPropose – a queue, initially empty, P_i enqueues valid blocks of transactions from clients
+   pendingTxs – transactions from clients not yet in a batch
    leaderStack ← initialize empty stack
+   q ← n − f                                         ▷ the quorum
+   Δ – minimum time between two proposals of P_i ;  lastProposal ← 0

 1: procedure path(v, u)       ▷ Check if exists a path of strong and weak edges in the DAG
 2:     return exists a sequence of k ∈ ℕ, vertices v_1, …, v_k s.t. v_1 = v, v_k = u,
            and ∀j ∈ [2, .., k] : v_j ∈ ⋃_{r≥1} DAG_i[r] ∧ v_j ∈ v_{j−1}.weakEdges ∪ v_{j−1}.strongEdges

 3: procedure strong_path(v, u)      ▷ Check if exists a path of only strong edges from v to u
 4:     return exists a sequence of k ∈ ℕ, vertices v_1, …, v_k s.t. v_1 = v, v_k = u,
            and ∀j ∈ [2, .., k] : v_j ∈ ⋃_{r≥1} DAG_i[r] ∧ v_j ∈ v_{j−1}.strongEdges

 5: procedure set_weak_edges(v, r)                    ▷ Add edges to orphan vertices
 6:     v.weakEdges ← {}
-    for r' = r − 2 down to 1 do
+7:     for r' = r − 2 down to max(1, r − GC) do         ▷ GC: garbage-collection depth
-        for every u ∈ DAG_i[r'] s.t. ¬path(v, u) do
+8:         for every u ∈ DAG_i[r'] s.t. ¬path(v, u) ∧ u ∉ deliveredVertices do
 9:             v.weakEdges ← v.weakEdges ∪ {u}

10: procedure get_vertex(p, r)
11:     if ∃v ∈ DAG_i[r] s.t. v.source = p then
12:         return v
13:     return ⊥

14: procedure get_leader_vertex(r)
15:     return get_vertex(L_r, r)

-    procedure a_bcast_i(b, r)
+16: procedure a_bcast_i(tx)
-        blocksToPropose.enqueue(b)
+17:     pendingTxs.append(tx)

+18: procedure make_batch()
+19:     B ← the first min(|pendingTxs|, maxBatch) transactions of pendingTxs
+20:     remove them from pendingTxs ;  return B

21: procedure broadcast_vertex(r)
+22:    B ← make_batch()
-        v ← create_new_vertex(r)
-        try_add_to_dag(v)
+23:    v ← create_new_vertex(r, B)
-        r_bcast_i(v, r)
+24:    p_bcast_i((r, P_i), v, B)                       ▷ PRBC, Figure 4

25: procedure order_vertices()
26:     while ¬leaderStack.isEmpty() do
27:         v ← leaderStack.pop()
28:         verticesToDeliver ← {v' ∈ ⋃_{r>0} DAG_i[r] | path(v, v') ∧ v' ∉ deliveredVertices}
-            for every v' ∈ verticesToDeliver in some deterministic order do
+29:        for every v' ∈ verticesToDeliver in order of (v'.round, v'.source) do
-                output a_deliver_i(v'.block, v'.round, v'.source)
+30:            output a_deliver_i(B_{v'}, v'.round, v'.source)   ▷ B_{v'}: the batch with digest v'.block
31:             deliveredVertices ← deliveredVertices ∪ {v'}
```

**Changes from Sailfish's Figure 1.**
- A vertex carries the 32-byte digest of its batch, not the batch (line `v.block`).
  The batch travels separately (Figure 4).
- A party builds its batch when it proposes (lines 18–20), from the transactions
  that arrived since its last proposal, at most `maxBatch`.
- The vertex is broadcast with PRBC, not reliable broadcast (line 24), and is not
  added to the DAG directly: it enters the DAG when certified, like every other
  vertex (Figure 2, lines 39–40).
- Weak edges reach back at most `GC` rounds and skip delivered vertices (lines 7–8).
- Histories are delivered in (round, source) order (line 29). A batch that is not
  yet held is output when it arrives (Figure 5).

---

## Figure 2 — DAG construction

```diff
Local variables:
-   round ← 1; buffer ← {}
    round ← 1
+   TC_r – q signed ⟨timeout, r⟩ messages ;  NV_r – signed ⟨no-vote, r⟩ messages received

+32: procedure valid(v)                                ▷ the vote rule, used by PRBC (Figure 4)
+33:     r ← v.round
+34:     return |v.strongEdges| ≥ q, from distinct sources
+35:         ∧ every u ∈ v.strongEdges is certified here, with u.round = r − 1
+36:         ∧ every u ∈ v.weakEdges is certified here, with r − GC ≤ u.round ≤ r − 2
+37:         ∧ (v.source ≠ L_r ∨ L_{r−1} ∈ sources(v.strongEdges) ∨ v.nvc has q valid ⟨no-vote, r − 1⟩)
+38:     ▷ a parent that is not certified here is asked for (Figure 5, line 137); v is checked again

-    upon r_deliver_i(v, r, p) do
-        if v.source = p ∧ v.round = r ∧ |v.StrongEdges| ≥ 2f + 1 ∧ is_valid(v) then
-            if ¬try_to_add_to_dag(v) then buffer ← buffer ∪ {v}
-            else for v' ∈ buffer : v'.round ≤ r do try_to_add_to_dag(v')
+39: upon p_certify_i((r, p), v) do                    ▷ q votes for v (Figure 4)
+40:     DAG_i[r] ← DAG_i[r] ∪ {v}
+41:     try_commit()                                   ▷ Figure 3

-    upon |DAG_i[r]| ≥ 2f + 1 ∧ (∃v' ∈ DAG_i[r] : v'.source = L_r ∨ TC_r is received) for r ≥ round do
+42: upon |DAG_i[r]| ≥ q ∧ (∃v' ∈ DAG_i[r] : v'.source = L_r ∨ TC_r is held) for r ≥ round do
+43:     wait until now ≥ lastProposal + Δ
44:      advance_round(r + 1)

45: upon timeout do
46:     multicast ⟨timeout, round − 1⟩_i
-    upon receiving f + 1 ⟨timeout, r⟩_* such that r ≥ round do
-        multicast ⟨timeout, r⟩_i
-    upon receiving TC_r such that r ≥ round do
-        multicast TC_r

+47: upon receiving q ⟨timeout, r⟩_* do
+48:     TC_r ← these q messages

-    procedure create_new_vertex(r)
+49: procedure create_new_vertex(r, B)
50:     v.round ← r
51:     v.source ← P_i
-        v.block ← blocksToPropose.dequeue()
+52:    v.block ← H(B)
53:     v.strongEdges ← DAG_i[r − 1]
54:     set_weak_edges(v, r)
55:     if ∄v' ∈ DAG_i[r − 1] : v'.source = L_{r−1} then
56:         v.tc ← TC_{r−1}
57:         if P_i = L_r then
58:             v.nvc ← NV_{r−1}
+59:    σ_v ← sign_i(⟨"vertex", HASH(v)⟩)
60:     return v
-    procedure try_to_add_to_dag(v)
-        if ∀v' ∈ v.strongEdges ∪ v.weakEdges : v' ∈ ⋃_{k≥1} DAG_i[k] then
-            DAG_i[v.round] ← DAG_i[v.round] ∪ {v}
-            if |DAG_i[v.round]| ≥ 2f + 1 then try_commit(v.round − 1, DAG_i[v.round])
-            buffer ← buffer \ {v} ;  return true
-        return false

61: procedure advance_round(r)
62:     if ∄v' ∈ DAG_i[r − 1] : v'.source = L_{r−1} then
63:         send ⟨no-vote, r − 1⟩_i to L_r
64:     if P_i = L_r then
-            wait until ∃v' ∈ DAG_i[r − 1] : v'.source = L_{r−1} or NVC_{r−1} is received
+65:        wait until ∃v' ∈ DAG_i[r − 1] : v'.source = L_{r−1} or q ⟨no-vote, r − 1⟩ are received
66:     round ← r ; start timer
+67:    lastProposal ← now
68:     broadcast_vertex(round)
```

**Changes from Sailfish's Figure 2.**
- **Validity moves into the broadcast.** Sailfish checks a delivered vertex
  (|strongEdges| ≥ 2f + 1, `is_valid`) and buffers it until its parents are in the
  DAG (its lines 29–35, 55–62). Here a correct party *votes* only for a vertex that
  passes `valid` (lines 32–38): q strong edges to distinct certified round-(r − 1)
  vertices, weak edges certified and inside the window, and a leader that skips the
  previous leader carries q no-votes. So every certified vertex is valid and its
  parents are certified, and a certified vertex enters the DAG at once (lines 39–41).
  There is no buffer.
- **The DAG is built from certificates** (line 39): a vertex counts once q parties
  voted for it, before its batch has arrived.
- **2f + 1 becomes q** (lines 34, 42, 47, 65).
- **Minimum gap Δ** between a party's proposals (lines 43, 67).
- **Timeouts.** A party sends its own timeout and forms TC_r from q timeouts
  (lines 45–48). Sailfish's other two timeout rules, multicasting a timeout after
  f + 1 others and forwarding a received TC (its lines 40–43), are not part of
  this protocol.
- The source signs its vertex (line 59).

---

## Figure 3 — Commit rule

```diff
Local variables:
    committedRound ← 0

-    upon receiving a set S of ≥ 2f + 1 first messages for round r + 1 vertices do
+69: upon p_certify_i((r + 1, ·), ·) or a vertex body arriving do   ▷ the vertices of round r + 1
-        try_commit(r, S)
+70:     try_commit()

-    procedure try_commit(r, S)
+71: procedure try_commit()
+72:     for r ← round − 1 down to committedRound + 1 do        ▷ the latest leader that commits directly
73:          v ← get_leader_vertex(r)
-        votes ← {v' ∈ S | strong_path(v', v)}
+74:         votes ← {v' ∈ DAG_i[r + 1] | v ∈ v'.strongEdges}
-        if votes ≥ 2f + 1 ∧ committedRound < r then
-            commit_leader(v)
+75:         if v ≠ ⊥ ∧ |votes| ≥ q then
+76:             if history_complete(v) then commit_leader(v)
+77:             return

78: procedure commit_leader(v)
79:     leaderStack.push(v)
80:     r ← v.round − 1
81:     v' ← v
82:     while r > committedRound do
83:         v_s ← get_leader_vertex(r)
84:         if v_s ≠ ⊥ ∧ strong_path(v', v_s) then
85:             leaderStack.push(v_s)
86:             v' ← v_s
87:         r ← r − 1
88:     committedRound ← v.round
89:     order_vertices()

+90: procedure history_complete(v)
+91:     return every u with path(v, u) ∧ u ∉ deliveredVertices is certified here
            and its vertex body is held      ▷ missing ones are fetched (Figure 5)
```

**Changes from Sailfish's Figure 3.**
- **What counts as support.** Sailfish commits L_r on 2f + 1 *first messages* of
  round r + 1 (the first message of each reliable broadcast). Here the support is
  q *certified* round-(r + 1) vertices with a strong edge to L_r (lines 74–75).
  A certificate costs one round trip after the vertex arrives, the same position
  the first message has in Sailfish.
- **The latest leader first** (line 72): `try_commit` looks for the latest round
  whose leader is directly supported, and the walk back (lines 78–89, Sailfish's own)
  orders the earlier leaders it has strong paths to and skips the rest.
- **No ordering with a gap** (lines 76, 90–91): a leader's history is ordered only
  once every vertex in it is certified and held. Batches may still arrive later.

---

## Figure 4 — PRBC broadcast

```diff
Local variables:
+   votes[τ, h] ← {}      ▷ signed votes for hash h in instance τ
+   voted[τ] ← ⊥           ▷ the one hash P_i voted for in τ
+   certified[τ] ← ⊥       ▷ the certified hash of τ
+   values[h], batches[d]  ▷ vertices by hash, batches by digest
+   S1(d) – the ⌈c√n⌉ parties selected by H(d ‖ "s1") ;  S2_i(d) – those selected by H(d ‖ "s2" ‖ i)

+92: procedure p_bcast_i(τ, v, B)
+93:     multicast ⟨batch, B⟩_i
+94:     multicast ⟨propose, v, σ_v⟩_i

+95: upon receiving ⟨batch, B⟩ with H(B) ∉ batches do
+96:     batches[H(B)] ← B
+97:     if P_i ∈ S1(H(B)) then send ⟨batch, B⟩ to S2_i(H(B))     ▷ one relay hop

+98: upon receiving ⟨propose, v, σ_v⟩ do
+99:     τ ← (v.round, v.source) ;  h ← HASH(v)
+100:    if σ_v is not v.source's signature on h then return
+101:    values[h] ← v
+102:    wait until batches[v.block] ≠ ⊥ ∧ valid(v)            ▷ hold B, check the vote rule (Fig. 2)
+103:    if voted[τ] ∉ {⊥, h} then return                       ▷ one vote per instance
+104:    voted[τ] ← h
+105:    if certified[τ] = ⊥ ∧ P_i ∈ S1(v.block) then send ⟨propose, v, σ_v⟩ to S2_i(v.block)
+106:    multicast ⟨vote, τ, h, sign_i(⟨"vote", τ, h⟩)⟩_i      ▷ also if τ is certified already

+107: upon receiving ⟨vote, τ, h, σ⟩_j with a valid σ do
+108:    votes[τ, h] ← votes[τ, h] ∪ {(j, σ)}
+109:    if |votes[τ, h]| ≥ q ∧ certified[τ] = ⊥ then
+110:        certified[τ] ← h
+111:        output p_certify_i(τ, h)
+112:        if values[h] = ⊥ ∨ batches[values[h].block] = ⊥ then  ▷ otherwise line 114 delivers at once
+113:            start_recovery(τ, h, voters of votes[τ, h])        ▷ Figure 5

+114: upon certified[τ] = h ∧ values[h] ≠ ⊥ ∧ batches[values[h].block] ≠ ⊥ for the first time do
+115:    output p_deliver_i(τ, values[h], batches[values[h].block])
```

**What the figure says.**
- **Two objects, one digest.** The batch and the vertex travel separately (lines 93–94).
  A relay layer chosen by the digest forwards each one hop (lines 97, 105). The
  consensus messages carry only h and d.
- **A vote is a promise to hold the data.** A correct party votes only when it holds
  the batch and the vertex passes the vote rule (line 102), once per instance
  (lines 103–104), and the vote signs the instance and the hash (line 106).
- **Certify, then deliver.** q votes certify (τ, h) (lines 109–111). The party
  delivers, once, when it also holds v and B (lines 114–115), and starts recovery
  if it does not (lines 112–113).
- **A party keeps voting after it certifies** (line 106): it may have certified from
  votes Byzantine parties sent to it alone, and the others may need its vote.

---

## Figure 5 — Recovery

```diff
+116: procedure start_recovery(τ, h, V)               ▷ V: the voters of the certificate
+117:    if values[h] = ⊥ then
+118:        fetch(⟨recovery, h⟩, V, until values[h] ≠ ⊥)
+119:    d ← values[h].block
+120:    if batches[d] = ⊥ then
+121:        wait T_rec                                ▷ the batch is usually still on its way
+122:        fetch(⟨batchRequest, d⟩, V, until batches[d] ≠ ⊥)

+123: procedure fetch(m, V, until done)
+124:    for pass ← 0, 1, 2, … do                    ▷ never gives up
+125:        for each p ∈ V \ {P_i} do
+126:            if done then return
+127:            send m to p
+128:            wait until done or T_rec · 2^min(pass, 3) has passed

+129: upon receiving ⟨recovery, h⟩ from p do
+130:    if P_i holds the vertex v with HASH(v) = h then send ⟨recoveryResp, v⟩ to p

+131: upon receiving ⟨batchRequest, d⟩ from p do
+132:    if P_i holds the batch B with H(B) = d then send ⟨batchResp, d, B⟩ to p

+133: upon receiving ⟨recoveryResp, v⟩ from a party asked, with HASH(v) = h do
+134:    values[h] ← v                                ▷ no signature: delivered, never voted for

+135: upon receiving ⟨batchResp, d, B⟩ from a party asked, with H(B) = d do
+136:    batches[d] ← B

+137: procedure want_certificate(h, hints)            ▷ a parent or history vertex not certified here
+138:    wait T_rec
+139:    for k ← 0, 1, 2, … until h is certified here do
+140:        send ⟨certRequest, h⟩ to one party of hints if k = 0, else to all parties
+141:        wait T_rec · 2^min(k + 1, 3)

+142: upon receiving ⟨certRequest, h⟩ from p do
+143:    if certified[τ] = h for some τ then send ⟨certificate, τ, h, votes[τ, h]⟩ to p

+144: upon receiving ⟨certificate, τ, h, C⟩ do
+145:    C ← the votes of C with a valid signature on ⟨"vote", τ, h⟩
+146:    if |C| ≥ q ∧ certified[τ] = ⊥ then votes[τ, h] ← C ;  handle as lines 109–113
```

**What the figure says.**
- **The requester checks everything itself** (lines 133, 135): an answer is kept
  only if it hashes to h, or to the digest d inside the vertex. So a responder needs
  no votes of its own (lines 129–132), and a wrong or missing answer only costs time.
- **Some voter always has the data.** At least q − f ≥ f + 1 voters are correct, and
  each stored the batch before voting (Figure 4, line 102). Correct parties keep
  delivered vertices and batches for R rounds, so asking every voter in turn
  (lines 124–128) reaches one that holds them.
- **Value first, then batch** (lines 117–122), each from the same voters, the batch
  after a wait T_rec because it normally arrives on its own.
- **Certificates travel** (lines 137–146): a party that sees a vertex it has not
  certified asks for its q signed votes, which anyone can check.

**Boundary.** Everything above assumes a correct party is less than R rounds behind
the others (R = 50 by default, like Narwhal's `gc_depth`); a party further behind
needs state transfer, which is not part of the protocol.
