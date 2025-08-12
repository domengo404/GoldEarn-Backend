from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, UserTask, Transaction
from datetime import datetime, timedelta

tasks_bp = Blueprint('tasks', __name__)

def calculate_referral_commissions(user, amount):
    """Calculate and create referral commissions for task rewards"""
    from src.models.user import Referral
    
    referrals = Referral.query.filter_by(referred_id=user.id).all()
    
    for referral in referrals:
        commission_amount = amount * referral.commission_rate
        
        # Create commission transaction
        commission_transaction = Transaction(
            user_id=referral.referrer_id,
            type='referral_commission',
            amount=commission_amount,
            status='completed',
            description=f'عمولة إحالة من المستوى {referral.level} - مهمة {user.phone}'
        )
        db.session.add(commission_transaction)
        
        # Add to referrer's balance
        referrer = User.query.get(referral.referrer_id)
        if referrer:
            referrer.balance += commission_amount

@tasks_bp.route('/can-do-task', methods=['GET'])
def can_do_task():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # Check if user can do task today
        can_do = user.can_do_task_today()
        
        # Get today's completed tasks count
        today = datetime.utcnow().date()
        today_tasks = UserTask.query.filter(
            UserTask.user_id == user.id,
            db.func.date(UserTask.completed_at) == today
        ).count()
        
        return jsonify({
            'can_do_task': can_do,
            'tasks_completed_today': today_tasks,
            'max_daily_tasks': user.get_max_daily_tasks(),
            'daily_reward': user.get_daily_reward(),
            'vip_level': user.vip_level
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في التحقق من المهام'}), 500

@tasks_bp.route('/complete-task', methods=['POST'])
def complete_task():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        task_type = data.get('task_type', 'survey')
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        # Check if user can do task today
        if not user.can_do_task_today():
            return jsonify({'error': 'لقد أكملت المهام المتاحة لليوم'}), 400
        
        # Get reward amount based on VIP level
        reward_amount = user.get_daily_reward()
        
        # Create task record
        user_task = UserTask(
            user_id=user.id,
            task_type=task_type,
            reward_amount=reward_amount
        )
        db.session.add(user_task)
        
        # Create reward transaction
        reward_transaction = Transaction(
            user_id=user.id,
            type='task_reward',
            amount=reward_amount,
            status='completed',
            description=f'مكافأة إتمام مهمة يومية - {task_type}'
        )
        db.session.add(reward_transaction)
        
        # Add reward to user balance
        user.balance += reward_amount
        
        # Calculate referral commissions
        calculate_referral_commissions(user, reward_amount)
        
        db.session.commit()
        
        return jsonify({
            'message': f'تم إتمام المهمة بنجاح! حصلت على {reward_amount} جنيه',
            'task': user_task.to_dict(),
            'transaction': reward_transaction.to_dict(),
            'new_balance': user.balance
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'حدث خطأ في إتمام المهمة'}), 500

@tasks_bp.route('/history', methods=['GET'])
def get_task_history():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        tasks = UserTask.query.filter_by(user_id=session['user_id']).order_by(
            UserTask.completed_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'tasks': [t.to_dict() for t in tasks.items],
            'total': tasks.total,
            'pages': tasks.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب سجل المهام'}), 500

@tasks_bp.route('/stats', methods=['GET'])
def get_task_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        user_id = session['user_id']
        
        # Total tasks completed
        total_tasks = UserTask.query.filter_by(user_id=user_id).count()
        
        # Tasks completed this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_tasks = UserTask.query.filter(
            UserTask.user_id == user_id,
            UserTask.completed_at >= week_ago
        ).count()
        
        # Tasks completed this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        monthly_tasks = UserTask.query.filter(
            UserTask.user_id == user_id,
            UserTask.completed_at >= month_ago
        ).count()
        
        # Total earnings from tasks
        total_task_earnings = db.session.query(db.func.sum(UserTask.reward_amount)).filter(
            UserTask.user_id == user_id
        ).scalar() or 0
        
        return jsonify({
            'total_tasks': total_tasks,
            'weekly_tasks': weekly_tasks,
            'monthly_tasks': monthly_tasks,
            'total_task_earnings': total_task_earnings
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في جلب إحصائيات المهام'}), 500

@tasks_bp.route('/survey-questions', methods=['GET'])
def get_survey_questions():
    """Get random survey questions for the user"""
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    # Mock survey questions - in real app these would come from database
    questions = [
        {
            'id': 1,
            'question': 'ما هو رأيك في جودة الخدمات المصرفية الإلكترونية؟',
            'type': 'multiple_choice',
            'options': ['ممتازة', 'جيدة', 'متوسطة', 'ضعيفة']
        },
        {
            'id': 2,
            'question': 'كم مرة تستخدم التطبيقات المصرفية في الأسبوع؟',
            'type': 'multiple_choice',
            'options': ['يومياً', '3-5 مرات', '1-2 مرة', 'نادراً']
        },
        {
            'id': 3,
            'question': 'ما هي أهم الميزات التي تبحث عنها في التطبيق المصرفي؟',
            'type': 'multiple_choice',
            'options': ['الأمان', 'سهولة الاستخدام', 'السرعة', 'الخدمات المتنوعة']
        },
        {
            'id': 4,
            'question': 'هل تفضل استخدام التطبيقات المحمولة أم المواقع الإلكترونية؟',
            'type': 'multiple_choice',
            'options': ['التطبيقات المحمولة', 'المواقع الإلكترونية', 'كلاهما', 'لا أفضل أي منهما']
        },
        {
            'id': 5,
            'question': 'ما مدى رضاك عن خدمة العملاء في البنوك؟',
            'type': 'multiple_choice',
            'options': ['راضي جداً', 'راضي', 'محايد', 'غير راضي']
        }
    ]
    
    # Return a random question
    import random
    selected_question = random.choice(questions)
    
    return jsonify({
        'question': selected_question
    }), 200

@tasks_bp.route('/submit-survey', methods=['POST'])
def submit_survey():
    """Submit survey answers and complete task"""
    if 'user_id' not in session:
        return jsonify({'error': 'غير مسجل الدخول'}), 401
    
    try:
        data = request.get_json()
        
        if not data or 'answers' not in data:
            return jsonify({'error': 'الإجابات مطلوبة'}), 400
        
        # For now, we just accept any answers and complete the task
        # In real app, you would validate and store the answers
        
        return complete_task()
        
    except Exception as e:
        return jsonify({'error': 'حدث خطأ في إرسال الاستبيان'}), 500

