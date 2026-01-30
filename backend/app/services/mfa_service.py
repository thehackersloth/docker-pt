"""
MFA/2FA service
"""

import secrets
import pyotp
import qrcode
import io
import base64
from typing import Optional
from app.core.database import SessionLocal
from app.models.user import User


class MFAService:
    """Multi-factor authentication service"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(secret: str, username: str, issuer: str = "Pentest Platform") -> str:
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.read()).decode()
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    @staticmethod
    def enable_mfa(user_id: str, secret: str) -> bool:
        """Enable MFA for user"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Store secret (should be encrypted in production)
            # For now, store in user model if we add mfa_secret field
            # user.mfa_secret = secret
            # user.mfa_enabled = True
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
