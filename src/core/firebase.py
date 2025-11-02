import os
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import auth, credentials
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.user import User

settings = get_settings()

_firebase_app = None

def initialize_firebase():
    global _firebase_app
    if _firebase_app is None:
        if os.path.exists(settings.firebase_service_account_path):
            cred = credentials.Certificate(settings.firebase_service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': settings.firebase_project_id
            })
        else:
            _firebase_app = firebase_admin.initialize_app()
    return _firebase_app

def verify_firebase_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        initialize_firebase()
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        return None

def get_or_create_user(db: Session, firebase_uid: str, email: str, full_name: str, date_of_birth: str = None) -> User:
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if not user:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=full_name,
            date_of_birth=date_of_birth
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user