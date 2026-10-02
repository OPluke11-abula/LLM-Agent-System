import pytest

from agent_workspace.core.providers import ProviderFactory


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://169.254.169.254/latest/meta-data",
        "https://attacker.example/v1",
        "https://user:pass@api.openai.com/v1",
    ],
)
def test_provider_factory_rejects_unsafe_base_urls(base_url):
    with pytest.raises(ValueError):
        ProviderFactory.get_provider("openai", base_url=base_url)


def test_provider_factory_accepts_official_and_local_provider_urls():
    assert ProviderFactory.get_provider(
        "openai", base_url="https://api.openai.com/v1"
    ).base_url == "https://api.openai.com/v1"
    assert ProviderFactory.get_provider(
        "ollama", base_url="http://127.0.0.1:11434"
    ).base_url == "http://127.0.0.1:11434"


@pytest.mark.anyio
async def test_openai_rejects_unsafe_runtime_config_url_before_http():
    provider = ProviderFactory.get_provider("openai", api_key="test-key")

    def fail_if_http_client_created(timeout):
        raise AssertionError("unsafe provider URL reached the HTTP client")

    provider._http_client = fail_if_http_client_created
    result = await provider.complete(
        "system", [], [], {"base_url": "https://attacker.example/v1"}
    )

    assert result[0] == "error"
    assert "not allowed" in result[1]
