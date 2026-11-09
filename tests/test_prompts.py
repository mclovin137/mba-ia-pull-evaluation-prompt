"""
Testes automatizados para validação de prompts.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure  # noqa: E402

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data() -> dict:
    data = load_prompts(str(PROMPT_FILE))
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada no YAML"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt_data) -> str:
    return prompt_data.get("system_prompt", "")


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data
        assert isinstance(prompt_data["system_prompt"], str)
        assert prompt_data["system_prompt"].strip() != ""

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é (um|uma)\s+\w+", system_prompt), \
            "O system_prompt deve definir uma persona com 'Você é um/uma ...'"
        roles = ["product owner", "product manager", "analista", "especialista"]
        assert any(role in system_prompt.lower() for role in roles), \
            "A persona deve indicar um papel de produto/análise"

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = system_prompt.lower()
        assert "user story" in text or "markdown" in text
        # Estrutura padrão de User Story e critérios BDD
        assert "como um" in text and "eu quero" in text and "para que" in text
        assert "critérios de aceitação" in text
        assert all(k in text for k in ("dado que", "quando", "então"))

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        assert re.search(r"exemplo", system_prompt, re.IGNORECASE)
        inputs = re.findall(r"^\s*Entrada:", system_prompt, re.MULTILINE)
        outputs = re.findall(r"^\s*Saída:", system_prompt, re.MULTILINE)
        assert len(inputs) >= 2, "São necessários pelo menos 2 exemplos de entrada"
        assert len(inputs) == len(outputs), "Cada entrada deve ter uma saída correspondente"

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        full_text = yaml.safe_dump(prompt_data, allow_unicode=True)
        assert "[TODO]" not in full_text
        assert "TODO" not in full_text

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert any("few-shot" in t.lower() for t in techniques), \
            "Few-shot Learning é obrigatório"

    # ---- Testes extras ----

    def test_structure_is_valid(self, prompt_data):
        """Usa o validador do projeto (utils.validate_prompt_structure)."""
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, errors

    def test_bug_report_only_in_user_prompt(self, prompt_data):
        """A entrada do usuário fica no user prompt (separação System vs User)."""
        assert "{bug_report}" in prompt_data["user_prompt"]
        assert "{bug_report}" not in prompt_data["system_prompt"]

    def test_template_has_only_expected_variables(self, prompt_data):
        """O template deve compilar e expor apenas a variável bug_report."""
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ])
        assert prompt.input_variables == ["bug_report"]

    def test_prompt_handles_edge_cases(self, system_prompt):
        """O prompt deve ter uma seção explícita de edge cases."""
        assert "edge case" in system_prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
