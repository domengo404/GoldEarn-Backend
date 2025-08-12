from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Referral
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

def validate_phone(phone):
    """Validate Egyptian phone number"""
    pattern = r'^(010|011|012|015)\d{8}$'
    return re.match(pattern, phone) is not None

def create_referral_chain(new_user, referrer):
    """Create referral chain for up to 3 levels"""
    if not referrer:
        return
    
    # Level 1: Direct referral
    referral_1 = Referral(
        referrer_id=referrer.id,
        referred_id=new_user.id,
        level=1,
        commission_rate=0.10
    )
    db.session.add(referral_1)
    
    # Level 2: Referrer's referrer
    level_2_referrer = None
    if referrer.referred_by:
        level_2_referrer = User.query.filter_by(referral_code=referrer.referred_by).first()
        if level_2_referrer:
            referral_2 = Referral(
                referrer_id=level_2_referrer.id,
                referred_id=new_user.id,
                level=2,
                commission_rate=0.03
            )
            db.session.add(referral_2)
    
    # Level 3: Level 2 referrer's referrer
    if level_2_referrer and level_2_referrer.referred_by:
        level_3_referrer = User.query.filter_by(referral_code=level_2_referrer.referred_by).first()
        if level_3_referrer:
            referral_3 = Referral(
                referrer_id=level_3_referrer.id,
                referred_id=new_user.id,
                level=3,
                commission_rate=0.01
            )
            db.session.add(referral_3)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('phone') or not data.get('password'):
            return jsonify({'error': 'رقم الهاتف وكلمة المرور مطلوبان'}), 400
        
        phone = data['phone'].strip()
        password = data['password']
        referral_code = data.get('referral_code', '').strip()
        
        # Validate phone number
        if not validate_phone(phone):
            return jsonify({'error': 'رقم الهاتف غير صحيح'}), 400
        
        # Check if user already exists
        if User.query.filter_by(phone=phone).first():
            return jsonify({'error': 'رقم الهاتف مسجل مسبقاً'}), 400
        
        # Validate referral code if provided
        referrer = None
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if not referrer:
                return jsonify({'error': 'رمز الإحالة غير صحيح'}), 400
        
        # Create new user
        new_user = User(
            phone=phone,
            password=password,
            referred_by=referral_code if referrer else None
        )
        
        db.session.add(new_user)
        db.session.flush()  # Get the user ID
        
        # Create referral chain
        create_referral_chain(new_user, referrer)
        
        db.session.commit()
        
        # Set session
        session['user_id'] = new_user.id
        session['phone'] = new_user.phone
        
        return jsonify({
            'message': 'تم التسجيل بنجاح',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في التسجيل'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not data.get('phone') or not data.get('password'):
            return jsonify({'error': 'رقم الهاتف وكلمة المرور مطلوبان'}), 400
        
        phone = data['phone'].strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(phone=phone).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'رقم الهاتف أو كلمة المرور غير صحيح'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'الحساب معطل، تواصل مع الدعم'}), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Set session
        session['user_id'] = user.id
        session['phone'] = user.phone
        
        return jsonify({
            'message': 'تم تسجيل الدخول بنجاح',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في تسجيل الدخول'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'تم تسجيل الخروج بنجاح'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'كلمة المرور الحالية والجديدة مطلوبتان'}), 400
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'كلمة المرور الحالية غير صحيحة'}), 400
        
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'تم تغيير كلمة المرور بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في تغيير كلمة المرور'}), 500

@auth_bp.route('/set-payment-password', methods=['POST'])
def set_payment_password():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        if not data or not data.get('payment_password'):
            return jsonify({'error': 'كلمة مرور الدفع مطلوبة'}), 400
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        user.set_payment_password(data['payment_password'])
        db.session.commit()
        
        return jsonify({'message': 'تم تعيين كلمة مرور الدفع بنجاح'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في تعيين كلمة مرور الدفع'}), 500

@auth_bp.route('/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # Update nickname if provided
        if 'nickname' in data:
            user.nickname = data['nickname'].strip() if data['nickname'] else None
        
        db.session.commit()
        
        return jsonify({
            'message': 'تم تحديث الملف الشخصي بنجاح',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في تحديث الملف الشخصي'}), 500

