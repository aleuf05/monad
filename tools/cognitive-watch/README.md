# Cognitive Watch

`CURRENT WATCH` remains canonical for the present. Cognitive Watch is a
disposable, read-only Qdrant projection that helps a Captain locate relevant
source artifacts from a small curator-approved corpus.

Use the isolated runtime:

```bash
/home/cgl/.cache/monad-cognitive-watch/bin/python tools/cognitive-watch/watch.py index
/home/cgl/.cache/monad-cognitive-watch/bin/python tools/cognitive-watch/watch.py find "how does Captain succession work?"
```

Every result carries its source path, Git commit, hash, heading, and class.
Read the source before treating a result as current or authoritative. The
watch does not ingest chat transcripts, write Canon, synthesize Current Watch,
or run as a daemon.
