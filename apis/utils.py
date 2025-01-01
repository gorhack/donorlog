from typing import Optional, Dict, Union

from fastapi import Request, HTTPException, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel, OAuthFlowAuthorizationCode
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError
from jose.exceptions import JWTClaimsError, ExpiredSignatureError

from core.jwt_token import verify_jwt
from core.user_token import UserTokenId


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
            authorizationCode=OAuthFlowAuthorizationCode(
                authorizationUrl=authorizationUrl,
                tokenUrl=tokenUrl,
                refreshUrl=refreshUrl,
                scopes=scopes)
        )
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    @staticmethod
    def create_unauthorized_error(detail: str):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def __call__(
        self, request: Request
    ) -> Union[None, UserTokenId, RedirectResponse]:
        # Authorization and access tokens are application Tokens (JWT, etc)
        authorization: str = request.cookies.get("access_token")
        if not authorization:
            authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise self.create_unauthorized_error("Not authenticated.")
            else:
                return None
        try:
            token = verify_jwt(param)
            return token
        except ExpiredSignatureError:
            if self.auto_error:
                raise self.create_unauthorized_error("Token Expired.")
            else:
                return None
        except (JWTError, JWTClaimsError):
            if self.auto_error:
                raise self.create_unauthorized_error(
                    "Not authenticated: Invalid Token."
                )
            else:
                return None
