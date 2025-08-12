from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    payment_password_hash = db.Column(db.String(255), nullable=True)
    referral_code = db.Column(db.String(10), unique=True, nullable=False)
    referred_by = db.Column(db.String(10), nullable=True)
    nickname = db.Column(db.String(100), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    vip_level = db.Column(db.String(10), default='trainee')
    vip_expiry = db.Column(db.DateTime, nullable=True)
    credit_score = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    tasks = db.relationship('UserTask', backref='user', lazy=True)
    referrals = db.relationship('Referral', backref='referrer_user', lazy=True, foreign_keys='Referral.referrer_id')

    def __init__(self, phone, password, referred_by=None):
        self.phone = phone
        self.set_password(password)
        self.referred_by = referred_by
        self.referral_code = self.generate_referral_code()

    def generate_referral_code(self):
        """Generate a unique referral code"""
        while True:
            code = secrets.token_urlsafe(6)[:6].upper()
            if not User.query.filter_by(referral_code=code).first():
                return code

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)

    def set_payment_password(self, password):
        """Set payment password hash"""
        self.payment_password_hash = generate_password_hash(password)

    def check_payment_password(self, password):
        """Check payment password"""
        if not self.payment_password_hash:
            return False
        return check_password_hash(self.payment_password_hash, password)

    def get_total_earnings(self):
        """Calculate total earnings from all sources"""
        total = 0
        for transaction in self.transactions:
            if transaction.type in ['task_reward', 'referral_commission'] and transaction.status == 'completed':
                total += transaction.amount
        return total

    def get_referral_earnings(self):
        """Calculate earnings from referrals"""
        total = 0
        for transaction in self.transactions:
            if transaction.type == 'referral_commission' and transaction.status == 'completed':
                total += transaction.amount
        return total

    def get_task_earnings(self):
        """Calculate earnings from tasks"""
        total = 0
        for transaction in self.transactions:
            if transaction.type == 'task_reward' and transaction.status == 'completed':
                total += transaction.amount
        return total

    def can_do_task_today(self):
        """Check if user can do a task today"""
        today = datetime.utcnow().date()
        today_tasks = UserTask.query.filter(
            UserTask.user_id == self.id,
            db.func.date(UserTask.completed_at) == today
        ).count()
        
        # Get max tasks per day based on VIP level
        max_tasks = self.get_max_daily_tasks()
        return today_tasks < max_tasks

    def get_max_daily_tasks(self):
        """Get maximum daily tasks based on VIP level"""
        vip_limits = {
            'trainee': 1,
            'V1': 1,
            'V2': 2,
            'V3': 4,
            'V4': 6,
            'V5': 10,
            'V6': 15,
            'V7': 20,
            'V8': 25,
            'partner': 100
        }
        return vip_limits.get(self.vip_level, 1)

    def get_daily_reward(self):
        """Get daily reward amount based on VIP level"""
        vip_rewards = {
            'trainee': 50,
            'V1': 50,
            'V2': 160,
            'V3': 520,
            'V4': 1800,
            'V5': 6000,
            'V6': 11700,
            'V7': 26000,
            'V8': 52500,
            'partner': 2600000
        }
        return vip_rewards.get(self.vip_level, 50)

    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'nickname': self.nickname,
            'balance': self.balance,
            'vip_level': self.vip_level,
            'vip_expiry': self.vip_expiry.isoformat() if self.vip_expiry else None,
            'credit_score': self.credit_score,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'total_earnings': self.get_total_earnings(),
            'referral_earnings': self.get_referral_earnings(),
            'task_earnings': self.get_task_earnings(),
            'can_do_task_today': self.can_do_task_today(),
            'max_daily_tasks': self.get_max_daily_tasks(),
            'daily_reward': self.get_daily_reward()
        }

    def __repr__(self):
        return f'<User {self.phone}>'


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # topup, withdrawal, task_reward, referral_commission
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, rejected
    description = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    receipt_url = db.Column(db.String(255), nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'amount': self.amount,
            'status': self.status,
            'description': self.description,
            'payment_method': self.payment_method,
            'receipt_url': self.receipt_url,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class UserTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_type = db.Column(db.String(50), default='survey')
    reward_amount = db.Column(db.Float, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_type': self.task_type,
            'reward_amount': self.reward_amount,
            'completed_at': self.completed_at.isoformat()
        }


class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    commission_rate = db.Column(db.Float, nullable=False)  # 0.10, 0.03, 0.01
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'referrer_id': self.referrer_id,
            'referred_id': self.referred_id,
            'level': self.level,
            'commission_rate': self.commission_rate,
            'created_at': self.created_at.isoformat()
        }


class VIPPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    daily_tasks = db.Column(db.Integer, nullable=False)
    daily_reward = db.Column(db.Float, nullable=False)
    monthly_income = db.Column(db.Float, nullable=False)
    yearly_income = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'name': self.name,
            'price': self.price,
            'daily_tasks': self.daily_tasks,
            'daily_reward': self.daily_reward,
            'monthly_income': self.monthly_income,
            'yearly_income': self.yearly_income,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }

