from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, VIPPackage, Transaction
from datetime import datetime, timedelta

vip_bp = Blueprint('vip', __name__)

def initialize_vip_packages():
    """Initialize VIP packages if they don't exist"""
    if VIPPackage.query.count() == 0:
        packages = [
            {
                'level': 'V1',
                'name': 'باقة V1',
                'price': 1500,
                'daily_tasks': 1,
                'daily_reward': 50,
                'monthly_income': 1500,
                'yearly_income': 18250
            },
            {
                'level': 'V2',
                'name': 'باقة V2',
                'price': 4800,
                'daily_tasks': 2,
                'daily_reward': 160,
                'monthly_income': 4800,
                'yearly_income': 58400
            },
            {
                'level': 'V3',
                'name': 'باقة V3',
                'price': 15000,
                'daily_tasks': 4,
                'daily_reward': 520,
                'monthly_income': 15600,
                'yearly_income': 189800
            },
            {
                'level': 'V4',
                'name': 'باقة V4',
                'price': 50400,
                'daily_tasks': 6,
                'daily_reward': 1800,
                'monthly_income': 54000,
                'yearly_income': 657000
            },
            {
                'level': 'V5',
                'name': 'باقة V5',
                'price': 162000,
                'daily_tasks': 10,
                'daily_reward': 6000,
                'monthly_income': 180000,
                'yearly_income': 2190000
            },
            {
                'level': 'V6',
                'name': 'باقة V6',
                'price': 304200,
                'daily_tasks': 15,
                'daily_reward': 11700,
                'monthly_income': 351000,
                'yearly_income': 4270500
            },
            {
                'level': 'V7',
                'name': 'باقة V7',
                'price': 650000,
                'daily_tasks': 20,
                'daily_reward': 26000,
                'monthly_income': 780000,
                'yearly_income': 9480000
            },
            {
                'level': 'V8',
                'name': 'باقة V8',
                'price': 1260000,
                'daily_tasks': 25,
                'daily_reward': 52500,
                'monthly_income': 1575000,
                'yearly_income': 19162500
            },
            {
                'level': 'partner',
                'name': 'شريك جديد',
                'price': 5200000,
                'daily_tasks': 100,
                'daily_reward': 2600000,
                'monthly_income': 78000000,
                'yearly_income': 948000000
            }
        ]
        
        for package_data in packages:
            package = VIPPackage(**package_data)
            db.session.add(package)
        
        db.session.commit()

@vip_bp.route('/packages', methods=['GET'])
def get_vip_packages():
    """Get all available VIP packages"""
    try:
        initialize_vip_packages()
        
        packages = VIPPackage.query.filter_by(is_active=True).order_by(VIPPackage.price).all()
        
        return jsonify({
            'packages': [p.to_dict() for p in packages]
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب باقات VIP'}), 500

@vip_bp.route('/packages/<string:level>', methods=['GET'])
def get_vip_package(level):
    """Get specific VIP package details"""
    try:
        package = VIPPackage.query.filter_by(level=level, is_active=True).first()
        
        if not package:
            return jsonify({'error': 'الباقة غير موجودة'}), 404
        
        return jsonify({
            'package': package.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب تفاصيل الباقة'}), 500

@vip_bp.route('/subscribe', methods=['POST'])
def subscribe_to_vip():
    """Subscribe to a VIP package"""
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        if not data or not data.get('level'):
            return jsonify({'error': 'مستوى الباقة مطلوب'}), 400
        
        level = data['level']
        payment_password = data.get('payment_password')
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # Check payment password if user has one set
        if user.payment_password_hash and not user.check_payment_password(payment_password):
            return jsonify({'error': 'كلمة مرور الدفع غير صحيحة'}), 400
        
        # Get package details
        package = VIPPackage.query.filter_by(level=level, is_active=True).first()
        if not package:
            return jsonify({'error': 'الباقة غير موجودة'}), 404
        
        # Check if user already has this VIP level or higher
        current_vip_levels = ['trainee', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'partner']
        current_index = current_vip_levels.index(user.vip_level) if user.vip_level in current_vip_levels else 0
        new_index = current_vip_levels.index(level) if level in current_vip_levels else 0
        
        if new_index <= current_index and user.vip_level != 'trainee':
            return jsonify({'error': 'لديك باقة أعلى أو مساوية لهذه الباقة'}), 400
        
        # Check if user has sufficient balance
        if user.balance < package.price:
            return jsonify({'error': 'الرصيد غير كافي لشراء هذه الباقة'}), 400
        
        # Deduct amount from balance
        user.balance -= package.price
        
        # Update user VIP level
        user.vip_level = level
        user.vip_expiry = datetime.utcnow() + timedelta(days=365)  # 1 year subscription
        
        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            type='vip_subscription',
            amount=-package.price,  # Negative because it's a deduction
            status='completed',
            description=f'اشتراك في باقة {package.name}'
        )
        db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم الاشتراك في {package.name} بنجاح!',
            'user': user.to_dict(),
            'transaction': transaction.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في الاشتراك'}), 500

@vip_bp.route('/current', methods=['GET'])
def get_current_vip():
    """Get current user's VIP status"""
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        current_package = None
        if user.vip_level != 'trainee':
            current_package = VIPPackage.query.filter_by(level=user.vip_level).first()
        
        # Check if VIP is expired
        is_expired = False
        if user.vip_expiry and user.vip_expiry < datetime.utcnow():
            is_expired = True
            # Reset to trainee if expired
            user.vip_level = 'trainee'
            user.vip_expiry = None
            db.session.commit()
        
        return jsonify({
            'current_level': user.vip_level,
            'vip_expiry': user.vip_expiry.isoformat() if user.vip_expiry else None,
            'is_expired': is_expired,
            'current_package': current_package.to_dict() if current_package else None,
            'max_daily_tasks': user.get_max_daily_tasks(),
            'daily_reward': user.get_daily_reward()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب حالة VIP'}), 500

@vip_bp.route('/benefits', methods=['GET'])
def get_vip_benefits():
    """Get VIP benefits comparison"""
    try:
        benefits = {
            'trainee': {
                'daily_tasks': 1,
                'daily_reward': 50,
                'monthly_income': 1500,
                'features': ['مهمة واحدة يومياً', 'مكافأة 50 جنيه', 'دعم أساسي']
            },
            'V1': {
                'daily_tasks': 1,
                'daily_reward': 50,
                'monthly_income': 1500,
                'features': ['مهمة واحدة يومياً', 'مكافأة 50 جنيه', 'دعم متقدم', 'إحصائيات مفصلة']
            },
            'V2': {
                'daily_tasks': 2,
                'daily_reward': 160,
                'monthly_income': 4800,
                'features': ['مهمتان يومياً', 'مكافأة 160 جنيه', 'دعم أولوية', 'تقارير شهرية']
            },
            'V3': {
                'daily_tasks': 4,
                'daily_reward': 520,
                'monthly_income': 15600,
                'features': ['4 مهام يومياً', 'مكافأة 520 جنيه', 'دعم VIP', 'مدير حساب مخصص']
            }
        }
        
        return jsonify({'benefits': benefits}), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب مزايا VIP'}), 500

