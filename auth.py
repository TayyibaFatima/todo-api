import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()


class AuthBody(BaseModel):
    email: str
    password: str


@router.post("/auth/signup", status_code=201)
def signup(body: AuthBody):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        result = supabase.auth.sign_up({"email": body.email, "password": body.password})
        return result.user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login")
def login(body: AuthBody):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        result = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


@router.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise Exception("no user")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/protected/profile")
def profile(user=Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "created_at": str(user.created_at)}


@router.get("/protected/dashboard")
def dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}"}


@router.post("/auth/logout", status_code=204)
def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return