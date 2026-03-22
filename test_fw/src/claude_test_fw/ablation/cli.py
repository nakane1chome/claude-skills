"""CLI entry point for the semantic ablation detector."""

from __future__ import annotations

from pathlib import Path

import click

from .chunker import chunk_markdown
from .embedder import TfidfEmbedder
from .matcher import greedy_match
from .scorer import score_document
from .reporter import report_terminal, report_json, report_markdown


@click.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--mode",
    type=click.Choice(["expand", "preserve", "compress"]),
    default="preserve",
    help="Expected transformation mode (affects thresholds).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json", "markdown"]),
    default="terminal",
    help="Output format.",
)
@click.option(
    "--threshold",
    type=float,
    default=0.1,
    help="Minimum cosine similarity for a concept match.",
)
@click.option(
    "--backend",
    type=click.Choice(["tfidf"]),
    default="tfidf",
    help="Embedding backend.",
)
def main(
    input_file: Path,
    output_file: Path,
    mode: str,
    output_format: str,
    threshold: float,
    backend: str,
) -> None:
    """Compare INPUT_FILE and OUTPUT_FILE for semantic ablation.

    Detects whether an AI editing pass preserved meaning while flattening
    vocabulary — the signature of semantic ablation.
    """
    input_text = input_file.read_text(encoding="utf-8")
    output_text = output_file.read_text(encoding="utf-8")

    # Chunk both documents
    input_units = chunk_markdown(input_text)
    output_units = chunk_markdown(output_text)

    if not input_units:
        click.echo("Error: no concept units found in input file.", err=True)
        raise SystemExit(1)
    if not output_units:
        click.echo("Error: no concept units found in output file.", err=True)
        raise SystemExit(1)

    # Embed
    embedder = TfidfEmbedder()
    all_texts = [u.text for u in input_units] + [u.text for u in output_units]
    embedder.fit(all_texts)

    input_embeddings = embedder.embed(input_units)
    output_embeddings = embedder.embed(output_units)

    # Match
    match_result = greedy_match(
        input_units, output_units, input_embeddings, output_embeddings, threshold
    )

    # Score
    doc_score = score_document(match_result, len(input_units), len(output_units))

    # Report
    if output_format == "terminal":
        report_terminal(doc_score, mode)
    elif output_format == "json":
        click.echo(report_json(doc_score, mode))
    elif output_format == "markdown":
        click.echo(report_markdown(doc_score, mode))


if __name__ == "__main__":
    main()
