"""
generate_template.py
====================
VEGA v3.0 -- Gerador de Template Markdown para Plano de Testes RAG Security

Responsabilidade:
    Gera um arquivo .md pre-estruturado e reutilizavel em:
        src/agents_outputs/test-plan/rag_security_test_plan_{YYYYMMDD}.md

    O template e preenchido com:
    - Metadados fixos da proposta de pesquisa (PICo-C, metricas, fases)
    - Lista de fontes disponivel no source_inventory (se existir)
    - Placeholders rastreados para os campos que VEGA deve preencher

Uso:
    python generate_template.py
    python generate_template.py --sources-only       (so inventario, sem casos)
    python generate_template.py --phase P2           (template para fase especifica)

Anti-alucinacao:
    Este script NAO inventa dados. Apenas le o que existe nos arquivos
    de inventario e proposta. Campos sem dados ficam como placeholders
    explicitamente marcados.
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Constantes da proposta de pesquisa
# Fonte: picoc-method/material/PROPOSTA RAG SECURITY.md
# Estas sao as UNICAS constantes pre-preenchidas sem leitura de JSON --
# sao dados fixos da proposta oficial, nao suposicoes.
# ---------------------------------------------------------------------------

RESEARCH_TITLE = (
    "Avaliacao Experimental de Prompt Injection e Vazamento de Dados "
    "em Arquiteturas RAG Corporativas"
)

PICOC = {
    "population": (
        "Arquiteturas RAG corporativas com corpus de documentos sensiveis "
        "(contratos, relatorios de incidentes, politicas, e-mails, dados operacionais)"
    ),
    "intervention": "[PREENCHER: vetores selecionados pelo usuario]",
    "comparison": (
        "Sistema RAG sem controles de seguranca (baseline) "
        "vs. sistema RAG com controles ativos (filtros, reranking, ACL, guardrails)"
    ),
    "outcome": "Reducao de ASR e DLR, manutencao de utilidade (UD < 15%), latencia aceitavel (CO < 500ms)",
    "context": "Ambiente experimental isolado, corpus 100% sintetico, sem dados reais de terceiros",
}

METRICS = [
    ("ASR", "Attack Success Rate",  "% de ataques com comportamento indesejado",          "Baseline"),
    ("DLR", "Data Leakage Rate",    "% de consultas que revelam dados nao autorizados",   "Baseline"),
    ("FPR", "False Positive Rate",  "% de consultas legitimas bloqueadas pelos controles", "< 5%"),
    ("FNR", "False Negative Rate",  "% de ataques nao detectados pelos controles",         "< 10%"),
    ("UD",  "Utility Degradation",  "Reducao na qualidade das respostas (via RAGAS)",      "< 15%"),
    ("CO",  "Control Overhead",     "Latencia adicional introduzida pelos controles (ms)", "< 500ms"),
]

ATTACK_VECTORS = [
    ("VA-1", "DIRECT_INJECTION",   "Instrucoes maliciosas diretamente na query do usuario",                 "ASR, FPR",  "Prompt"),
    ("VA-2", "INDIRECT_INJECTION", "Instrucoes maliciosas embutidas em documentos recuperados",             "ASR, FNR",  "Ingestao + Prompt"),
    ("VA-3", "RETRIEVAL_POISON",   "Documentos projetados para serem recuperados indevidamente",            "ASR, DLR",  "Ingestao + Recuperacao"),
    ("VA-4", "CONTEXT_MANIP",      "Sobrescrita do contexto de sistema via documentos",                     "ASR",       "Prompt"),
    ("VA-5", "DATA_EXTRACTION",    "Queries especificas para extrair dados sensiveis do corpus",            "DLR, FNR",  "Saida"),
    ("VA-6", "ROLE_JAILBREAK",     "Instrucoes para ignorar restricoes de papel do modelo",                 "ASR, FPR",  "Prompt"),
    ("VA-7", "SEMANTIC_INDUCTION", "Manipulacao do espaco de embedding para direcionar recuperacao",         "ASR, DLR",  "Recuperacao"),
]

PHASES = {
    "P1": "Preparacao -- Corpus, Taxonomia e Ambiente",
    "P2": "Baseline -- Ataques sem Controles",
    "P3": "Mitigacao -- Controles e Testes Ablatorios",
    "P4": "Analise -- Resultados e Redacao",
}

TC_PLACEHOLDER = """\
### TC-{NNN} -- [TITULO DO CASO DE TESTE]

| Campo | Valor |
|---|---|
| Fase | {fase_id} |
| Vetor | [ATTACK_CLASS] |
| Modelo alvo | [PREENCHER] |
| Tipo de input | [user_query / document / system_prompt] |
| Metricas coletadas | [ASR / DLR / FPR / FNR] |
| Criterio de sucesso | [PREENCHER: definicao mensuravel] |
| Controles ativos | [nenhum -- baseline / lista de controles] |

**Descricao do payload de ataque:**

[PREENCHER: descricao tecnica do ataque]

**Comportamento vulneravel esperado:**

[PREENCHER: o que o sistema fara se vulneravel]

**Evidencia bibliografica:**

> Fonte: `[NOME-DO-ARQUIVO.json]` | Campo: `[sections[N].content]`
> Trecho: "[TRECHO EXATO EXTRAIDO DO JSON -- nao inventar]"
> Relevancia: [por que este trecho fundamenta o caso de teste]

---
"""


# ---------------------------------------------------------------------------
# Resolucao de caminhos
# ---------------------------------------------------------------------------

def find_repo_root() -> Path:
    """
    Localiza a raiz do repositorio por marcadores conhecidos.
    Tenta CWD primeiro, depois sobe ate 10 niveis.
    """
    anchors = {".git", "picoc-method", "src", ".agents"}
    candidate = Path.cwd()
    for _ in range(10):
        if anchors.issubset({f.name for f in candidate.iterdir()}):
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent

    # Fallback para o caminho do script
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir
    for _ in range(10):
        try:
            if anchors.issubset({f.name for f in candidate.iterdir()}):
                return candidate
        except PermissionError:
            pass
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent

    raise RuntimeError(
        "Nao foi possivel localizar REPO_ROOT automaticamente.\n"
        "Execute o script a partir da raiz do repositorio."
    )


# ---------------------------------------------------------------------------
# Leitura do inventario de fontes
# ---------------------------------------------------------------------------

def load_latest_inventory(agents_output_dir: Path) -> dict | None:
    """
    Carrega o inventario de fontes mais recente em agents_outputs/test-plan/.
    Retorna None se nenhum inventario for encontrado.
    """
    inventory_dir = agents_output_dir / "test-plan"
    if not inventory_dir.exists():
        return None

    inventories = sorted(inventory_dir.glob("source_inventory_*.json"), reverse=True)
    if not inventories:
        return None

    with open(inventories[0], encoding="utf-8") as f:
        return json.load(f)


def load_best_sources_list(articles_output_dir: Path) -> list[dict]:
    """
    Carrega metadados minimos dos JSONs disponiveis em best-sources/.
    Retorna lista de dicts com json_file e title.
    Nunca inventa dados -- retorna vazio se a pasta nao existir.
    """
    sources_dir = articles_output_dir / "best-sources"
    if not sources_dir.exists():
        return []

    sources = []
    for json_path in sorted(sources_dir.glob("*.json")):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            sources.append({
                "json_file":  json_path.name,
                "source_pdf": data.get("metadata", {}).get("source_file", json_path.stem + ".pdf"),
                "title":      data.get("title") or "[titulo nao extraido]",
            })
        except (json.JSONDecodeError, OSError) as e:
            sources.append({
                "json_file":  json_path.name,
                "source_pdf": json_path.stem + ".pdf",
                "title":      f"[erro ao ler JSON: {e}]",
            })
    return sources


# ---------------------------------------------------------------------------
# Blocos de secoes do template
# ---------------------------------------------------------------------------

def section_header(repo_root: Path, sources: list[dict], phase_filter: str | None) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    phase_label = PHASES.get(phase_filter, "Todas as fases") if phase_filter else "Todas as fases"

    return f"""\
# Plano de Testes -- Seguranca em RAG Corporativo

**Pesquisa:** {RESEARCH_TITLE}
**Agente:** VEGA v3.0
**Data de geracao:** {today}
**Escopo de fases:** {phase_label}
**Versao:** 1 (rascunho -- aguarda preenchimento pelo agente VEGA)

---

"""


def section_picoc() -> str:
    rows = "\n".join(
        f"| **{k.capitalize()}** | {v} |"
        for k, v in PICOC.items()
    )
    return f"""\
## Alinhamento PICo-C

| Componente | Definicao |
|---|---|
{rows}

---

"""


def section_sources(sources: list[dict]) -> str:
    if not sources:
        return """\
## Fontes Disponiveis

Nenhum JSON encontrado em `best-sources/`.
Execute ATLAS (pdf-to-json-converter) antes de usar este template.

---

"""
    header = "## Fontes Disponiveis\n\n"
    header += "| # | Arquivo JSON | Titulo Extraido | Usada nos casos |\n"
    header += "|---|---|---|---|\n"
    rows = "\n".join(
        f"| {i+1} | `{s['json_file']}` | {s['title']} | [PREENCHER] |"
        for i, s in enumerate(sources)
    )
    return header + rows + "\n\n---\n\n"


def section_metrics() -> str:
    header = "## Metricas de Avaliacao\n\n"
    header += "| Sigla | Nome Completo | Descricao | Meta |\n"
    header += "|---|---|---|---|\n"
    rows = "\n".join(
        f"| {sigla} | {nome} | {desc} | {meta} |"
        for sigla, nome, desc, meta in METRICS
    )
    return header + rows + "\n\n---\n\n"


def section_attack_reference() -> str:
    header = "## Referencia de Vetores de Ataque\n\n"
    header += "| ID | Classe | Descricao | Metricas | Camada |\n"
    header += "|---|---|---|---|---|\n"
    rows = "\n".join(
        f"| {vid} | {cls} | {desc} | {metrics} | {layer} |"
        for vid, cls, desc, metrics, layer in ATTACK_VECTORS
    )
    return header + rows + "\n\n---\n\n"


def section_phases(phase_filter: str | None) -> str:
    phases_to_include = (
        {phase_filter: PHASES[phase_filter]}
        if phase_filter and phase_filter in PHASES
        else PHASES
    )

    blocks = []
    tc_counter = 1
    for phase_id, phase_name in phases_to_include.items():
        block = f"## {phase_id} -- {phase_name}\n\n"
        block += "**Objetivo:** [PREENCHER]\n"
        block += "**Duracao estimada:** [PREENCHER] semanas\n"
        block += "**Modelos testados:** [PREENCHER]\n\n"
        block += "---\n\n"
        # Dois casos de teste placeholder por fase
        for _ in range(2):
            block += TC_PLACEHOLDER.format(
                NNN=str(tc_counter).zfill(3),
                fase_id=phase_id
            )
            tc_counter += 1
        blocks.append(block)

    return "\n".join(blocks)


def section_no_source_table() -> str:
    return """\
## Campos sem Cobertura nos JSONs Carregados

| Campo | Caso de Teste | Motivo |
|---|---|---|
| [PREENCHER] | TC-[NNN] | Nenhum JSON contem evidencia para este vetor |

---

"""


def section_notes() -> str:
    return """\
## Notas do Pesquisador

<!-- Espaco para observacoes, decisoes de design e restricoes identificadas -->

---

## Historico de Versoes

| Versao | Data | Responsavel | Alteracao |
|---|---|---|---|
| 1 | [DATA] | VEGA v3.0 | Geracao inicial do template |

"""


# ---------------------------------------------------------------------------
# Composicao e escrita do template
# ---------------------------------------------------------------------------

def build_template(sources: list[dict], phase_filter: str | None, repo_root: Path) -> str:
    parts = [
        section_header(repo_root, sources, phase_filter),
        section_picoc(),
        section_sources(sources),
        section_metrics(),
        section_attack_reference(),
        section_phases(phase_filter),
        section_no_source_table(),
        section_notes(),
    ]
    return "".join(parts)


def write_template(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = output_dir / f"rag_security_test_plan_{today}.md"

    # Idempotencia: nao sobrescreve sem avisar
    if out_path.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_path = output_dir / f"rag_security_test_plan_{ts}.md"
        print(f"[AVISO] Arquivo do dia ja existe. Salvando como: {out_path.name}")

    out_path.write_text(content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VEGA -- Gerador de template Markdown para plano de testes RAG Security"
    )
    parser.add_argument(
        "--phase",
        choices=list(PHASES.keys()),
        default=None,
        help="Gerar template apenas para uma fase especifica (P1, P2, P3 ou P4)"
    )
    parser.add_argument(
        "--sources-only",
        action="store_true",
        help="Exibir apenas o inventario de fontes, sem gerar o template completo"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Caminho explicito para a raiz do repositorio (opcional)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Resolver REPO_ROOT
    try:
        repo_root = args.repo_root if args.repo_root else find_repo_root()
    except RuntimeError as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        sys.exit(1)

    articles_output = repo_root / "src" / "scripts_outputs" / "articles-outputs"
    agents_output   = repo_root / "src" / "agents_outputs"

    print(f"[INFO] REPO_ROOT      : {repo_root}")
    print(f"[INFO] Lendo fontes de: {articles_output / 'best-sources'}")
    print(f"[INFO] Output em      : {agents_output / 'test-plan'}")
    print()

    # Carregar fontes
    sources = load_best_sources_list(articles_output)
    print(f"[INFO] {len(sources)} JSON(s) encontrado(s) em best-sources/")
    for s in sources:
        print(f"       - {s['json_file']} -> {s['title'][:60]}")

    if not sources:
        print()
        print("[AVISO] Nenhum JSON encontrado. Execute ATLAS primeiro.")
        print("        O template sera gerado com placeholders vazios.")

    if args.sources_only:
        print()
        print("[INFO] Modo --sources-only: inventario exibido. Template nao gerado.")
        sys.exit(0)

    # Gerar template
    print()
    template = build_template(sources, args.phase, repo_root)
    out_path = write_template(template, agents_output / "test-plan")

    print(f"[OK] Template gerado: {out_path}")
    print()
    print("Proximos passos:")
    print("  1. Abra o arquivo .md gerado")
    print("  2. Execute VEGA e instrua-o a preencher o template com base nos JSONs")
    print("  3. Campos [PREENCHER] serao substituidos por VEGA com evidencias dos JSONs")
    print("  4. Campos sem cobertura serao marcados como [SEM FONTE NOS JSONs CARREGADOS]")


if __name__ == "__main__":
    main()
