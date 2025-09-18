import os
from dataclasses import dataclass


@dataclass
class Settings:
    tenant_id: str
    client_id: str
    graph_host: str = "https://graph.microsoft.com/v1.0"
    token_cache_path: str = ".token_cache.bin"


def load_settings() -> Settings:
    tenant_id = os.getenv("AZURE_TENANT_ID", "common")
    client_id = os.getenv("AZURE_CLIENT_ID", "da1c90d2-e826-43b6-b2d5-836f9f2898c7")
    graph_host = os.getenv("GRAPH_HOST", "https://graph.microsoft.com/v1.0")
    token_cache_path = os.getenv("TOKEN_CACHE_PATH", ".token_cache.bin")
    return Settings(
        tenant_id=tenant_id,
        client_id=client_id,
        graph_host=graph_host,
        token_cache_path=token_cache_path,
    )


