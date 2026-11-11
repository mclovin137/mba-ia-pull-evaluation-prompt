# Evidências locais

Execução em 10/11/2026 (America/Sao_Paulo), com Python 3.12.14 e as dependências de `requirements.txt`. Os timestamps do JSON e JUnit registram o ambiente em UTC.

Código analisado: `8d79970f21947631f0140143ee2f4cd8bf2f4796`.

## Resultados reais

| Evidência | Resultado |
|---|---|
| `pytest.txt` e `pytest.xml` | 10 testes passaram, nenhuma falha |
| `validation.json` | 11 verificações passaram |
| Template | Compila com apenas a variável `bug_report`; mensagens system/user separadas |
| Dataset | 15 exemplos, com `bug_report` e `reference` |
| SDK instalado | Aceita os parâmetros usados para pull e push públicos |
| Integridade da base | SHA dos três arquivos protegidos e do dataset conferidos com a base |

## Como reproduzir

Na raiz do repositório, com o ambiente virtual ativado e dependências instaladas:

```bash
python -m pytest tests/test_prompts.py -v --tb=short --junitxml=docs/evidence/pytest.xml > docs/evidence/pytest.txt 2>&1
python docs/evidence/validate_local.py > docs/evidence/validation.json
```

O relatório JSON identifica o commit de código usado nesta auditoria. Ao alterar o código, registre o novo commit antes de gerar novas evidências. A validação não chama provedores nem o LangSmith. As assinaturas do SDK são verificadas offline; isso não comprova sucesso de autenticação ou publicação.

## Pendências para aprovação do desafio

- Configurar `.env`, handle público do Hub e modelos disponíveis.
- Executar pull, push público e avaliação real dos 15 exemplos no LangSmith.
- Registrar as iterações e comprovar as cinco métricas ≥ 0.8.
- Publicar o link compartilhado do dataset e o link público do prompt.
- Adicionar screenshots das notas, do dataset e traces de pelo menos três exemplos.
- Preencher os resultados finais e os modelos no README principal.

Não foram produzidas notas, screenshots ou traces simulados. As credenciais não estão disponíveis no ambiente desta execução. Testes locais aprovados não representam aprovação nas métricas do desafio.
