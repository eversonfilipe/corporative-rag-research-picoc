# Contexto Estruturado da Pesquisa RAG Security

## Identificação

| Campo | Valor |
|---|---|
| Título | Avaliação Experimental de Prompt Injection e Vazamento de Dados em Arquiteturas RAG Corporativas |
| Área | Segurança em IA / Segurança Ofensiva Controlada |
| Subárea | RAG Security, Prompt Injection, Data Leakage, LLM Applications |
| Duração | 12 meses |
| Data | Junho de 2026 |
| Potencial de publicação | IEEE S&P, ACM CCS, USENIX Security, NDSS |

---

## Metodologia PICo-C

| Componente | Definição nesta pesquisa |
|---|---|
| **P**opulation | Arquiteturas RAG corporativas com corpus de documentos sensíveis (contratos, relatórios de incidentes, políticas, e-mails, dados operacionais) |
| **I**ntervention | Ataques: prompt injection direta/indireta, retrieval poisoning, context manipulation, data extraction, role jailbreaking, semantic induction |
| **C**omparison | Sistema RAG sem controles (baseline) vs. com controles de segurança ativos (filtros, reranking, ACL, guardrails) |
| **o**utcome | Redução de ASR e DLR, manutenção de utilidade (UD < 15%), latência aceitável (CO < 500ms) |
| **C**ontext | Ambiente experimental isolado, corpus 100% sintético, sem dados reais de terceiros |

---

## Corpus Sintético

| Categoria | Exemplos | Volume |
|---|---|---|
| Contratos | NDA, fornecedores, licenças, SLAs | 100 docs |
| Relatórios de incidente | Logs de segurança, CVEs, post-mortems | 120 docs |
| Políticas internas | SI, BYOD, acesso privilegiado | 80 docs |
| E-mails corporativos | Comunicações executivas, negociações, dados de RH | 150 docs |
| Dados operacionais | Logs de acesso, registros financeiros sintéticos | 50 docs |

---

## Vetores de Ataque (7 classes)

| ID | Classe | Descrição |
|---|---|---|
| VA-1 | DIRECT_INJECTION | Instruções maliciosas diretamente na query do usuário |
| VA-2 | INDIRECT_INJECTION | Instruções maliciosas embutidas em documentos recuperados |
| VA-3 | RETRIEVAL_POISON | Documentos projetados para serem recuperados indevidamente |
| VA-4 | CONTEXT_MANIP | Sobrescrita do contexto de sistema via documentos |
| VA-5 | DATA_EXTRACTION | Queries crafted para extrair dados sensíveis |
| VA-6 | ROLE_JAILBREAK | Instruções para ignorar restrições de papel do modelo |
| VA-7 | SEMANTIC_INDUCTION | Manipulação do espaço de embedding para direcionar recuperação |

---

## Controles de Segurança (4 camadas)

| Camada | Controles | Técnica |
|---|---|---|
| Ingestão | Classificação de docs, detecção de padrões maliciosos, chunking adaptativo | NLP + regex |
| Recuperação | Reranking, controle de acesso por metadados, filtragem semântica | Embedding + ACL |
| Prompt | Sanitização de entrada, instruções defensivas no system prompt, delimitadores | Engenharia de prompt |
| Saída | Detecção de PII, classificação de resposta, output guardrails | LLM-as-judge |

---

## Métricas de Avaliação

| Métrica | Sigla | Descrição | Meta |
|---|---|---|---|
| Attack Success Rate | ASR | % de ataques que resultam em comportamento indesejado | Baseline |
| Data Leakage Rate | DLR | % de consultas que revelam dados não autorizados | Baseline |
| False Positive Rate | FPR | % de consultas legítimas bloqueadas | < 5% |
| False Negative Rate | FNR | % de ataques não detectados | < 10% |
| Utility Degradation | UD | Redução na qualidade das respostas (RAGAS) | < 15% |
| Control Overhead | CO | Latência adicional dos controles (ms) | < 500ms |

---

## Fases de Execução

| Fase | Período | Atividades | Entrega |
|---|---|---|---|
| 1 | Meses 1-3 | Revisão sistemática, corpus sintético, taxonomia, ambiente | Corpus + Taxonomia |
| 2 | Meses 4-6 | RAG baseline, ataques sem controles, métricas baseline | Relatório Baseline |
| 3 | Meses 7-9 | Controles, testes ablatórios, comparação entre modelos | Dataset + Resultados |
| 4 | Meses 10-12 | Análise estatística, artigo, benchmark open-source | Artigo + Benchmark |

---

## Modelos Candidatos

- GPT-4o (OpenAI)
- Claude (Anthropic)
- Gemini (Google)
- LLaMA (Meta — open-source)

---

## Ferramentas Previstas

| Categoria | Ferramentas |
|---|---|
| Pipeline RAG | LangChain, LlamaIndex, ChromaDB, Pinecone |
| Avaliação RAG | RAGAS, TruLens, DeepEval |
| Detecção de ataques | Guardrails AI, NeMo Guardrails, Llama Guard |
| Análise estatística | Python (scipy, statsmodels), R, Jupyter Notebooks |

---

## Referências Base da Proposta

1. Greshake et al. (2023) — Indirect Prompt Injection (arXiv:2302.12173)
2. Perez & Ribeiro (2022) — Ignore Previous Prompt (NeurIPS ML Safety Workshop)
3. OWASP (2024) — Top 10 for LLM Applications v1.1
4. Lewis et al. (2020) — RAG for Knowledge-Intensive NLP Tasks (NeurIPS 2020)
5. Zou et al. (2023) — Universal Adversarial Attacks on Aligned LLMs (arXiv:2307.15043)
6. NIST (2023) — AI Risk Management Framework (AI RMF 1.0)
7. Yi et al. (2023) — Benchmarking Indirect Prompt Injection (arXiv:2312.14197)

---

## Antiprompts Globais para VEGA

- Nunca inventar resultados antes da execução experimental
- Nunca citar artigos não presentes nos JSONs de articles-outputs
- Nunca marcar um controle como "eficaz" ou "ineficaz" sem dados reais
- Nunca simplificar um caso de teste omitindo payload description ou critério de sucesso
- Sempre rastrear cada decisão de design de teste a um artigo fonte ou à proposta
