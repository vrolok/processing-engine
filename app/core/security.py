### Core application infrastructure:
### Security (security.py):
# - Azure AD authentication integration
# - User context extraction and validation
# - Token handling and verification

from typing import Any
from fastapi import HTTPException, Depends, status
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from config import settings

# Azure AD authentication scheme
azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=settings.APP_CLIENT_ID,
    tenant_id=settings.TENANT_ID,
    scopes={f'api://{settings.API_SCOPE}/.default': 'read'}
)

async def get_current_user(token: str = Depends(azure_scheme)) -> dict[str, Any]:
    """
    Validate and decode the JWT token to get current user.
    """
    try:
        # Token is already validated by azure_scheme
        return {
            "id": token.get("oid"),
            "email": token.get("email"),
            "name": token.get("name"),
            "roles": token.get("roles", [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )