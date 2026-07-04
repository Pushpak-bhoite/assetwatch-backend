"""
Email Service using SendGrid

This module handles all email sending functionality for the AssetWatch application.
Supports:
- Password reset emails
- Email verification emails
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from app.core.config import settings


class EmailService:
    """
    Email service using SendGrid API.
    
    Usage:
        email_service = EmailService()
        await email_service.send_password_reset_email(
            to_email="user@example.com",
            token="reset-token-here"
        )
    """
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.from_name = settings.EMAILS_FROM_NAME or "AssetWatch"
        self.frontend_host = settings.FRONTEND_HOST
        
    @property
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.api_key and self.from_email)
    
    def _get_client(self) -> SendGridAPIClient:
        """Get SendGrid client instance."""
        if not self.api_key:
            raise ValueError("SendGrid API key is not configured")
        return SendGridAPIClient(self.api_key)
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str
    ) -> bool:
        """
        Send an email using SendGrid.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML content of the email
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_configured:
            print(f"[EMAIL SERVICE] Not configured. Would send to {to_email}: {subject}")
            return False
            
        try:
            
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=HtmlContent(html_content)
            )
            
            client = self._get_client()
            response = client.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"[EMAIL SERVICE] Successfully sent email to {to_email}")
                return True
            else:
                print(f"[EMAIL SERVICE] Failed to send email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[EMAIL SERVICE] Error sending email: {e}")
            return False
    
    async def send_password_reset_email(
        self, 
        to_email: str, 
        token: str
    ) -> bool:
        """
        Send password reset email with reset link.
        
        Args:
            to_email: User's email address
            token: Password reset token from FastAPI Users
            
        Returns:
            True if sent successfully
        """
        reset_link = f"{self.frontend_host}/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Password Reset Request</h1>
            </div>
            
            <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hello,</p>
                
                <p style="font-size: 16px;">We received a request to reset your password for your AssetWatch account. Click the button below to set a new password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 14px 30px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              font-weight: bold;
                              font-size: 16px;
                              display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                    <a href="{reset_link}" style="color: #667eea;">{reset_link}</a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <p style="font-size: 14px; color: #666;">
                    <strong>Didn't request this?</strong><br>
                    If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
                </p>
                
                <p style="font-size: 14px; color: #666;">
                    This link will expire in {settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS} hours for security reasons.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                <p>&copy; {self.from_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Reset Your Password - AssetWatch",
            html_content=html_content
        )
    
    async def send_verification_email(
        self, 
        to_email: str, 
        token: str
    ) -> bool:
        """
        Send email verification link.
        
        Args:
            to_email: User's email address
            token: Verification token from FastAPI Users
            
        Returns:
            True if sent successfully
        """
        verify_link = f"{self.frontend_host}/verify-email?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Verify Your Email</h1>
            </div>
            
            <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Welcome to AssetWatch! 🎉</p>
                
                <p style="font-size: 16px;">Thank you for signing up. Please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verify_link}" 
                       style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                              color: white; 
                              padding: 14px 30px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              font-weight: bold;
                              font-size: 16px;
                              display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                    <a href="{verify_link}" style="color: #11998e;">{verify_link}</a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <p style="font-size: 14px; color: #666;">
                    <strong>Why verify?</strong><br>
                    Verifying your email helps us ensure the security of your account and enables you to receive important notifications about your assets.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                <p>&copy; {self.from_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Verify Your Email - AssetWatch",
            html_content=html_content
        )

    async def send_invitation_email(
        self, 
        to_email: str, 
        inviter_name: str,
        organization_type: str,
        personal_message: str = None
    ) -> bool:
        """
        Send invitation email to a new user.
        
        Args:
            to_email: Invitee's email address
            inviter_name: Name of the person sending the invitation
            organization_type: Role/type the invitee will have
            personal_message: Optional personal message from the inviter
            
        Returns:
            True if sent successfully
        """
        register_link = f"{self.frontend_host}/sign-up"
        
        # Map organization types to display names
        role_labels = {
            "customer": "Customer",
            "reseller": "Reseller",
            "reseller_customer": "Reseller Customer",
            "assetwatch": "AssetWatch Admin"
        }
        role_display = role_labels.get(organization_type, organization_type)
        
        # Build personal message section if provided
        personal_message_html = ""
        if personal_message:
            personal_message_html = f"""
                <div style="background: #f8f9fa; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0; border-radius: 0 5px 5px 0;">
                    <p style="font-size: 14px; color: #555; margin: 0; font-style: italic;">
                        "{personal_message}"
                    </p>
                    <p style="font-size: 12px; color: #888; margin: 10px 0 0 0;">
                        — {inviter_name}
                    </p>
                </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">You're Invited! 🎉</h1>
            </div>
            
            <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hello,</p>
                
                <p style="font-size: 16px;">
                    <strong>{inviter_name}</strong> has invited you to join AssetWatch as a <strong>{role_display}</strong>.
                </p>
                
                {personal_message_html}
                
                <p style="font-size: 16px;">
                    AssetWatch is a powerful network infrastructure monitoring platform that helps you keep track of your assets and ensure everything is running smoothly.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{register_link}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 14px 30px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              font-weight: bold;
                              font-size: 16px;
                              display: inline-block;">
                        Accept Invitation & Sign Up
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="font-size: 12px; word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                    <a href="{register_link}" style="color: #667eea;">{register_link}</a>
                </p>
                
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                
                <p style="font-size: 14px; color: #666;">
                    <strong>What happens next?</strong><br>
                    Click the link above to create your account. Use this email address (<strong>{to_email}</strong>) when signing up to ensure your account is properly linked.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #888; font-size: 12px;">
                <p>&copy; {self.from_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"You're invited to join AssetWatch by {inviter_name}",
            html_content=html_content
        )


# Global email service instance
email_service = EmailService()
