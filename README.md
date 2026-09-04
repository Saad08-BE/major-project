# Local Privacy-Based Healthcare Intelligence System

A privacy-first, local-only healthcare RAG project for academic demonstration.
It will search the supplied healthcare dataset and local PDF documents, retrieve
relevant evidence, and use Ollama running on the same computer to draft a
grounded response with sources. It is not a diagnostic or clinical decision
system, and patient-record search is intentionally excluded.

## Privacy boundary

- Healthcare CSV files, uploaded documents, embeddings, indexes, logs, and LLM
  prompts stay on this computer.
- The application accepts only a loopback (`localhost`/`127.0.0.1`/`::1`)
  Ollama endpoint. It has no cloud LLM or cloud fallback.
- Raw data belongs in `data/raw/` and is ignored by Git. The application will
  not modify it.
- Derived local artifacts will be stored in `data/processed/`,
  `data/documents/`, and `vector_store/`, which are also ignored by Git.

Installing Python packages and downloading a model are separate setup actions
that may require an internet connection. They are not used to send runtime
healthcare data anywhere.

## Phase 1 setup

Use Python 3.11 or later:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m unittest discover
streamlit run app/main.py
```

The web shell runs locally on `127.0.0.1:8501` by default. It does not call
Ollama during Phase 1. Future phases will add dataset profiling, retrieval, PDF
ingestion, and local generation.

## Local model plan

The configurable default is `qwen2.5:3b`, a compact local instruct model suited
to exploratory use on an M1 MacBook Air with 8 GB unified memory. It still uses
several GB while running, so retrieval will remain usable when it is stopped.
The final model choice will be benchmarked on this machine before claims about
latency or answer quality are made.

The default local embedding model is `sentence-transformers/all-MiniLM-L6-v2`
(384 dimensions). Its initial download is a setup step; embedding runs locally
afterward.

## Project layout

```text
app/config/      Local configuration and path policy
app/safety/      Input validation and healthcare disclosure
app/llm/         Local Ollama adapter (no cloud fallback)
app/ui/          Streamlit UI components
data/raw/        Original supplied dataset (not committed)
data/processed/  Derived datasets (not committed)
vector_store/    Local indexes (not committed)
tests/           Foundation tests
```

## Development checks

```bash
python3 -m unittest discover
python3 -c 'import ast, pathlib; [ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for path in pathlib.Path("app").rglob("*.py")]'
```

Phase 2 will profile `data/raw/Indian_healthcare.csv` without editing it and
will document fields suitable for structured filters versus semantic retrieval.
