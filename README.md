# APRBC-Sailfish

Benchmarking code for a thesis on DAG-based Byzantine fault-tolerant consensus.
It compares **APRBC-Sailfish** with Sailfish (payload carried inline in the
vertices) and with the Narwhal-based Sailfish baseline.

In APRBC-Sailfish the consensus path carries only 32-byte batch digests. Batches
travel separately, on their own connection, and a process votes on a digest
without waiting for the batch. A recovery protocol fetches any vertex or batch a
process is missing. In the code the protocol is called PRBC-Sailfish
(`prbc_sailfish`).

## Repository layout

```
Cargo.toml              Rust workspace (shared, sparse_bullshark)
shared/                 environment and key loading, node list, transaction generator
  nodes.csv             local committee: id,host,port,behavior
  public_keys.toml      public keys of all nodes
sparse_bullshark/       the node binary
  src/main.rs           picks the protocol from the PROTOCOL variable
  src/consensus/        prbc_sailfish.rs, sailfish.rs, rbc/ (Bracha, signed vote),
                        dag.rs, mempool.rs; bullshark.rs and sparse_bullshark.rs
                        are the earlier Bullshark variants
  src/network/          wire messages
  src/types/            vertex, timeout and no-vote certificates
  src/utils/metrics.rs  CPU, memory and network meters
scripts/
  local/                run_linux.py (all nodes on one machine), bench.py, run_sparse.ps1
  cluster/              run_distributed.py, run_cluster.py, setup_cluster.sh,
                        setup_keys.sh, monitor_cluster.py
  plots/                figure scripts
docs/                   runbook and experiment logs
thesis_writing/         results, pseudocode and correctness notes for the thesis
```

## Build

Needs a recent stable Rust toolchain.

```bash
cargo build --release
```

This produces `target/release/sparse_bullshark`. The binary reads
`./shared/nodes.csv` and `./shared/public_keys.toml` from its working
directory, so nodes run from the repository root. The scripts handle this
themselves, so they work from any directory.

## Keys

Each node signs its messages with an Ed25519 key. The scripts read the private
keys from a file named `keys` at the repository root, one line per node in node
order (`<private key, base64>:<public key, base64>`). The public halves must
match `shared/public_keys.toml`.

**The `keys` file is not in this repository.** To run the code, contact the
author and they will send it to you.

## Running

### All nodes on one machine (Linux)

The committee is `shared/nodes.csv` (7 nodes on localhost by default).

```bash
python3 scripts/local/run_linux.py --tx-size 512 --n-tx 500 --mode prbc_sailfish --input-rate 20000
python3 scripts/local/run_linux.py --tx-size 512 --n-tx 500 --mode sailfish --rbc signed_vote
```

Each run lasts 60 seconds. It prints one `CONFIG` and one `RESULTS` block,
each metric being the median across nodes: throughput, consensus and
end-to-end latency, rounds per second, CPU, memory and network. `--help` lists
every option. To run a list of experiments in sequence, edit `EXPERIMENTS` in
`scripts/local/bench.py` and run it.

### On a cluster

On the orchestrating machine, after building:

```bash
bash scripts/cluster/setup_cluster.sh     # writes shared/nodes_distributed.csv and copies binary, keys and config to every machine
python3 scripts/cluster/run_distributed.py --tx-size 512 --n-tx 500 --mode prbc_sailfish --n-nodes 10 --input-rate 20000
```

The machine list is at the top of `setup_cluster.sh`. The script assumes the
same user and SSH key on every machine. `docs/RUNBOOK.md` covers the full
cluster procedure: WAN emulation with `tc netem`, cleanup between runs, and
resource monitoring with `monitor_cluster.py`.

### Protocols and options

| Setting | Values |
|---|---|
| `--mode` / `PROTOCOL` | `prbc_sailfish` (APRBC-Sailfish), `sailfish`. The binary also accepts `sparse` and `dense` (earlier Bullshark variants) |
| `--rbc` | `signed_vote` or `bracha`, reliable broadcast for `sailfish` |
| `--mempool decoupled` | Sailfish with digests instead of inline payload |
| `--input-rate` | offered load in tx/s across the whole committee (0 = unlimited) |
| `--timeout` | round timeout in ms (default 500) |

### Faults

The `behavior` column of the node list sets each node's behaviour. `ok` is
correct. The faulty behaviours are:

| Value | Behaviour |
|---|---|
| `silent` | never proposes |
| `byz1` | sends its proposal to only 2f+1 peers |
| `byz2` | forwards a fake payload |
| `byz3` | sends its batch to only 2f+1 peers |
| `byz4` | never answers recovery requests |
| `byz5` | `byz1`, and also sends its votes to only 2f+1 peers |

## Baseline

The Narwhal-based Sailfish baseline is a separate code base,
[nibeshrestha/sailfish](https://github.com/nibeshrestha/sailfish), run with its
own benchmark harness. `docs/RUNBOOK.md` gives the settings used.
