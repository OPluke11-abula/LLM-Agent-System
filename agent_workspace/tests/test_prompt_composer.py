import os
import sys
import tempfile
import pytest
from pathlib import Path
from jinja2 import Template

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.prompt_composer import PromptComposer


@pytest.fixture
def mock_prompts_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create standard PAP structure for prompts
        pap_dir = temp_path / ".agent"
        prompts_dir = pap_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Create config.yaml
        with open(temp_path / "config.yaml", "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        yield temp_dir


def test_prompt_composer_happy_path(mock_prompts_env):
    temp_path = Path(mock_prompts_env)
    
    # Create mock prompt template file
    prompt_md = """---
id: welcome_msg
template: "Hello {{ name }}, welcome to {{ studio_name }}!"
variables:
  - name
  - studio_name
version: "1.0.0"
---
# Welcome Message Doc
"""
    prompt_file = temp_path / ".agent" / "prompts" / "welcome_msg.md"
    prompt_file.write_text(prompt_md, encoding="utf-8")
    
    # Initialize PromptComposer pointing to our mock directory
    composer = PromptComposer(workspace_path=os.path.join(mock_prompts_env, "agent_workspace"))
    
    # Render prompt
    rendered = composer.build(
        prompt_id="welcome_msg",
        variables={"name": "Alice", "studio_name": "FindAi Studio"}
    )
    
    assert rendered == "Hello Alice, welcome to FindAi Studio!"


def test_prompt_composer_missing_variables(mock_prompts_env):
    temp_path = Path(mock_prompts_env)
    
    prompt_md = """---
id: test_vars
template: "Hello {{ a }} and {{ b }}"
variables:
  - a
  - b
version: "1.0.0"
---
"""
    prompt_file = temp_path / ".agent" / "prompts" / "test_vars.md"
    prompt_file.write_text(prompt_md, encoding="utf-8")
    
    composer = PromptComposer(workspace_path=os.path.join(mock_prompts_env, "agent_workspace"))
    
    # Missing variable 'b'
    with pytest.raises(ValueError) as excinfo:
        composer.build("test_vars", {"a": "Alice"})
    assert "Missing required variables" in str(excinfo.value)
    assert "b" in str(excinfo.value)


def test_prompt_composer_ssti_protection(mock_prompts_env):
    temp_path = Path(mock_prompts_env)
    
    prompt_md = """---
id: ssti_test
template: "Greeting: {{ user_input }}"
variables:
  - user_input
version: "1.0.0"
---
"""
    prompt_file = temp_path / ".agent" / "prompts" / "ssti_test.md"
    prompt_file.write_text(prompt_md, encoding="utf-8")
    
    composer = PromptComposer(workspace_path=os.path.join(mock_prompts_env, "agent_workspace"))
    
    # Malicious SSTI payload trying to inject Jinja2 expressions
    malicious_input = "{{ 7 * 7 }} {% if True %}SSTI{% endif %}"
    
    rendered = composer.build("ssti_test", {"user_input": malicious_input})
    
    # Check that it contains the escaped literal placeholders
    assert '{% raw %}{{{% endraw %}' in rendered or '{% raw %}}}{% endraw %}' in rendered
    
    # Verify that a second-pass rendering of the output results in safe literal text without executing SSTI
    second_pass = Template(rendered).render()
    assert "49" not in second_pass
    assert "SSTI" in second_pass  # "SSTI" string appears as literal text, but let's check exact literal representation
    assert second_pass == "Greeting: {{ 7 * 7 }} {% if True %}SSTI{% endif %}"
