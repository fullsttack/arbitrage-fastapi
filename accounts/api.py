import logging
from typing import List

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import transaction
from ninja import Router, Schema
from ninja.security import django_auth

from accounts.models import UserProfile
from core.models import APICredential, Exchange

logger = logging.getLogger(__name__)

router = Router()


class LoginSchema(Schema):
    username: str
    password: str


class RegisterSchema(Schema):
    username: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


class UserSchema(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    date_joined: str


class UserProfileSchema(Schema):
    phone: str = ""
    telegram_id: str = ""
    enable_telegram_alerts: bool = True
    enable_email_alerts: bool = True
    default_exchange: str = ""
    timezone: str = "UTC"


class APICredentialSchema(Schema):
    exchange: str
    api_key: str
    api_secret: str = ""
    permissions: dict = {}
    is_active: bool = True


class APICredentialResponseSchema(Schema):
    id: int
    exchange: str
    api_key_preview: str
    is_active: bool
    last_used: str = None
    created_at: str


@router.post("/register", response=UserSchema)
def register(request, data: RegisterSchema):
    """
    Register a new user.
    """
    if User.objects.filter(username=data.username).exists():
        return {"error": "Username already exists"}
    
    if User.objects.filter(email=data.email).exists():
        return {"error": "Email already exists"}
    
    with transaction.atomic():
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
    
    return user


@router.post("/login")
def login_user(request, data: LoginSchema):
    """
    Login user.
    """
    user = authenticate(username=data.username, password=data.password)
    if user:
        login(request, user)
        return {"success": True, "username": user.username}
    return {"success": False, "error": "Invalid credentials"}


@router.post("/logout", auth=django_auth)
def logout_user(request):
    """
    Logout user.
    """
    logout(request)
    return {"success": True}


@router.get("/me", auth=django_auth, response=UserSchema)
def get_current_user(request):
    """
    Get current user information.
    """
    return request.user


@router.get("/profile", auth=django_auth, response=UserProfileSchema)
def get_profile(request):
    """
    Get user profile.
    """
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return profile


@router.patch("/profile", auth=django_auth, response=UserProfileSchema)
def update_profile(request, data: UserProfileSchema):
    """
    Update user profile.
    """
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    for field, value in data.dict(exclude_unset=True).items():
        if field == "default_exchange" and value:
            # Validate exchange exists
            if not Exchange.objects.filter(code=value).exists():
                return {"error": f"Exchange {value} not found"}
        setattr(profile, field, value)
    
    profile.save()
    return profile


@router.get("/credentials", auth=django_auth, response=List[APICredentialResponseSchema])
def list_credentials(request):
    """
    List user's API credentials.
    """
    credentials = APICredential.objects.filter(
        user=request.user
    ).select_related("exchange")
    
    return [
        {
            "id": cred.id,
            "exchange": cred.exchange.code,
            "api_key_preview": f"{cred.api_key[:8]}...{cred.api_key[-4:]}",
            "is_active": cred.is_active,
            "last_used": cred.last_used.isoformat() if cred.last_used else None,
            "created_at": cred.created_at.isoformat(),
        }
        for cred in credentials
    ]


@router.post("/credentials", auth=django_auth, response=APICredentialResponseSchema)
def add_credential(request, data: APICredentialSchema):
    """
    Add API credential for an exchange.
    """
    exchange = Exchange.objects.filter(code=data.exchange).first()
    if not exchange:
        return {"error": f"Exchange {data.exchange} not found"}
    
    # Check if credential already exists
    existing = APICredential.objects.filter(
        user=request.user,
        exchange=exchange
    ).first()
    
    if existing:
        # Update existing credential
        existing.api_key = data.api_key
        existing.api_secret = data.api_secret
        existing.permissions = data.permissions
        existing.is_active = data.is_active
        existing.save()
        credential = existing
    else:
        # Create new credential
        credential = APICredential.objects.create(
            user=request.user,
            exchange=exchange,
            api_key=data.api_key,
            api_secret=data.api_secret,
            permissions=data.permissions,
            is_active=data.is_active,
        )
    
    # Test credential
    from exchanges.tasks import test_api_credential
    test_api_credential.delay(credential.id)
    
    return {
        "id": credential.id,
        "exchange": credential.exchange.code,
        "api_key_preview": f"{credential.api_key[:8]}...{credential.api_key[-4:]}",
        "is_active": credential.is_active,
        "created_at": credential.created_at.isoformat(),
    }


@router.delete("/credentials/{credential_id}", auth=django_auth)
def delete_credential(request, credential_id: int):
    """
    Delete an API credential.
    """
    credential = APICredential.objects.filter(
        id=credential_id,
        user=request.user
    ).first()
    
    if not credential:
        return {"error": "Credential not found"}
    
    credential.delete()
    return {"success": True}


@router.post("/credentials/{credential_id}/test", auth=django_auth)
def test_credential(request, credential_id: int):
    """
    Test an API credential.
    """
    credential = APICredential.objects.filter(
        id=credential_id,
        user=request.user
    ).first()
    
    if not credential:
        return {"error": "Credential not found"}
    
    from exchanges.tasks import test_api_credential
    task = test_api_credential.delay(credential.id)
    
    return {"success": True, "task_id": task.id}