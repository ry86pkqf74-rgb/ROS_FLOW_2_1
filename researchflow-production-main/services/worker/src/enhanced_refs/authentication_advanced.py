"""
Advanced Authentication & Authorization System for AI Bridge

Enterprise-grade authentication with:
- Multi-provider authentication (API keys, JWT, OAuth2)
- Role-based access control (RBAC)
- Organization-level permissions
- Rate limiting per user tier
- API key management
- Session management
- Audit logging

Author: AI Bridge Enhancement Team
"""

import logging
import asyncio
import jwt
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles with hierarchical permissions."""
    SUPER_ADMIN = "super_admin"        # Full system access
    ORG_ADMIN = "org_admin"           # Organization administration
    PROJECT_MANAGER = "project_manager"  # Project management
    RESEARCHER = "researcher"          # Research operations
    ANALYST = "analyst"               # Data analysis
    VIEWER = "viewer"                 # Read-only access
    API_USER = "api_user"             # API-only access

class UserTier(Enum):
    """User tiers for rate limiting and feature access."""
    FREE = "free"                     # Basic free tier
    BASIC = "basic"                   # Basic paid tier
    PROFESSIONAL = "professional"     # Professional tier
    ENTERPRISE = "enterprise"         # Enterprise tier
    UNLIMITED = "unlimited"           # Unlimited access

class PermissionScope(Enum):
    """Permission scopes for fine-grained access control."""
    # Core operations
    REFERENCES_READ = "references:read"
    REFERENCES_WRITE = "references:write"
    REFERENCES_DELETE = "references:delete"
    
    # AI features
    AI_BASIC = "ai:basic"
    AI_ADVANCED = "ai:advanced"
    AI_PREMIUM = "ai:premium"
    
    # Analytics and monitoring
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_WRITE = "analytics:write"
    
    # Administration
    USER_MANAGEMENT = "users:manage"
    ORGANIZATION_MANAGEMENT = "organizations:manage"
    SYSTEM_ADMINISTRATION = "system:admin"
    
    # Billing and costs
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    
    # API management
    API_KEYS_MANAGE = "api_keys:manage"

@dataclass
class UserProfile:
    """User profile with authentication and authorization info."""
    user_id: str
    username: str
    email: str
    
    # Authentication
    password_hash: Optional[str] = None
    api_keys: List[str] = field(default_factory=list)
    
    # Authorization
    role: UserRole = UserRole.VIEWER
    tier: UserTier = UserTier.FREE
    permissions: Set[PermissionScope] = field(default_factory=set)
    
    # Organization
    organization_id: Optional[str] = None
    organization_role: Optional[str] = None
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    daily_cost_limit_usd: float = 10.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "tier": self.tier.value,
            "permissions": [p.value for p in self.permissions],
            "organization_id": self.organization_id,
            "organization_role": self.organization_role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "rate_limits": {
                "per_minute": self.rate_limit_per_minute,
                "per_hour": self.rate_limit_per_hour,
                "daily_cost_limit_usd": self.daily_cost_limit_usd
            }
        }
    
    def has_permission(self, permission: PermissionScope) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions or self.role in [UserRole.SUPER_ADMIN]
    
    def can_access_ai_feature(self, feature_tier: str) -> bool:
        """Check if user can access AI feature based on tier."""
        tier_access = {
            "basic": [UserTier.BASIC, UserTier.PROFESSIONAL, UserTier.ENTERPRISE, UserTier.UNLIMITED],
            "advanced": [UserTier.PROFESSIONAL, UserTier.ENTERPRISE, UserTier.UNLIMITED],
            "premium": [UserTier.ENTERPRISE, UserTier.UNLIMITED]
        }
        return self.tier in tier_access.get(feature_tier, [])

@dataclass
class APIKey:
    """API key with metadata and permissions."""
    key_id: str
    key_hash: str
    user_id: str
    
    # Metadata
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Permissions
    scopes: Set[PermissionScope] = field(default_factory=set)
    rate_limit_override: Optional[int] = None
    
    # Status
    is_active: bool = True
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key_id": self.key_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "scopes": [s.value for s in self.scopes],
            "is_active": self.is_active,
            "usage_count": self.usage_count
        }
    
    def is_valid(self) -> bool:
        """Check if API key is valid."""
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True

class AuthenticationManager:
    """
    Advanced authentication and authorization manager.
    
    Handles multiple authentication methods and provides comprehensive
    user management and permission checking.
    """
    
    def __init__(self, 
                 jwt_secret: str = "your-secret-key",
                 jwt_algorithm: str = "HS256",
                 jwt_expiry_hours: int = 24):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expiry_hours = jwt_expiry_hours
        
        # In-memory storage (replace with database in production)
        self.users: Dict[str, UserProfile] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.user_by_email: Dict[str, str] = {}
        self.user_by_username: Dict[str, str] = {}
        
        # Rate limiting tracking
        self.rate_limit_buckets: Dict[str, Dict[str, List[datetime]]] = {}
        
        # Initialize default permissions for roles
        self._setup_default_role_permissions()
        
        logger.info("Authentication Manager initialized")
    
    def _setup_default_role_permissions(self):
        """Setup default permissions for each role."""
        self.role_permissions = {
            UserRole.SUPER_ADMIN: set(PermissionScope),  # All permissions
            UserRole.ORG_ADMIN: {
                PermissionScope.REFERENCES_READ, PermissionScope.REFERENCES_WRITE,
                PermissionScope.AI_BASIC, PermissionScope.AI_ADVANCED,
                PermissionScope.ANALYTICS_READ, PermissionScope.ANALYTICS_WRITE,
                PermissionScope.USER_MANAGEMENT, PermissionScope.BILLING_READ
            },
            UserRole.PROJECT_MANAGER: {
                PermissionScope.REFERENCES_READ, PermissionScope.REFERENCES_WRITE,
                PermissionScope.AI_BASIC, PermissionScope.AI_ADVANCED,
                PermissionScope.ANALYTICS_READ
            },
            UserRole.RESEARCHER: {
                PermissionScope.REFERENCES_READ, PermissionScope.REFERENCES_WRITE,
                PermissionScope.AI_BASIC, PermissionScope.ANALYTICS_READ
            },
            UserRole.ANALYST: {
                PermissionScope.REFERENCES_READ, PermissionScope.AI_BASIC,
                PermissionScope.ANALYTICS_READ
            },
            UserRole.VIEWER: {
                PermissionScope.REFERENCES_READ
            },
            UserRole.API_USER: {
                PermissionScope.REFERENCES_READ, PermissionScope.REFERENCES_WRITE,
                PermissionScope.AI_BASIC
            }
        }
    
    async def create_user(self, 
                         username: str,
                         email: str,
                         password: str,
                         role: UserRole = UserRole.VIEWER,
                         tier: UserTier = UserTier.FREE,
                         organization_id: Optional[str] = None) -> UserProfile:
        """Create a new user account."""
        try:
            # Validate uniqueness
            if username in self.user_by_username:
                raise ValueError(f"Username '{username}' already exists")
            
            if email in self.user_by_email:
                raise ValueError(f"Email '{email}' already exists")
            
            # Generate user ID
            user_id = self._generate_user_id()
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Set tier-based limits
            rate_limits = self._get_tier_rate_limits(tier)
            
            # Create user profile
            user = UserProfile(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                tier=tier,
                permissions=self.role_permissions.get(role, set()),
                organization_id=organization_id,
                rate_limit_per_minute=rate_limits["per_minute"],
                rate_limit_per_hour=rate_limits["per_hour"],
                daily_cost_limit_usd=rate_limits["daily_cost_limit"]
            )
            
            # Store user
            self.users[user_id] = user
            self.user_by_email[email] = user_id
            self.user_by_username[username] = user_id
            
            logger.info(f"User created: {username} ({email}) with role {role.value}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    def _get_tier_rate_limits(self, tier: UserTier) -> Dict[str, Union[int, float]]:
        """Get rate limits based on user tier."""
        tier_limits = {
            UserTier.FREE: {"per_minute": 10, "per_hour": 100, "daily_cost_limit": 1.0},
            UserTier.BASIC: {"per_minute": 60, "per_hour": 1000, "daily_cost_limit": 10.0},
            UserTier.PROFESSIONAL: {"per_minute": 200, "per_hour": 5000, "daily_cost_limit": 50.0},
            UserTier.ENTERPRISE: {"per_minute": 1000, "per_hour": 20000, "daily_cost_limit": 500.0},
            UserTier.UNLIMITED: {"per_minute": 10000, "per_hour": 100000, "daily_cost_limit": 10000.0}
        }
        return tier_limits.get(tier, tier_limits[UserTier.FREE])
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID."""
        return f"usr_{secrets.token_hex(16)}"
    
    async def authenticate_password(self, username_or_email: str, password: str) -> Optional[UserProfile]:
        """Authenticate user with username/email and password."""
        try:
            # Find user
            user_id = None
            if username_or_email in self.user_by_username:
                user_id = self.user_by_username[username_or_email]
            elif username_or_email in self.user_by_email:
                user_id = self.user_by_email[username_or_email]
            
            if not user_id or user_id not in self.users:
                return None
            
            user = self.users[user_id]
            
            # Check if user is active
            if not user.is_active:
                return None
            
            # Verify password
            if user.password_hash and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                # Update last login
                user.last_login = datetime.utcnow()
                logger.info(f"User authenticated: {user.username}")
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def authenticate_api_key(self, api_key: str) -> Optional[UserProfile]:
        """Authenticate user with API key."""
        try:
            # Hash the provided key to find match
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Find API key
            api_key_obj = None
            for key_obj in self.api_keys.values():
                if key_obj.key_hash == key_hash and key_obj.is_valid():
                    api_key_obj = key_obj
                    break
            
            if not api_key_obj:
                return None
            
            # Get associated user
            if api_key_obj.user_id not in self.users:
                return None
            
            user = self.users[api_key_obj.user_id]
            
            if not user.is_active:
                return None
            
            # Update API key usage
            api_key_obj.last_used = datetime.utcnow()
            api_key_obj.usage_count += 1
            
            logger.info(f"API key authenticated for user: {user.username}")
            return user
            
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return None
    
    async def create_jwt_token(self, user: UserProfile) -> str:
        """Create JWT token for user."""
        try:
            payload = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "tier": user.tier.value,
                "organization_id": user.organization_id,
                "exp": datetime.utcnow() + timedelta(hours=self.jwt_expiry_hours),
                "iat": datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            return token
            
        except Exception as e:
            logger.error(f"Error creating JWT token: {e}")
            raise
    
    async def verify_jwt_token(self, token: str) -> Optional[UserProfile]:
        """Verify JWT token and return user."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload.get("user_id")
            
            if user_id and user_id in self.users:
                user = self.users[user_id]
                if user.is_active:
                    return user
            
            return None
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return None
    
    async def create_api_key(self, 
                           user_id: str,
                           name: str,
                           scopes: Optional[Set[PermissionScope]] = None,
                           expires_days: Optional[int] = None) -> Dict[str, str]:
        """Create new API key for user."""
        try:
            if user_id not in self.users:
                raise ValueError("User not found")
            
            user = self.users[user_id]
            
            # Generate API key
            api_key = f"sk_{secrets.token_hex(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_id = f"key_{secrets.token_hex(16)}"
            
            # Set expiration
            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            # Default scopes based on user permissions
            if scopes is None:
                scopes = user.permissions
            else:
                # Ensure user has all requested scopes
                scopes = scopes.intersection(user.permissions)
            
            # Create API key object
            api_key_obj = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                user_id=user_id,
                name=name,
                expires_at=expires_at,
                scopes=scopes
            )
            
            # Store API key
            self.api_keys[key_id] = api_key_obj
            user.api_keys.append(key_id)
            
            logger.info(f"API key created for user {user.username}: {name}")
            
            return {
                "api_key": api_key,
                "key_id": key_id,
                "name": name,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
            
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            raise
    
    async def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        """Revoke an API key."""
        try:
            if key_id not in self.api_keys:
                return False
            
            api_key = self.api_keys[key_id]
            
            # Check ownership
            if api_key.user_id != user_id:
                return False
            
            # Revoke key
            api_key.is_active = False
            
            # Remove from user's key list
            user = self.users[user_id]
            if key_id in user.api_keys:
                user.api_keys.remove(key_id)
            
            logger.info(f"API key revoked: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key: {e}")
            return False
    
    async def check_rate_limit(self, user_id: str, endpoint: str = "default") -> bool:
        """Check if user has exceeded rate limits."""
        try:
            if user_id not in self.users:
                return False
            
            user = self.users[user_id]
            now = datetime.utcnow()
            
            # Initialize rate limit buckets for user
            if user_id not in self.rate_limit_buckets:
                self.rate_limit_buckets[user_id] = {}
            
            if endpoint not in self.rate_limit_buckets[user_id]:
                self.rate_limit_buckets[user_id][endpoint] = []
            
            # Clean old requests (remove requests older than 1 hour)
            bucket = self.rate_limit_buckets[user_id][endpoint]
            cutoff_time = now - timedelta(hours=1)
            bucket[:] = [req_time for req_time in bucket if req_time > cutoff_time]
            
            # Check minute limit
            minute_cutoff = now - timedelta(minutes=1)
            minute_requests = [req_time for req_time in bucket if req_time > minute_cutoff]
            
            if len(minute_requests) >= user.rate_limit_per_minute:
                logger.warning(f"Rate limit exceeded (per minute): {user.username}")
                return False
            
            # Check hourly limit
            if len(bucket) >= user.rate_limit_per_hour:
                logger.warning(f"Rate limit exceeded (per hour): {user.username}")
                return False
            
            # Record this request
            bucket.append(now)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user statistics and usage information."""
        try:
            if user_id not in self.users:
                return None
            
            user = self.users[user_id]
            
            # Calculate API key usage
            api_key_stats = []
            for key_id in user.api_keys:
                if key_id in self.api_keys:
                    key_obj = self.api_keys[key_id]
                    api_key_stats.append({
                        "key_id": key_id,
                        "name": key_obj.name,
                        "usage_count": key_obj.usage_count,
                        "last_used": key_obj.last_used.isoformat() if key_obj.last_used else None,
                        "is_active": key_obj.is_active
                    })
            
            return {
                "user_profile": user.to_dict(),
                "api_keys": api_key_stats,
                "rate_limit_status": {
                    "current_limits": {
                        "per_minute": user.rate_limit_per_minute,
                        "per_hour": user.rate_limit_per_hour
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None

# FastAPI integration
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """FastAPI dependency to get current authenticated user."""
    auth_manager = get_auth_manager()
    
    token = credentials.credentials
    
    # Try JWT token first
    user = await auth_manager.verify_jwt_token(token)
    if user:
        return user
    
    # Try API key authentication
    user = await auth_manager.authenticate_api_key(token)
    if user:
        return user
    
    raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def require_permission(permission: PermissionScope):
    """Decorator to require specific permission."""
    def permission_checker(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission required: {permission.value}"
            )
        return user
    return permission_checker

def require_tier(tier: UserTier):
    """Decorator to require minimum user tier."""
    def tier_checker(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        tier_hierarchy = {
            UserTier.FREE: 0,
            UserTier.BASIC: 1,
            UserTier.PROFESSIONAL: 2,
            UserTier.ENTERPRISE: 3,
            UserTier.UNLIMITED: 4
        }
        
        if tier_hierarchy.get(user.tier, 0) < tier_hierarchy.get(tier, 999):
            raise HTTPException(
                status_code=402,
                detail=f"Upgrade required. Minimum tier: {tier.value}"
            )
        return user
    return tier_checker

# Global authentication manager
_auth_manager: Optional[AuthenticationManager] = None

def get_auth_manager() -> AuthenticationManager:
    """Get global authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager