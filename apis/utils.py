from typing import Optional, Dict

from fastapi import Request, HTTPException, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError
from jose.exceptions import JWTClaimsError, ExpiredSignatureError

from core.jwt_token import verify_jwt
from core.token import UserTokenId


# noinspection PyPep8Naming
class OAuth2AuthorizationWithCookie(OAuth2):
    def __init__(
        self,
        authorizationUrl: str,
        tokenUrl: str,
        refreshUrl: Optional[str] = None,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            authorizationCode={
                "authorizationUrl": authorizationUrl,
                "tokenUrl": tokenUrl,
                "refreshUrl": refreshUrl,
                "scopes": scopes,
            }
        )
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request: Request) -> Optional[UserTokenId]:
        # Authorization and access tokens are application Tokens (JWT, etc)
        authorization: str = request.cookies.get("access_token")
        if not authorization:
            authorization: str = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        try:
            token = verify_jwt(token)
            return token
        except (JWTError, ExpiredSignatureError, JWTClaimsError):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Not authenticated: Invalid Token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
