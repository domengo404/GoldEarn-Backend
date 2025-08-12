from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Transaction, Referral
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

transactions_bp = Blueprint('transactions', __name__)

UPLOAD_FOLDER = 'uploads/receipts'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_referral_commissions(user, amount):
    """Calculate and create referral commissions"""
    referrals = Referral.query.filter_by(referred_id=user.id).all()
    
    for referral in referrals:
        commission_amount = amount * referral.commission_rate
        
        # Create commission transaction
        commission_transaction = Transaction(
            user_id=referral.referrer_id,
            type='referral_commission',
            amount=commission_amount,
            status='completed',
            description=f'عمولة إحالة من المستوى {referral.level} - {user.phone}'
        )
        db.session.add(commission_transaction)
        
        # Add to referrer's balance
        referrer = User.query.get(referral.referrer_id)
        if referrer:
            referrer.balance += commission_amount

@transactions_bp.route('/topup', methods=['POST'])
def create_topup():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        if not data or not data.get('amount') or not data.get('payment_method'):
            return jsonify({'error': 'المبلغ وطريقة الدفع مطلوبان'}), 400
        
        amount = float(data['amount'])
        payment_method = data['payment_method']
        
        if amount <= 0:
            return jsonify({'error': 'المبلغ يجب أن يكون أكبر من صفر'}), 400
        
        if payment_method not in ['vodafone_cash', 'bank_transfer']:
            return jsonify({'error': 'طريقة دفع غير صحيحة'}), 400
        
        # Create topup transaction
        transaction = Transaction(
            user_id=session['user_id'],
            type='topup',
            amount=amount,
            status='pending',
            payment_method=payment_method,
            description=f'طلب شحن رصيد بمبلغ {amount} جنيه'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إرسال طلب الشحن بنجاح',
            'transaction': transaction.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في إرسال طلب الشحن'}), 500

@transactions_bp.route('/topup/<int:transaction_id>/upload-receipt', methods=['POST'])
def upload_receipt(transaction_id):
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        transaction = Transaction.query.filter_by(
            id=transaction_id,
            user_id=session['user_id'],
            type='topup'
        ).first()
        
        if not transaction:
            return jsonify({'error': 'المعاملة غير موجودة'}), 404
        
        if 'receipt' not in request.files:
            return jsonify({'error': 'لم يتم رفع ملف'}), 400
        
        file = request.files['receipt']
        if file.filename == '':
            return jsonify({'error': 'لم يتم اختيار ملف'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{transaction_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            
            # Create upload directory if it doesn't exist
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Update transaction with receipt URL
            transaction.receipt_url = file_path
            db.session.commit()
            
            return jsonify({
                'message': 'تم رفع الإيصال بنجاح',
                'transaction': transaction.to_dict()
            }), 200
        else:
            return jsonify({'error': 'نوع الملف غير مدعوم'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في رفع الإيصال'}), 500

@transactions_bp.route('/withdraw', methods=['POST'])
def create_withdrawal():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        if not data or not data.get('amount'):
            return jsonify({'error': 'المبلغ مطلوب'}), 400
        
        amount = float(data['amount'])
        
        if amount <= 0:
            return jsonify({'error': 'المبلغ يجب أن يكون أكبر من صفر'}), 400
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        if user.balance < amount:
            return jsonify({'error': 'الرصيد غير كافي'}), 400
        
        # Create withdrawal transaction
        transaction = Transaction(
            user_id=user.id,
            type='withdrawal',
            amount=amount,
            status='pending',
            description=f'طلب سحب أرباح بمبلغ {amount} جنيه'
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'تم إرسال طلب السحب بنجاح',
            'transaction': transaction.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في إرسال طلب السحب'}), 500

@transactions_bp.route('/history', methods=['GET'])
def get_transaction_history():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        transaction_type = request.args.get('type', 'all')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        query = Transaction.query.filter_by(user_id=session['user_id'])
        
        if transaction_type != 'all':
            query = query.filter_by(type=transaction_type)
        
        transactions = query.order_by(Transaction.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'transactions': [t.to_dict() for t in transactions.items],
            'total': transactions.total,
            'pages': transactions.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب السجلات'}), 500

@transactions_bp.route('/summary', methods=['GET'])
def get_transaction_summary():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        user_id = session['user_id']
        
        # Get summary counts
        total_topups = Transaction.query.filter_by(
            user_id=user_id, type='topup', status='completed'
        ).count()
        
        total_withdrawals = Transaction.query.filter_by(
            user_id=user_id, type='withdrawal', status='completed'
        ).count()
        
        pending_transactions = Transaction.query.filter_by(
            user_id=user_id, status='pending'
        ).count()
        
        rejected_transactions = Transaction.query.filter_by(
            user_id=user_id, status='rejected'
        ).count()
        
        return jsonify({
            'total_topups': total_topups,
            'total_withdrawals': total_withdrawals,
            'pending_transactions': pending_transactions,
            'rejected_transactions': rejected_transactions
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب الملخص'}), 500

@transactions_bp.route('/earnings', methods=['GET'])
def get_earnings():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # Get referral statistics
        level_1_referrals = Referral.query.filter_by(
            referrer_id=user.id, level=1
        ).count()
        
        # Get total team referrals (all levels)
        total_team_referrals = Referral.query.filter_by(
            referrer_id=user.id
        ).count()
        
        # Get level 1 topup amount
        level_1_topup_amount = 0
        level_1_referred_users = [r.referred_id for r in Referral.query.filter_by(
            referrer_id=user.id, level=1
        ).all()]
        
        if level_1_referred_users:
            level_1_topup_amount = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.user_id.in_(level_1_referred_users),
                Transaction.type == 'topup',
                Transaction.status == 'completed'
            ).scalar() or 0
        
        # Get total team topup amount
        all_referred_users = [r.referred_id for r in Referral.query.filter_by(
            referrer_id=user.id
        ).all()]
        
        total_team_topup_amount = 0
        if all_referred_users:
            total_team_topup_amount = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.user_id.in_(all_referred_users),
                Transaction.type == 'topup',
                Transaction.status == 'completed'
            ).scalar() or 0
        
        return jsonify({
            'total_earnings': user.get_total_earnings(),
            'referral_earnings': user.get_referral_earnings(),
            'task_earnings': user.get_task_earnings(),
            'level_1_referrals': level_1_referrals,
            'total_team_referrals': total_team_referrals,
            'level_1_topup_amount': level_1_topup_amount,
            'total_team_topup_amount': total_team_topup_amount
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب الأرباح'}), 500

