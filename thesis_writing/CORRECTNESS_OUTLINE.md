# Correctness outline — PRBC (chapter 4) and PRBC-Sailfish (chapter 5)

Source material for section 4.8 (*Outline of Correctness Proofs*: 4.8.1
Safety, 4.8.2 Liveness) and for the correctness outline in chapter 5. Proof
sketches at the level of an outline: lemma, short proof, theorem. "Line N"
always means a line of `PSEUDOCODE_PAPER.md`, the five figures in the style of
the Sailfish paper that chapters 4 and 5 show. The detailed, code-referenced
`PSEUDOCODE.md` is cited only in the implementation notes at the end.

## How to use this file

- **Two separate sets of lemmas.** Part A proves properties of PRBC alone and
  never mentions leaders, edges, the DAG or ordering. Part B proves
  PRBC-Sailfish and uses Part A only through Theorems 4.4 and 4.7 and
  Lemma 4.2, as a black box. This is how DAG-Rider and Sailfish use reliable
  broadcast, and how Tusk uses Narwhal.
- **One link between them:** an external validity predicate `valid(v)`.
  Part A leaves it abstract; Part B sets it to the DAG rule (Figure 2,
  lines 32–38). (The idea of an external validity predicate is from Cachin,
  Kursawe, Petzold and Shoup, 2001.)
- **Prove the protocol of `PSEUDOCODE_PAPER.md`.** It is the implemented
  protocol, written at the paper's level; `PSEUDOCODE.md` shows how the code
  realises each line.
- Add no numbers or results. Keep the outline style: statement, short proof.

## Model (state once at the start of 4.8; chapter 5 refers back)

- **Parties.** n parties, at most f Byzantine, n ≥ 3f + 1, static corruption.
  Quorum q = n − f, which is 2f + 1 when n = 3f + 1.
- **Counting facts** used throughout:
  - (F1) any q parties include at least q − f ≥ f + 1 correct ones;
  - (F2) any two sets of q parties share at least 2q − n ≥ f + 1 parties, so
    at least one correct party;
  - (F3) at least n − f = q parties are correct, so they alone can form a quorum.
- **Cryptography.** A PKI; signatures cannot be forged; the hash (SHA-256) is
  collision resistant. Every statement holds except with the negligible
  probability of a forgery or collision. That is the only probability in the
  safety argument.
- **Network.** Authenticated point-to-point links; every message between
  correct parties is eventually delivered. Partial synchrony: after an
  unknown time GST, every such message arrives within δ.
- **Retention.** No correct party falls more than R rounds behind the others
  (R = `RETENTION_ROUNDS`). A party further behind would need state transfer,
  which is not implemented; Narwhal has the same boundary (its `gc_depth`).
- **Signatures on** (`PRBC_SIGS`, the default). With them off the protocol is
  not Byzantine fault tolerant; claim nothing for that mode, nor for
  `REDUCED_QUORUM`.

---

# Part A — PRBC (chapter 4, section 4.8)

## A.1 The primitive

Each instance has a **tag** τ = (r, s): round r, sender s. The sender calls
`p_bcast(τ, v, B)` (line 92), where B is a batch and v a value (in chapter 5,
a vertex) that carries the digest d = H(B) and its own tag (v.round = r,
v.source = s).

A party **certifies** (τ, h) when it holds a **certificate**: q votes for
(τ, h) from distinct parties, each a valid signature over ⟨"vote", τ, h⟩
(lines 106–107). A certificate is held whether its votes arrived one by one
(lines 108–111) or together, forwarded by another party (lines 144–146).

A party **delivers** (τ, v, B) when it has certified (τ, h) and holds v with
HASH(v) = h and B with H(B) = v.block (lines 114–115).

`valid(v)` is an **external validity predicate**, evaluated locally. Assume it
is eventually stable: once true at a correct party it stays true. A party
whose check fails for now keeps the value and checks again (line 102).

**Rules a correct party follows.** The lemmas use only these.

- **(C1) Sender.** A correct sender signs exactly one value per tag and sends
  v with its signature, and B, to every party (lines 21–24, 59, 93–94).
- **(C2) One vote per tag.** A correct party votes at most once per tag
  (lines 103–104).
- **(C3) Vote preconditions.** It votes for (τ, h) only for a v with
  HASH(v) = h and tag τ, both taken from v itself (line 99); with a valid
  signature of v.source (line 100); with B stored and H(B) = v.block
  (lines 96, 102); and with `valid(v)` true (line 102).
- **(C4) Holding.** A correct voter keeps v and B while τ is inside the
  retention window (Figure 5, boundary note).
- **(C5) Recovery.** Figure 5, lines 116–136.
- **(C6) Voting does not stop at certification.** A party that certifies τ
  before it votes delivers, and still votes once (C3) holds for the value
  the sender signed: nothing in lines 98–106 depends on τ being certified
  (line 106). A copy fetched by recovery carries no signature and is never
  voted for (line 134); the sender's own copy is.

## A.2 Safety (4.8.1)

**Lemma 4.1 (one certificate per tag).** For every tag τ, a certificate
exists for at most one hash.

*Proof.* Suppose certificates exist for (τ, h) and (τ, h′) with h ≠ h′. By
(F2) their voters share a correct party c. Signatures cannot be forged, and
each covers the tag together with the hash, so c signed votes for both. This
contradicts (C2). ∎

*Remark for the text.* Binding the tag into the signed bytes is essential: a
signature over h alone could be presented as a vote for a different tag.

**Lemma 4.2 (a certificate has f + 1 correct witnesses).** If a certificate
for (τ, h) exists, at least f + 1 correct parties voted for (τ, h). When it
voted, each held a value v with HASH(v) = h and tag τ, signed by its sender;
held B with H(B) = v.block; and found `valid(v)` true.

*Proof.* (F1) and (C3). ∎

**Lemma 4.3 (integrity).** If a correct party delivers (τ, v, B), then
(a) HASH(v) = h, the unique certified hash of τ, and v has tag τ;
(b) H(B) = v.block;
(c) if the sender is correct, v is the value it signed for τ and B its batch;
(d) the party delivers at most once for τ.

*Proof.* (a) A value is stored under the hash computed from it (lines 99,
133), and delivery takes the value stored under the certified hash
(line 114). By Lemma 4.2 a correct voter held a value with this hash and tag
τ; by collision resistance it is v. (b) A batch is stored under its own
digest (lines 96, 136). (c) By Lemma 4.2 a correct voter verified the
sender's signature over h; a correct sender signs one value per tag (C1), so
h is that value's hash, and B is its batch by (b). (d) Delivery happens only
the first time its condition holds (line 114), and certified[τ] is set once
(line 109). ∎

**Theorem 4.4 (PRBC safety: agreement and integrity).** For every tag, all
correct parties that deliver, deliver the same (v, B); if the sender is
correct, it is the sender's.

*Proof.* Lemma 4.1 leaves one hash; Lemma 4.3(a, b) and collision resistance
give the same v and B; Lemma 4.3(c) gives the second part. ∎

*Remark: sampling plays no part in safety.* No step uses the relay sets S1
and S2 (lines 97, 105). They decide only who receives a copy first, and
every copy is checked against h or d. Safety is therefore deterministic (up
to a forgery or collision), not "with high probability".

## A.3 Liveness (4.8.2)

After GST, within the retention bound.

**Lemma 4.5 (availability).** If a correct party p certifies (τ, h), p
eventually delivers (τ, v, B).

*Proof.* If p already holds v and B, it delivers at once (line 114).
Otherwise it starts recovery with the certificate's voters as candidates
(lines 112–113). By Lemma 4.2 at least f + 1 of them are correct and held v
and B, which they keep (C4) and send to anyone who asks, with no other
condition (lines 129–132). p asks one candidate at a time and, after a pass
with no valid answer, starts again with a longer wait (lines 123–128), so it
asks every candidate again and again; it keeps a late answer from anyone it
asked (lines 133, 135). After GST some correct candidate's answer arrives. A
wrong answer is never kept, since p checks it against h or the digest d
(lines 133, 135); it only costs time. The value is fetched first, then the
batch (lines 117–122). ∎

**Lemma 4.6 (validity).** If the sender is correct and `valid(v)` eventually
holds at every correct party, every correct party delivers (τ, v, B).

*Proof.* By (C1) every correct party receives B and v with its signature, and
both checks pass (lines 96, 100). Take a correct p. Once `valid(v)` holds,
all of (C3) holds. p has voted for no other value of τ, since it votes only
for values signed by the sender (C3) and a correct sender signed only v (C1);
so p votes and sends its vote to every party (line 106). This holds even if p
certified (τ, h) before it could vote, for instance from Byzantine votes sent
to p alone: p then delivers at once and still votes (C6). So all correct
parties vote, at least q of them (F3), and every correct party collects q
votes for (τ, h), certifies, and, holding v and B, delivers. ∎

*Remark for the text.* (C6) is what this proof needs. A party that stopped
at certification would withhold its vote, and if Byzantine parties sent
their votes only to it, every other correct party could stay one vote short.

**Theorem 4.7 (PRBC liveness).**
(a) *Validity:* Lemma 4.6.
(b) *Transferable totality:* if a certificate for (τ, h) exists, every
correct party that obtains it delivers (τ, v, B). A certificate is q signed
votes, so anyone can forward it and anyone can check it (lines 142–146).

*Proof.* (b) A correct party that obtains it has certified (τ, h); apply
Lemma 4.5. ∎

*Remark: what PRBC does not give by itself.* Classic reliable-broadcast
totality, "if one correct party delivers, all do", does not hold for PRBC
alone. With a Byzantine sender, which may send v to only some parties,
Byzantine voters can send their votes to only some correct parties, so one
correct party may certify while another never sees q votes. (With a correct
sender every correct party votes, so this cannot happen: Lemma 4.6.) PRBC
replaces totality with certificates that can be passed on; the protocol built
on PRBC must make them travel. PRBC-Sailfish does (Lemma 5.2).

*Remark: where the probability is.* The relay sets decide how often a party
certifies a value before it holds v and B, that is, how often Lemma 4.5 must
fetch over the network. This is the quantity the hypergeometric model in
`RECOVERY_TESTING.md` predicts. It changes the cost, not the guarantees. The
sets are derived from the batch digest, so a Byzantine sender can steer them
by choosing its batch; this too changes only the cost.

---

# Part B — PRBC-Sailfish (chapter 5)

## B.1 Setup

- In every round r, each party s PRBC-broadcasts its vertex under tag (r, s)
  (lines 21–24). Strong edges, weak edges and the no-vote certificate are
  fields of the vertex (Figure 1).
- `valid(v)` is the vote rule of Figure 2 (lines 32–37). Certificates are
  never discarded within the window, so it is eventually stable; a parent
  not yet certified is asked for (line 38) and the vertex checked again
  (line 102).
- By Lemma 4.1 each slot (r, s) has at most one certified vertex: *the*
  vertex of the slot. G is the set of all certified vertices, a global DAG
  used only in the proofs. L_r is the vertex of slot (r, L_r's party), if any.
- A party **directly commits** L_r when q certified round-(r+1) vertices have
  a strong edge to L_r (lines 74–75). `try_commit` takes the latest directly
  committed leader as the **anchor** (line 72), walks back from it and orders
  the leaders it reaches, oldest first (lines 78–89). A party's **log** is the
  sequence of vertices output by `order_vertices` (lines 25–31).
- From chapter 4 only Theorems 4.4 and 4.7 and Lemma 4.2 are used.

## B.2 The DAG

**Lemma 5.1 (the certified DAG is well formed).** Let v ∈ G be of round
r ≥ 2.
(a) v has strong edges to the vertices of at least q distinct round-(r − 1)
slots, all in G;
(b) each weak edge of v is a vertex of G of a round between
max(1, r − GC) and r − 2;
(c) if v is the leader's vertex and has no strong edge to L_{r−1}, it carries
q valid no-votes for round r − 1.
A round-1 vertex points to genesis only.

*Proof.* By Lemma 4.2 a correct party voted for v with `valid(v)` true,
which checks (a)–(c) against that party's certificates (lines 34–37). By
Lemma 4.1 those certificates are the same at every party. ∎

*Corollary.* Every parent of a vertex in G is in G: G is closed under edges.

**Lemma 5.2 (certificates travel).** Let a correct party p hold a vertex
u ∈ G, and let h be an edge of u. If p asks for h's certificate (line 38 or
91), p eventually certifies h.

*Proof.* By Lemma 4.2 at least f + 1 correct parties voted for u with
`valid(u)` true, so each held a certificate for h (lines 35–36). They keep
it within the retention window, which is longer than how far below u a
parent can lie (the GC window, lines 7, 36). p first asks one party that
referenced h, then everyone, with doubling waits (lines 137–141). A correct
holder answers with its q votes (lines 142–143), which p checks and adopts
(lines 144–146). If the votes reach p by themselves first, p stops asking
(line 139). ∎

*Remark for the text.* This is the step where Sailfish's proof relies on
reliable-broadcast totality. Here a certificate travels because a certified
vertex references it, and only referenced vertices are ever ordered, so this
weaker form is enough.

**Lemma 5.3 (correct vertices become valid everywhere).** After GST, if a
correct party s creates a vertex v for round r, then `valid(v)` eventually
holds at every correct party, so (Lemma 4.6) every correct party delivers v.

*Proof.* s built v from its own certificates. Its strong edges are all its
certified round-(r − 1) vertices (line 53), at least q, since s advanced
only with q of them (line 42). Its weak edges are certified and inside the
window (lines 5–9, 54). If s leads round r without L_{r−1}, v carries q
no-votes s received (lines 55–58, 65). So a correct party finds v valid once
it has certified v's parents. For each parent it lacks, it asks, with s and
the party it got v from as hints (line 38). s holds that certificate, so the
party certifies the parent and checks v again (line 102). ∎

## B.3 Safety

**Lemma 5.4 (no-vote lemma).** If a correct party directly commits L_r, then
L_{r+1}, if it exists, has a strong edge to L_r.

*Proof.* Let D be the q certified round-(r+1) vertices with a strong edge to
L_r that the party counted. Suppose L_{r+1} has no strong edge to L_r. By
Lemma 5.1(c) it carries q no-votes for round r. The sources of D and the
signers of those no-votes share a correct party c (F2). The vertex of c's
slot in D is c's own (Theorem 4.4), and it points to L_r. But a correct party
sends a no-vote for round r only when L_r is not in its DAG as it enters
round r + 1 (lines 62–63), and then its round-(r+1) vertex, built from the
same DAG, does not point to L_r (line 53); as the leader of round r + 1 it
puts no-votes into its vertex only when that vertex does not point to L_r
(lines 55–58). Contradiction. ∎

**Lemma 5.5 (path lemma).** If a correct party directly commits L_r, every
vertex of G of round r + 2 or later has a strong path to L_r.

*Proof.* By induction on the round r′. For r′ = r + 2: such a vertex has
strong edges to q round-(r+1) slots (Lemma 5.1(a)) and D covers q slots, so
by (F2) they share a slot, and by Lemma 4.1 the same vertex, which points to
L_r. For r′ > r + 2: the vertex has a strong edge into round r′ − 1, whose
vertex has a path by induction. ∎

*Corollary 5.6.* If a correct party directly commits L_r, every leader vertex
of G of a later round has a strong path to L_r (Lemma 5.4 for round r + 1,
Lemma 5.5 beyond).

**Lemma 5.7 (every correct party decides every leader the same way).** For
every round r, if one correct party orders L_r, every correct party whose log
reaches round r orders it too; if one skips round r, so do the others.

*Proof sketch.*
(i) *The walk back is deterministic.* It reads only the edges of vertices in
the anchor's history and the certified leader vertices (lines 82–87).
Line 76 guarantees that every vertex of that history is certified locally
and its edges are known; edges are fixed by the hash. Whether a leader joins
the chain is therefore the same computation at every party; a leader that is
not certified, or not reached, is skipped by everyone.
(ii) Let p and p′ decide round r while walking back from anchors a and a′,
with a's round no higher than a′'s. If the rounds are equal, a = a′ (one
vertex per slot) and (i) applies. Otherwise p directly committed a, so by
Corollary 5.6 every leader vertex of a later round has a strong path to a. So
p′'s walk reaches a and continues from it, exactly like p's walk below a, and
by (i) both decide round r the same way. ∎

**Lemma 5.8 (same history, same order).** Two correct parties that order the
same leaders in the same order produce the same log.

*Proof.* For a leader ℓ, `order_vertices` outputs the vertices reachable from
ℓ that earlier leaders did not output, sorted by (round, source)
(lines 28–29). By induction over the leaders, the already-output sets agree;
the reachable sets agree because the history is complete (line 76; every
leader of the chain lies in the anchor's history) and edges are fixed by
hashes. ∎

**Theorem 5.9 (consistency).** The logs of any two correct parties are
prefixes of each other. Since each slot carries the same batch everywhere
(Theorem 4.4), applying the logs' batches in order gives the same transaction
sequence everywhere.

*Proof.* Lemmas 5.7 and 5.8. ∎

## B.4 Liveness

**Timeout condition.** After GST, the round timeout τ (`ROUND_TIMEOUT_MS`)
exceeds the time from the first correct party entering a round to a correct
leader's vertex of that round being certified at every correct party. That is
the minimum gap Δ between a party's proposals (line 43) plus a few δ, plus
T_rec + 2δ if a parent certificate has to be fetched. Sailfish needs a
timeout condition of the same kind. (In the experiments τ = 500 ms and
Δ ≤ 100 ms.)

**Lemma 5.10 (rounds advance).** After GST every correct party enters every
round.

*Proof.* By induction on r. Suppose every correct party has proposed in round
r. Each certifies all n − f ≥ q correct round-r vertices (Lemma 5.3), so the
first condition of line 42 holds. Two cases.
- *Some correct party's round-(r+1) vertex points to L_r.* That vertex reaches
  every correct party (Lemma 5.3), whose check asks for L_r's certificate
  (line 38), so every correct party certifies L_r (Lemma 5.2) and advances
  (line 42).
- *No correct party's round-(r+1) vertex points to L_r.* Then all of them
  time out (line 45); the q correct timeouts form a timeout certificate
  (lines 47–48) and every correct party advances (line 42). The leader of
  round r + 1 also needs q no-votes: every correct party's vertex skips L_r,
  so all correct parties, at least q, send it a no-vote (lines 62–63) and it
  advances (line 65). ∎

**Lemma 5.11 (correct leaders are committed).** After GST, if the leader of
round r is correct, every correct party eventually orders L_r.

*Proof.* By the timeout condition every correct party certifies L_r before
timing out, so its round-(r+1) vertex points to L_r (lines 42, 53). Every
correct party certifies these n − f ≥ q vertices and holds them (Lemma 5.3),
so L_r has q votes in the sense of lines 74–75. `try_commit` then finds an
anchor of round r or later; if it is not L_r, its walk back reaches L_r by
Corollary 5.6. The anchor's history becomes complete (Lemma 5.12), so the
commit happens. ∎

**Lemma 5.12 (histories become complete).** If a correct party has an anchor
candidate, `history_complete` eventually holds for it.

*Proof.* Every vertex in the history is in G (Corollary of Lemma 5.1). A hash
not certified locally is asked for (line 91) and certified (Lemma 5.2); a
certified vertex whose body is missing is recovered (Lemma 4.5). The history
is finite. ∎

**Theorem 5.13 (liveness).** After GST:
(a) *ordering never stops.* Leaders rotate, so any f + 1 consecutive rounds
include a correct leader, which is ordered (Lemma 5.11); a faulty leader is
skipped by the next anchor's walk back;
(b) *every correct party's batch is ordered.* Its vertex is certified by every
correct party (Lemma 5.3). A correct leader that creates a vertex after
certifying it either reaches it through strong edges, or has already ordered
it, or adds it as a weak edge (lines 5–9, 53–54). That leader is ordered
(Lemma 5.11), so the vertex is in every correct party's log, and its batch
arrives (Lemma 4.5).

*Proof.* As sketched in (a) and (b). ∎

---

## Implementation notes to state in the text (chapter 6)

These refer to the detailed `PSEUDOCODE.md`.

1. **Execution order.** The prototype counts a batch as executed when it
   arrives (`PSEUDOCODE.md` lines 114–117, 225–229), which can be out of log
   order. It does not execute transactions, so no state can diverge. A real
   executor applies batches in log order and waits for a missing one, which
   Lemma 4.5 bounds. Theorem 5.9 is about the log.
2. **Timeout certificates are carried, not checked** (`PSEUDOCODE.md`
   line 150). Safety does not use them: skipping a leader rests on the
   no-vote certificate, which is checked (`PSEUDOCODE.md` lines 174–179).
3. **The record of votes is finite.** A party keeps its votes for 128 rounds
   and refuses to vote for a tag older than that (`PSEUDOCODE.md` lines 161,
   216), so (C2) holds although the record is pruned.
4. **Late votes are dropped unchecked.** A vote for a tag the party has
   already certified is dropped before its signature is checked
   (`PSEUDOCODE.md` line 80). It changes nothing above: once a party has
   certified (τ, h), further votes for τ have no effect on it, and other
   parties still receive every vote.
5. **Retention bound and no state transfer**, as in the model.

## Do not claim

- Probabilistic safety ("with high probability"). Safety is deterministic up
  to cryptographic failure; the sampling affects cost only.
- Classic reliable-broadcast totality for PRBC alone (see the remark after
  Theorem 4.7).
- Anything for `PRBC_SIGS=off` or `REDUCED_QUORUM`.
- A concrete latency bound in δ. The timeout condition is stated
  qualitatively; deriving exact constants would need a careful analysis of
  round entry times that this outline does not do.
