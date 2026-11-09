"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

Uso:
    python src/push_prompts.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = PROJECT_ROOT / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_NAME = "bug_to_user_story_v2"

# Variável de entrada usada pelo dataset de avaliação
REQUIRED_VARIABLE = "bug_report"


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate (system + user) a partir do YAML."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def build_readme(prompt_data: dict) -> str:
    """Gera um README curto exibido na página do prompt no Hub."""
    techniques = prompt_data.get("techniques_applied", [])
    lines = [
        f"# {PROMPT_NAME}",
        "",
        prompt_data.get("description", ""),
        "",
        f"**Versão:** {prompt_data.get('version', '')}",
        "",
        "## Técnicas aplicadas",
        "",
    ]
    lines += [f"- {t}" for t in techniques]
    lines += [
        "",
        "## Entrada",
        "",
        f"- `{{{REQUIRED_VARIABLE}}}`: relato de bug em texto livre",
    ]
    return "\n".join(lines)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    identifier = f"{username}/{prompt_name}"

    try:
        prompt = build_chat_prompt(prompt_data)
    except Exception as e:
        print(f"❌ Erro ao montar o ChatPromptTemplate: {e}")
        print("   Dica: chaves literais no texto precisam ser escapadas como {{ }}")
        return False

    if REQUIRED_VARIABLE not in prompt.input_variables:
        print(f"❌ O template precisa usar a variável {{{REQUIRED_VARIABLE}}}")
        return False

    extra_vars = set(prompt.input_variables) - {REQUIRED_VARIABLE}
    if extra_vars:
        print(f"❌ Variáveis inesperadas no template: {sorted(extra_vars)}")
        print("   O dataset só fornece 'bug_report'. Escape chaves literais com {{ }}.")
        return False

    techniques = prompt_data.get("techniques_applied", [])
    tags = list(dict.fromkeys(
        prompt_data.get("tags", [])
        + [t.lower().replace(" ", "-") for t in techniques]
    ))

    description = prompt_data.get("description", "")
    if techniques:
        description = f"{description} | Técnicas: {', '.join(techniques)}"

    print(f"Fazendo push de: {identifier}")
    print(f"   Tags: {tags}")

    try:
        client = Client()
        url = client.push_prompt(
            identifier,
            object=prompt,
            is_public=True,
            description=description[:1000],
            readme=build_readme(prompt_data),
            tags=tags,
            commit_description=prompt_data.get("changelog", f"Versão {prompt_data.get('version', '')}"),
        )
    except Exception as e:
        message = str(e)
        if "nothing to commit" in message.lower() or "409" in message:
            print("   ℹ️  Nenhuma alteração desde o último push (commit idêntico).")
            return True
        print(f"❌ Erro ao fazer push: {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY no .env")
        print("- USERNAME_LANGSMITH_HUB é o seu handle público do Hub")
        print("  (ele só existe depois de tornar algum prompt público pela UI)")
        return False

    print(f"   ✓ Push realizado: {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    if not isinstance(prompt_data, dict):
        return False, ["Conteúdo do prompt não é um dicionário"]

    for field in ("description", "system_prompt", "user_prompt", "version"):
        value = prompt_data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    full_text = f"{prompt_data.get('system_prompt', '')}\n{prompt_data.get('user_prompt', '')}"

    if "TODO" in full_text:
        errors.append("O prompt ainda contém TODOs")

    if f"{{{REQUIRED_VARIABLE}}}" not in prompt_data.get("user_prompt", ""):
        errors.append(f"user_prompt deve conter a variável {{{REQUIRED_VARIABLE}}}")

    if f"{{{REQUIRED_VARIABLE}}}" in prompt_data.get("system_prompt", ""):
        errors.append(
            f"{{{REQUIRED_VARIABLE}}} não deve ficar no system_prompt "
            "(a entrada do usuário pertence ao user_prompt)"
        )

    techniques = prompt_data.get("techniques_applied", [])
    if not isinstance(techniques, list) or len(techniques) < 2:
        errors.append("Liste pelo menos 2 técnicas em techniques_applied")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_FILE))
    if not data:
        return 1

    prompt_data = data.get(PROMPT_NAME)
    if prompt_data is None:
        print(f"❌ Chave '{PROMPT_NAME}' não encontrada em {PROMPT_FILE.name}")
        return 1

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for err in errors:
            print(f"   - {err}")
        return 1
    print("   ✓ Prompt validado")

    if not push_prompt_to_langsmith(PROMPT_NAME, prompt_data):
        return 1

    print("\n✅ Push concluído! Próximo passo: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
