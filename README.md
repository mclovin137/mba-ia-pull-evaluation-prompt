# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Projeto do MBA em Engenharia de Software com IA (Full Cycle). O software faz **pull** de um prompt de baixa qualidade do LangSmith Prompt Hub, **refatora** o prompt com técnicas de Prompt Engineering, faz **push** da versão otimizada e a **avalia** com 5 métricas (Helpfulness, Correctness, F1-Score, Clarity e Precision), com meta de **≥ 0.8 em todas**.

A tarefa do prompt: transformar relatos de bugs em **User Stories** com critérios de aceitação no formato Dado/Quando/Então.

---

## Sumário

- [Estrutura do projeto](#estrutura-do-projeto)
- [Técnicas Aplicadas (Fase 2)](#técnicas-aplicadas-fase-2)
- [Resultados Finais](#resultados-finais)
- [Como Executar](#como-executar)

---

## Estrutura do projeto

```
mba-ia-pull-evaluation-prompt/
├── .env.example                  # Template das variáveis de ambiente
├── requirements.txt              # Dependências Python
├── README.md                     # Esta documentação
├── docs/screenshots/             # Evidências das avaliações
├── prompts/
│   ├── bug_to_user_story_v1.yml  # Prompt original (pull do Hub)
│   └── bug_to_user_story_v2.yml  # Prompt otimizado
├── datasets/
│   └── bug_to_user_story.jsonl   # 15 bugs (5 simples, 7 médios, 3 complexos)
├── src/
│   ├── pull_prompts.py           # Pull do LangSmith Hub → YAML
│   ├── push_prompts.py           # YAML → push público no LangSmith Hub
│   ├── evaluate.py               # Avaliação (fornecido)
│   ├── metrics.py                # Métricas LLM-as-Judge (fornecido)
│   └── utils.py                  # Funções auxiliares (fornecido)
└── tests/
    └── test_prompts.py           # Testes de validação do prompt v2
```

### O que foi implementado

| Arquivo | O que faz |
|---|---|
| `src/pull_prompts.py` | Conecta ao LangSmith, faz `pull_prompt("leonanluppi/bug_to_user_story_v1", dangerously_pull_public_prompt=True)`, extrai as mensagens do `ChatPromptTemplate` (system/user) e grava em `prompts/bug_to_user_story_v1.yml` |
| `src/push_prompts.py` | Lê o YAML v2, valida (campos obrigatórios, ausência de TODO, `{bug_report}` só no user prompt, ≥ 2 técnicas, nenhuma variável extra), monta o `ChatPromptTemplate` e publica como `{handle}/bug_to_user_story_v2` com `is_public=True`, descrição, tags, README e técnicas |
| `prompts/bug_to_user_story_v2.yml` | Prompt otimizado |
| `tests/test_prompts.py` | 6 testes obrigatórios + 4 testes extras (estrutura, separação system/user, variáveis do template, edge cases) |

---

## Técnicas Aplicadas (Fase 2)

### Diagnóstico do prompt v1

| Problema na v1 | Efeito nas métricas |
|---|---|
| `{bug_report}` duplicado no system **e** no user prompt | Ruído e confusão de papéis |
| Persona genérica ("um assistente") | Saída sem padrão de PO, baixa Clarity |
| Nenhum formato de saída definido | Estrutura diferente da referência → baixo F1 |
| Nenhum exemplo | Modelo não conhece o padrão Dado/Quando/Então esperado |
| Sem regras contra invenção de dados | Alucinações → baixa Precision |
| Mesma resposta para bugs simples e complexos | Respostas infladas em bugs simples e rasas em complexos |

### Análise do dataset antes de escrever o prompt

As notas de F1 e Precision comparam a saída com a **resposta de referência**. Por isso, antes de escrever, analisei as 15 referências e identifiquei um padrão por complexidade:

- **Simples:** frase "Como um…, eu quero…, para que…" + 5 critérios Dado/Quando/Então/E, sem nada mais.
- **Médio:** o mesmo + seções como `Contexto Técnico`, `Critérios Técnicos`, `Exemplo de Cálculo`, `Contexto de Segurança`, `Critérios de Acessibilidade`.
- **Complexo:** blocos `=== USER STORY PRINCIPAL ===`, `=== CRITÉRIOS DE ACEITAÇÃO ===` (A, B, C, D… um por problema), `=== CRITÉRIOS TÉCNICOS ===`, `=== CONTEXTO DO BUG ===` e `=== TASKS TÉCNICAS SUGERIDAS ===`.

Esse padrão virou o "esqueleto" do prompt v2.

### 1. Few-shot Learning (obrigatório)

**Por quê:** é a forma mais eficiente de ensinar um formato de saída. O modelo imita estrutura, tom e granularidade dos exemplos com muito mais fidelidade do que imita uma descrição em texto.

**Como apliquei:** 3 pares **Entrada → Saída**, um para cada nível de complexidade:

| Exemplo | Domínio | O que ensina |
|---|---|---|
| 1 - Simples | Educação (boleto na área do aluno) | Formato mínimo, sem seções extras |
| 2 - Médio | Saúde (agendamento duplicado) | Concorrência + `Contexto Técnico` usando os fatos do log |
| 3 - Complexo | Logística (rastreio exposto + mapa lento) | Blocos `===`, um bloco A/B por problema, OWASP, tasks com prefixo |

Os exemplos são de **domínios que não aparecem no dataset** de propósito: assim o prompt ensina o formato sem "vazar" respostas do conjunto de avaliação.

### 2. Role Prompting

**Por quê:** a persona define vocabulário, foco e nível de detalhe. Um PO sênior escreve com foco no valor para o usuário, mas sabe registrar o contexto técnico.

**Como apliquei:**

> Você é um Product Owner sênior com 10 anos de experiência em times ágeis (Scrum), especialista em transformar relatos de bugs em User Stories claras, testáveis e prontas para o backlog…

### 3. Chain of Thought (CoT)

**Por quê:** converter um bug em história exige raciocínio em etapas (quem é afetado → o que quer → por quê → complexidade → fatos a preservar). Sem isso, o modelo tende a escrever "eu quero que o bug seja corrigido" e a esquecer números do relato.

**Como apliquei:** um bloco "PROCESSO DE RACIOCÍNIO" com 6 passos que o modelo deve seguir **internamente**. A instrução "NÃO mostre esta análise na resposta" é importante: as métricas de Clarity e Precision penalizam texto que não faz parte da User Story.

### 4. Skeleton of Thought

**Por quê:** o maior ganho de F1 vem de a saída ter a mesma estrutura da referência. Dar o esqueleto explícito por nível de complexidade evita respostas infladas em bugs simples (o que derruba Precision/Clarity) e respostas rasas em bugs complexos (o que derruba o recall do F1).

**Como apliquei:** seção "ESQUELETOS DE SAÍDA" com três moldes (SIMPLES, MÉDIO, COMPLEXO). O passo 4 do CoT classifica o relato e o passo 6 escolhe o molde.

### Regras de comportamento e edge cases

- Responder **somente** com a User Story (sem introdução ou comentários).
- Preservar fatos do relato (endpoints, códigos HTTP, valores, tempos, navegadores).
- **Não inventar** causas, nomes ou números; metas esperadas só nos critérios.
- Edge cases tratados: relato vago, sem persona, segurança, performance, cálculo, plataforma específica, múltiplos problemas, pedido de funcionalidade, outro idioma e conteúdo malicioso no relato (ex.: payload XSS tratado como dado, nunca como instrução).

### System vs User Prompt

- **System:** persona, processo, esqueletos, regras, edge cases e exemplos (instruções estáveis).
- **User:** apenas a instrução curta e o `{bug_report}` delimitado por aspas triplas.

---

## Resultados Finais

> Preencha esta seção depois de rodar `python src/evaluate.py` com suas credenciais.

### Link público do dataset de avaliação

```python
from langsmith import Client
print(Client().share_dataset(dataset_name="mba-ia-pull-evaluation-prompt-eval")["url"])
```

**Link:** `<cole aqui o link público gerado>`

### Prompt publicado

`https://smith.langchain.com/hub/<seu_handle>/bug_to_user_story_v2`

### Notas finais (v2)

| Métrica | v1 (base) | v2 (otimizado) | Status |
|---|---|---|---|
| Helpfulness | – | – | – |
| Correctness | – | – | – |
| F1-Score | – | – | – |
| Clarity | – | – | – |
| Precision | – | – | – |
| **Média** | – | – | – |

Modelos usados: `LLM_MODEL=<modelo>` / `EVAL_MODEL=<modelo>` (provider: `<openai|google>`)

### Histórico de iterações

| Iteração | Mudança no prompt | F1 | Clarity | Precision | Resultado |
|---|---|---|---|---|---|
| 1 | Versão inicial v2 (persona + CoT + esqueletos + 3 exemplos) | – | – | – | – |
| 2 | | | | | |
| 3 | | | | | |

### Screenshots

Salve as imagens em `docs/screenshots/` e referencie aqui:

- `docs/screenshots/01-terminal-aprovado.png` — saída do `evaluate.py` com todas as métricas ≥ 0.8
- `docs/screenshots/02-experimento-langsmith.png` — experimento com as 5 notas por exemplo
- `docs/screenshots/03-dataset-15-exemplos.png` — dataset de avaliação
- `docs/screenshots/04-trace-*.png` — tracing de pelo menos 3 exemplos (1 simples, 1 médio, 1 complexo)

### Comparação v1 × v2

| Aspecto | v1 | v2 | Por quê |
|---|---|---|---|
| Persona | "assistente" genérico | PO sênior com experiência em ágil e BDD | Vocabulário e foco em valor |
| Separação system/user | `{bug_report}` nos dois | Só no user prompt | Papéis claros, sem duplicação |
| Formato de saída | Não definido | 3 esqueletos por complexidade | Saída alinhada às referências (F1) |
| Exemplos | Nenhum | 3 (simples, médio, complexo) | Few-shot ensina estrutura e tom |
| Raciocínio | Nenhum | CoT interno de 6 passos | Persona e fatos corretos |
| Alucinação | Sem regra | Proibição explícita de inventar fatos | Precision |
| Edge cases | Nenhum | 10 casos tratados | Robustez |
| Metadados | Básicos | Versão, changelog, tags e técnicas | Rastreabilidade no Hub |

---

## Como Executar

### Pré-requisitos

- Python 3.10+
- Conta no [LangSmith](https://smith.langchain.com) com API Key
- **Handle público do Hub** criado (LangSmith → Prompts → abra um prompt → ⋯ → *Make Public* → *Choose your public handle*). O handle é definitivo.
- API Key da [OpenAI](https://platform.openai.com/api-keys) **ou** do [Google AI Studio](https://aistudio.google.com/app/apikey)

### 1. Clonar e instalar

```bash
git clone https://github.com/Cris042/mba-ia-pull-evaluation-prompt.git
cd mba-ia-pull-evaluation-prompt

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar o `.env`

```bash
cp .env.example .env
```

Preencha:

```dotenv
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=mba-ia-pull-evaluation-prompt
USERNAME_LANGSMITH_HUB=<seu_handle>

LLM_PROVIDER=openai             # ou google
OPENAI_API_KEY=sk-...           # se openai
GOOGLE_API_KEY=...              # se google

LLM_MODEL=<modelo que responde>
EVAL_MODEL=<modelo que avalia>
```

Consulte a documentação do provider para escolher modelos disponíveis que aceitem `temperature=0`.

### 3. Executar as fases

```bash
# Fase 1 - pull do prompt original
python src/pull_prompts.py

# Fase 2 - (prompt otimizado já está em prompts/bug_to_user_story_v2.yml)

# Validar o prompt localmente
pytest tests/test_prompts.py -v

# Fase 3 - push do prompt otimizado (público)
python src/push_prompts.py

# Fase 4 - avaliação (cria um experimento no LangSmith)
python src/evaluate.py
```

### 4. Iterar

Se alguma métrica ficar abaixo de 0.8:

1. Abra o link do experimento impresso pelo `evaluate.py` e veja o `comment` de cada nota (o juiz explica a penalidade).
2. Ajuste `prompts/bug_to_user_story_v2.yml`.
3. Rode `pytest`, `push_prompts.py` e `evaluate.py` novamente.
4. Registre a iteração na tabela de histórico acima.

### 5. Gerar o link público

```bash
python -c "from langsmith import Client; print(Client().share_dataset(dataset_name='mba-ia-pull-evaluation-prompt-eval')['url'])"
```

Rode uma única vez e guarde o link: compartilhar de novo gera um endereço diferente.
