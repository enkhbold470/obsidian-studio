# Architecture (CLI-only)

## Overview

```mermaid
flowchart LR
  cli[core.cli]
  pipe[brainrot.run_pipeline]
  disk[temp_build_and_output]
  cli --> pipe
  pipe --> disk
```

- **`core/brainrot.py`** — dialogue, TTS, FFmpeg; writes under `temp_build/` and your `--output` path.
- **`core/cli.py`** — argparse entry; loads `.env` and calls `run_pipeline`.

There is no database, object storage, or web API in this repository.
