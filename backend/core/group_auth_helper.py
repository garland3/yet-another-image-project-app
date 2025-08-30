"""
Group authorization helper functions with caching and utilities.
Provides performance optimizations and convenience wrappers around core auth.
"""

import time
import logging
from typing import Dict, Tuple, List
from .group_auth import is_user_in_group as _core_is_user_in_group

logger = logging.getLogger(__name__)

# Simple in-memory cache for group membership checks
# Format: {(user_email, group_id): (is_member, timestamp)}
_group_membership_cache: Dict[Tuple[str, str], Tuple[bool, float]] = {}
_CACHE_TTL = 300  # 5 minutes


def is_user_in_group(user_email: str, group_id: str) -> bool:
    """
    Cached wrapper around core group membership check.
    
    Args:
        user_email: The user's email address
        group_id: The group ID to check membership for
        
    Returns:
        True if user is in the group, False otherwise
    """
    if not user_email or not group_id:
        return False
    
    # Normalize inputs for consistent caching
    user_email = user_email.lower().strip()
    group_id = group_id.strip()
    
    cache_key = (user_email, group_id)
    current_time = time.time()
    
    # Check cache first
    if cache_key in _group_membership_cache:
        is_member, cached_time = _group_membership_cache[cache_key]
        if current_time - cached_time < _CACHE_TTL:
            logger.debug(f"Cache hit: {user_email} in {group_id} = {is_member}")
            return is_member
        else:
            # Cache expired, remove entry
            del _group_membership_cache[cache_key]
            logger.debug(f"Cache expired for: {user_email} in {group_id}")
    
    # Call core auth function
    is_member = _core_is_user_in_group(user_email, group_id)
    
    # Cache the result
    _group_membership_cache[cache_key] = (is_member, current_time)
    logger.debug(f"Cached result: {user_email} in {group_id} = {is_member}")
    
    return is_member


def is_user_in_any_group(user_email: str, group_ids: List[str]) -> bool:
    """
    Check if user is in any of the provided groups.
    
    Args:
        user_email: The user's email address
        group_ids: List of group IDs to check membership for
        
    Returns:
        True if user is in any of the groups, False otherwise
    """
    if not user_email or not group_ids:
        return False
    
    for group_id in group_ids:
        if is_user_in_group(user_email, group_id):
            return True
    
    return False


def is_user_in_all_groups(user_email: str, group_ids: List[str]) -> bool:
    """
    Check if user is in all of the provided groups.
    
    Args:
        user_email: The user's email address
        group_ids: List of group IDs to check membership for
        
    Returns:
        True if user is in all of the groups, False otherwise
    """
    if not user_email or not group_ids:
        return False
    
    for group_id in group_ids:
        if not is_user_in_group(user_email, group_id):
            return False
    
    return True


def get_user_groups(user_email: str, candidate_groups: List[str]) -> List[str]:
    """
    Get list of groups that the user is a member of from the candidate list.
    
    Args:
        user_email: The user's email address
        candidate_groups: List of group IDs to check membership for
        
    Returns:
        List of group IDs the user is a member of
    """
    if not user_email or not candidate_groups:
        return []
    
    user_groups = []
    for group_id in candidate_groups:
        if is_user_in_group(user_email, group_id):
            user_groups.append(group_id)
    
    return user_groups


def clear_cache() -> None:
    """
    Clear the entire group membership cache.
    Useful for testing or when auth system changes.
    """
    global _group_membership_cache
    _group_membership_cache.clear()
    logger.info("Group membership cache cleared")


def clear_user_cache(user_email: str) -> None:
    """
    Clear cache entries for a specific user.
    
    Args:
        user_email: The user's email address to clear from cache
    """
    if not user_email:
        return
    
    user_email = user_email.lower().strip()
    keys_to_remove = [key for key in _group_membership_cache.keys() if key[0] == user_email]
    
    for key in keys_to_remove:
        del _group_membership_cache[key]
    
    logger.info(f"Cleared cache for user: {user_email}")


def get_cache_stats() -> Dict[str, int]:
    """
    Get cache statistics for monitoring/debugging.
    
    Returns:
        Dictionary with cache statistics
    """
    current_time = time.time()
    valid_entries = 0
    expired_entries = 0
    
    for (is_member, cached_time) in _group_membership_cache.values():
        if current_time - cached_time < _CACHE_TTL:
            valid_entries += 1
        else:
            expired_entries += 1
    
    return {
        "total_entries": len(_group_membership_cache),
        "valid_entries": valid_entries,
        "expired_entries": expired_entries,
        "cache_ttl_seconds": _CACHE_TTL
    }