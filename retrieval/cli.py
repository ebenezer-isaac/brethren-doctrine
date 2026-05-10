"""One-shot retrieval CLI per docs/TIER_2_SPEC.md §11 Step 3 done-state.

Usage:
    uv run python -m retrieval.cli "what do the notes say about communion?"
    uv run python -m retrieval.cli "Romans 6:1-4 baptism" --k 5 --no-rerank
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import typer
import voyageai
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from rich.console import Console

from retrieval.envelope import apply_boost, build_envelope
from retrieval.hybrid import DEFAULT_FUSED_K, hybrid_search
from retrieval.rerank import rerank as rerank_hits
from retrieval.router import route

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def search(
    query: str = typer.Argument(..., help="Free-text query"),
    k: int = typer.Option(10, "--k", "-k", help="Number of results to return after rerank"),
    fused_k: int = typer.Option(DEFAULT_FUSED_K, "--fused-k", help="Candidates after RRF fusion"),
    rerank: bool = typer.Option(True, "--rerank/--no-rerank", help="Apply BGE cross-encoder rerank"),
    boost: bool = typer.Option(True, "--boost/--no-boost", help="Apply authority post-boost (Stage 4)"),
    pretty: bool = typer.Option(True, "--pretty/--json-only", help="Print rich summary or just JSON"),
):
    """Run hybrid retrieval on the brethren-doctrine corpus and print the §5 envelope."""
    started = time.time()

    routing = route(query)
    console.print(
        f"[dim]intent={routing.intent}  bm25_w={routing.bm25_w}  dense_w={routing.dense_w}  "
        f"use_graph={routing.use_graph}[/dim]"
    )

    qc = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6433"), prefer_grpc=False)
    vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    sp = SparseTextEmbedding(model_name="Qdrant/bm25")

    fused = hybrid_search(qc, vo, sp, query, routing, fused_k=fused_k)

    if rerank:
        ranked = rerank_hits(query, fused, top_n=k)
    else:
        ranked = fused[:k]

    if boost:
        ranked = apply_boost(ranked)

    elapsed_ms = (time.time() - started) * 1000.0
    envelope = build_envelope(ranked, total_candidates=len(fused), elapsed_ms=elapsed_ms, intent=routing.intent)

    if pretty:
        _print_pretty(envelope)
        console.print()
        console.print(f"[dim]elapsed: {envelope['meta']['elapsed_ms']} ms[/dim]")
    else:
        sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2))


def _print_pretty(envelope: dict) -> None:
    console.print(f"[bold]Status[/bold]: {envelope['status']}    "
                  f"[bold]Returned[/bold]: {envelope['pagination']['returned']}/{envelope['pagination']['total']}")
    for i, item in enumerate(envelope["answer_context"], 1):
        console.print()
        console.print(
            f"[bold cyan]{i}.[/bold cyan] "
            f"[yellow]{item['source_doc']}[/yellow]"
            f"  [dim]({item['source_type']}, authority={item['authority_level']}, "
            f"type={item['chunk_type']}, score={item['score']})[/dim]"
        )
        text = item["text"]
        snippet = text if len(text) <= 360 else text[:360] + "..."
        console.print(f"  {snippet}")
        if item["scripture_refs"]:
            console.print(f"  [dim]refs: {', '.join(item['scripture_refs'][:6])}[/dim]")
        console.print(f"  [dim]{item['citations'][0]}[/dim]")


if __name__ == "__main__":
    app()
