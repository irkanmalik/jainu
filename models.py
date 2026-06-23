from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150))
    password_hash = db.Column(db.String(300), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    credits = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship("Video", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(300))
    status = db.Column(db.String(50), default="pending")  # pending, processing, done, failed
    error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Setting(db.Model):
    """Key/value site settings — admin can edit anything from /admin/settings"""
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=None):
        s = Setting.query.get(key)
        return s.value if s else default

    @staticmethod
    def set(key, value):
        s = Setting.query.get(key)
        if s:
            s.value = str(value)
        else:
            s = Setting(key=key, value=str(value))
            db.session.add(s)
        db.session.commit()

    @staticmethod
    def get_bool(key, default=False):
        v = Setting.get(key)
        if v is None:
            return default
        return str(v).lower() in ("1", "true", "yes", "on")

    @staticmethod
    def get_int(key, default=0):
        try:
            return int(Setting.get(key, default))
        except (TypeError, ValueError):
            return default


DEFAULT_SETTINGS = {
    # Branding
    "site_name": "Pictory AI",
    "site_tagline": "Turn any text into stunning AI videos",
    "primary_color": "#6366f1",
    "logo_emoji": "🎬",
    # AI config
    "gemini_model": "gemini-2.0-flash-exp",
    "image_model": "gemini-2.0-flash-exp",
    "system_prompt": (
        "You are a video script writer. Given a topic, output a JSON array of 4-6 scenes. "
        "Each scene: {\"narration\": \"short sentence to be spoken (under 20 words)\", "
        "\"image_prompt\": \"detailed cinematic image description for that scene\"}. "
        "Return ONLY valid JSON, no markdown fences."
    ),
    "voice_lang": "en",
    "scene_duration": "4",
    "video_resolution": "720",
    # Feature toggles
    "signup_enabled": "true",
    "video_gen_enabled": "true",
    "free_credits": "5",
    "max_prompt_length": "500",
    "require_login": "true",
}


def seed_settings():
    for k, v in DEFAULT_SETTINGS.items():
        if Setting.query.get(k) is None:
            db.session.add(Setting(key=k, value=v))
    db.session.commit()
