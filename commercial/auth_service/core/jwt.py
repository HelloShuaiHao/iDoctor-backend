"""JWT token decoding and validation"""
from typing import Optional
from .security import verify_token


def decode_access_token(token: str) -> dict:
    """解码并验证访问令牌
    
    Args:
        token: JWT访问令牌
        
    Returns:
        dict: Token的payload
        
    Raises:
        ValueError: 如果token无效或验证失败
    """
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise ValueError("Invalid or expired access token")
    return payload
