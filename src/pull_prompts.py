"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

Uso:
    python src/pull_prompts.py
"""

import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

# Prompt semente publicado pelo desafio
SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"

# Destino local (relativo à raiz do projeto, independente de onde o script é chamado)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "prompts" / "bug_to_user_story_v1.yml"

# Mapeia o tipo da mensagem do LangChain para o campo correspondente no YAML
ROLE_TO_FIELD = {
    "system": "system_prompt",
    "human": "user_prompt",
    "user": "user_prompt",
}


def _message_role(message) -> str:
    """
    Descobre o papel (system/human/ai) de uma mensagem de um ChatPromptTemplate.

    Funciona tanto para templates (SystemMessagePromptTemplate, ...) quanto para
    mensagens fixas (SystemMessage, ...).
    """
    class_name = type(message).__name__.lower()
    if class_name.startswith("system"):
        return "system"
    if class_name.startswith("human"):
        return "human"
    if class_name.startswith(("ai", "assistant")):
        return "ai"
    return getattr(message, "type", "unknown")


def _message_text(message) -> str:
    """Extrai o texto bruto (com as variáveis {…}) de uma mensagem do template."""
    inner = getattr(message, "prompt", None)
    if inner is not None and hasattr(inner, "template"):
        return inner.template
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)


def prompt_to_dict(prompt: ChatPromptTemplate, prompt_identifier: str) -> dict:
    """
    Converte um ChatPromptTemplate no mesmo formato YAML usado pelo projeto.
    """
    data = {
        "description": "Prompt para converter relatos de bugs em User Stories",
        "system_prompt": "",
        "user_prompt": "",
    }

    for message in prompt.messages:
        role = _message_role(message)
        field = ROLE_TO_FIELD.get(role)
        if field is None:
            continue
        text = _message_text(message)
        # Se houver mais de uma mensagem do mesmo papel, concatena preservando a ordem
        data[field] = f"{data[field]}\n\n{text}".strip() if data[field] else text

    data["input_variables"] = sorted(prompt.input_variables)
    data["version"] = "v1"
    data["source"] = prompt_identifier
    data["pulled_at"] = date.today().isoformat()
    data["tags"] = ["bug-analysis", "user-story", "product-management"]

    return data


def pull_prompts_from_langsmith(prompt_identifier: str = SOURCE_PROMPT,
                                output_file: Path = OUTPUT_FILE) -> bool:
    """
    Faz pull do prompt no LangSmith Hub e salva em YAML.

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"Conectando ao LangSmith e puxando: {prompt_identifier}")

    try:
        client = Client()
        # O pull de prompts "owner/nome" é bloqueado por padrão, pois o objeto é
        # LangChain serializado vindo de terceiros. Aqui é o prompt semente do
        # desafio, então o risco é conhecido.
        prompt = client.pull_prompt(
            prompt_identifier,
            dangerously_pull_public_prompt=True,
        )
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY no .env")
        print(f"- Se o prompt '{prompt_identifier}' existe e é público")
        return False

    if not isinstance(prompt, ChatPromptTemplate):
        print(f"❌ Tipo de prompt inesperado: {type(prompt).__name__}")
        return False

    print(f"   ✓ Prompt carregado ({len(prompt.messages)} mensagens)")
    print(f"   ✓ Variáveis de entrada: {prompt.input_variables}")

    prompt_key = prompt_identifier.split("/")[-1]
    payload = {prompt_key: prompt_to_dict(prompt, prompt_identifier)}

    if not save_yaml(payload, str(output_file)):
        return False

    print(f"   ✓ Salvo em: {output_file.relative_to(PROJECT_ROOT)}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    if not pull_prompts_from_langsmith():
        return 1

    print("\n✅ Pull concluído com sucesso!")
    print("\nPróximo passo: analise prompts/bug_to_user_story_v1.yml e")
    print("refatore em prompts/bug_to_user_story_v2.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
