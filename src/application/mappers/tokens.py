def whitelist_key(user_id: str, device_id: str)->str:
    return f"whitelist:access:{user_id}:{device_id}"


def refresh_key(user_id: str, device_id: str) -> str:
    return f"whitelist:refresh:{user_id}:{device_id}"


def blacklist_key(token: str) -> str:
    return f"blacklist:token:{token}"
