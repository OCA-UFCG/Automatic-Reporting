from __future__ import annotations

import argparse
import csv
from datetime import datetime
import io
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape


def parse_drive_file_id(value: str) -> str | None:
    if "/d/" in value:
        marker = value.split("/d/", 1)[1]
        return marker.split("/", 1)[0]

    parsed = urlparse(value)
    query = parse_qs(parsed.query)

    if "id" in query and query["id"]:
        return query["id"][0]

    if parsed.netloc and "drive.google.com" in parsed.netloc and parsed.path:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 1 and parts[0] != "file":
            return parts[0]

    if "/" not in value and len(value) > 20:
        return value

    return None


def build_drive_csv_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def read_csv_from_text(csv_text: str) -> list[dict[str, Any]]:
    sample = csv_text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(csv_text), dialect=dialect)
    rows: list[dict[str, Any]] = []
    for row in reader:
        cleaned_row = {
            (key or "").strip().lstrip("\ufeff"): (
                value.strip() if isinstance(value, str) else value
            )
            for key, value in row.items()
        }
        rows.append(cleaned_row)
    return rows


def fetch_csv_rows(source: str) -> list[dict[str, Any]]:
    path = Path(source)
    if path.exists():
        return read_csv_from_text(path.read_text(encoding="utf-8"))

    file_id = parse_drive_file_id(source)
    url = build_drive_csv_url(file_id) if file_id else source

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type.lower() and "drive.google.com" in url:
        raise ValueError(
            "Não foi possível baixar o CSV do Google Drive. "
            "Verifique se o arquivo está compartilhado como 'Qualquer pessoa com o link'."
        )

    return read_csv_from_text(response.text)


def _set_nested_value(target: dict[str, Any], keys: list[str], value: Any) -> None:
    current = target
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def nest_dot_keys(row: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key, value in row.items():
        if "." in key:
            _set_nested_value(nested, key.split("."), value)
        else:
            nested[key] = value
    return nested


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def find_city_column(columns: list[str], explicit_column: str | None) -> str:
    if explicit_column:
        return explicit_column

    candidates = [
        "city",
        "cidade",
        "municipio",
        "município",
        "nm_mun",
        "nome_municipio",
        "nome município",
    ]
    normalized_map = {normalize_text(col): col for col in columns}
    for candidate in candidates:
        if candidate in normalized_map:
            return normalized_map[candidate]

    raise ValueError(
        "Não encontrei coluna de cidade automaticamente. "
        "Use --city-column para informar o nome da coluna."
    )


def find_year_column(columns: list[str], explicit_column: str | None) -> str | None:
    if explicit_column:
        return explicit_column

    candidates = ["year", "ano"]
    normalized_map = {normalize_text(col): col for col in columns}
    for candidate in candidates:
        if candidate in normalized_map:
            return normalized_map[candidate]
    return None


def select_city_row(
    rows: list[dict[str, Any]], city_name: str, city_column: str
) -> dict[str, Any]:
    expected = normalize_text(city_name)
    for row in rows:
        if normalize_text(str(row.get(city_column, ""))) == expected:
            return row

    raise ValueError(
        f"Cidade '{city_name}' não encontrada na coluna '{city_column}'."
    )


def build_demografia_context(row: dict[str, Any]) -> dict[str, Any]:
    base_nested = nest_dot_keys(row)
    demografia = dict(base_nested.get("demografia", {}))
    flat_keys = [
        "pop_total",
        "pop_mulher",
        "pop_mulher_per",
        "pop_homem",
        "pop_homem_per",
        "cres_pop",
        "cor_raca_pri",
        "porte",
    ]
    for key in flat_keys:
        if key in row and key not in demografia:
            demografia[key] = row[key]
    return demografia


def maybe_generate_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "Para gerar PDF, instale dependência opcional: pip install weasyprint"
        ) from exc

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))


def render_html(template_path: Path, output_path: Path, context: dict[str, Any]) -> None:

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_path.name)
    html = template.render(**context)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera um relatório HTML simples a partir de um CSV local ou do Google Drive."
    )
    parser.add_argument(
        "source",
        help="Caminho local, URL do CSV, URL do Google Drive ou apenas file_id do Drive.",
    )
    parser.add_argument(
        "--template",
        default="templates/report.html.j2",
        help="Caminho do template Jinja2.",
    )
    parser.add_argument(
        "--output",
        default="output/report.html",
        help="Caminho do HTML gerado.",
    )
    parser.add_argument(
        "--title",
        default="Relatório CSV",
        help="Título exibido no relatório.",
    )
    parser.add_argument(
        "--city",
        help="Nome da cidade/município para gerar relatório individual.",
    )
    parser.add_argument(
        "--city-column",
        help="Nome da coluna de cidade no CSV (ex.: cidade, municipio, city).",
    )
    parser.add_argument(
        "--year",
        help="Ano para exibição no relatório. Se omitido, tenta usar coluna ano/year.",
    )
    parser.add_argument(
        "--year-column",
        help="Nome da coluna de ano no CSV (ex.: ano, year).",
    )
    parser.add_argument(
        "--pdf-output",
        help="Caminho do PDF de saída (opcional). Ex.: output/report.pdf",
    )

    args = parser.parse_args()

    rows = fetch_csv_rows(args.source)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    if args.city:
        if not rows:
            raise ValueError("CSV vazio. Não há linhas para selecionar município.")

        columns = list(rows[0].keys())
        city_column = find_city_column(columns, args.city_column)
        selected_row = select_city_row(rows, args.city, city_column)
        row = nest_dot_keys(selected_row)
        demografia_context = build_demografia_context(selected_row)
        city_value = selected_row.get(city_column, args.city)

        year_column = find_year_column(columns, args.year_column)
        year_value = args.year or (selected_row.get(year_column, "") if year_column else "")

        context = {
            "title": args.title,
            "generated_at": generated_at,
            "city": city_value,
            "year": year_value,
            "row": row,
            "demografia": demografia_context,
        }
    else:
        context = {
            "title": args.title,
            "generated_at": generated_at,
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
        }

    render_html(
        template_path=Path(args.template),
        output_path=Path(args.output),
        context=context,
    )

    print(f"Relatório gerado em: {args.output}")
    if args.pdf_output:
        maybe_generate_pdf(Path(args.output), Path(args.pdf_output))
        print(f"PDF gerado em: {args.pdf_output}")


if __name__ == "__main__":
    main()
