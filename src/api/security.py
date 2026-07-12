import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(key: str = Security(api_key_header)) -> str:
    """
    Valida a API Key enviada no header da requisição.

    OWASP: Broken Authentication — garante que só
    requisições autenticadas acessam os endpoints.

    Args:
        key: chave enviada no header X-API-Key

    Raises:
        HTTPException 403 se a chave for inválida
    """
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida ou ausente.",
        )
    return key