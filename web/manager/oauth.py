__all__ = ('OauthManager',)

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import timedelta
from os import urandom
from typing import Iterable, List, Optional, Tuple
from urllib.parse import SplitResult, urlsplit

from flask import g
from sqlalchemy import select, update

from commons.models import AccessToken, OauthApp
from web.config import RedisConfig
from web.const import api_scopes
from web.utils import db, redis_connect

redis = redis_connect()

def randtoken() -> str:
    return 'acmoj-' + urandom(16).hex()

def port(uri: SplitResult) -> int:
    if uri.port is not None: return uri.port
    implicit_map = { 'http': 80, 'https': 443 }
    return implicit_map[uri.scheme]

class OauthManager:
    @staticmethod
    def get_app(client_id: str) -> Optional[OauthApp]:
        return db.scalar(select(OauthApp).where(OauthApp.client_id == client_id))

    @staticmethod
    def from_app_id(id: int) -> Optional[OauthApp]:
        return db.get(OauthApp, id)

    @staticmethod
    def scope_is_valid(app: OauthApp, scope: str) -> bool:
        return scope in api_scopes and scope in app.scopes

    @staticmethod
    def redirect_uri_is_valid(app: OauthApp, redirect_uri: str) -> bool:
        uri = urlsplit(redirect_uri)
        if uri.username is not None or uri.password is not None or uri.scheme not in ('http', 'https'):
            return False
        recorded = urlsplit(app.redirect_uri)
        return (
            uri.scheme == recorded.scheme and
            uri.hostname == recorded.hostname and
            port(uri) == port(recorded) and
            uri.path.startswith(recorded.path)
        )

    @staticmethod
    def create_code(app: OauthApp, redirect_uri: str, scopes: Iterable[str]) -> str:
        code = randtoken()
        redirect_uri = urlsafe_b64encode(redirect_uri.encode()).decode()
        scope = urlsafe_b64encode(' '.join(scopes).encode()).decode()
        redis.set(f'{RedisConfig.prefix}oauth:code:{code}', f'{app.id}:{g.user.id}:{redirect_uri}:{scope}', ex=60)
        return code

    # returns userid, scopes
    @staticmethod
    def use_code(app: OauthApp, redirect_uri: Optional[str], code: str) -> Optional[Tuple[int, List[str]]]:
        key = f'{RedisConfig.prefix}oauth:code:{code}'
        info = redis.get(key)
        delcount = redis.delete(key)
        if delcount < 1: return None

        app_id, user_id, redirect_uri_recorded, scope = info.split(':')
        redirect_uri_recorded = urlsafe_b64decode(redirect_uri_recorded.encode()).decode()
        scopes = urlsafe_b64decode(scope.encode()).decode().split(' ')
        if int(app_id) != app.id:
            return None
        if redirect_uri is not None and redirect_uri_recorded != redirect_uri:
            return None
        return int(user_id), scopes

    @classmethod
    def create_access_token(cls, app: OauthApp, user_id: int, scopes: List[str]) -> AccessToken:
        if any(not cls.scope_is_valid(app, scope) for scope in scopes):
            raise ValueError('Invalid scope')

        token = AccessToken()
        token.token = randtoken()
        token.user_id = user_id
        token.scopes = scopes
        token.app_id = app.id
        token.expires_at = g.time + timedelta(days=365)
        db.add(token)
        return token

    @staticmethod
    def revoke_app(app: OauthApp):
        db.execute(
            update(AccessToken)
            .where(AccessToken.user_id == g.user.id)
            .where(AccessToken.app_id == app.id)
            .where(g.time < AccessToken.expires_at)
            .where(AccessToken.revoked_at == None)
            .values(revoked_at=g.time)
        )
        db.flush()
