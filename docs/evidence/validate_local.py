"""Validação offline; não chama LLMs nem publica dados no LangSmith.

Execute da raiz: python docs/evidence/validate_local.py
"""
import hashlib
import inspect
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import sys

import yaml
from langsmith import Client

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from push_prompts import build_chat_prompt, validate_prompt

BASE_SHA = '8d79970f21947631f0140143ee2f4cd8bf2f4796'
# Hashes conferidos com o repositório devfullcycle/mba-ia-pull-evaluation-prompt.
EXPECTED = {
    'src/evaluate.py': 'f9f2bdd90dc14b7d6556b627afb7c4c10c70d59a',
    'src/metrics.py': 'b80f12e3c19bbccdfd97e76255916200239b4a7b',
    'src/utils.py': '239d0c8974f0ea34946344fc7e21b84399144a7b',
    'datasets/bug_to_user_story.jsonl': 'e7132dc89ad34a401fc6e1f07c84449b6ba72cfa',
}

def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

data = yaml.safe_load((ROOT / 'prompts/bug_to_user_story_v2.yml').read_text())['bug_to_user_story_v2']
valid, errors = validate_prompt(data)
prompt = build_chat_prompt(data)
rendered = prompt.invoke({'bug_report': 'Botão de login não responde.'})
rows = [json.loads(line) for line in (ROOT / 'datasets/bug_to_user_story.jsonl').read_text().splitlines() if line.strip()]
checks = {
    'prompt_validation': valid and not errors,
    'only_bug_report_variable': prompt.input_variables == ['bug_report'],
    'system_user_roles': [m.type for m in rendered.messages] == ['system', 'human'],
    'dataset_15_examples': len(rows) == 15,
    'dataset_required_fields': all('bug_report' in row['inputs'] and 'reference' in row['outputs'] for row in rows),
    'sdk_supports_public_pull': 'dangerously_pull_public_prompt' in inspect.signature(Client.pull_prompt).parameters,
    'sdk_supports_public_push': 'is_public' in inspect.signature(Client.push_prompt).parameters,
}
checks.update({f'base_unchanged:{p}': sha == git_blob_sha((ROOT / p).read_bytes()) for p, sha in EXPECTED.items()})
report = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'source_commit': BASE_SHA,
    'python': platform.python_version(),
    'packages': {p: version(p) for p in ['pytest', 'langchain-core', 'langsmith', 'pyyaml']},
    'checks': checks,
    'passed': all(checks.values()),
    'scope': 'Validação local sem chamadas externas. Não comprova publicação, tracing ou notas no LangSmith.',
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['passed'] else 1)
