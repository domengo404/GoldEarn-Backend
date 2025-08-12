from flask import Blueprint, request, jsonify, session, render_template_string, redirect
from src.models.user import db, User, Transaction, UserTask, Referral, VIPPackage
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import os

admin_bp = Blueprint('admin', __name__)

# Admin credentials (in real app, this would be in database with proper hashing)
ADMIN_CREDENTIALS = {
    'admin': 'admin123',  # username: password
    "manager": "manager123"
}

def require_admin():
    """Check if user is logged in as admin"""
    if "admin_user" not in session:
        return False
    return True

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        # Return admin login page
        login_html = """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>لوحة تحكم المدير - GoldEarn</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #fff;
                }
                .login-container {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 40px;
                    width: 400px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
                .logo {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .logo h1 {
                    color: #FFD700;
                    font-size: 2.5rem;
                    margin-bottom: 10px;
                }
                .logo p {
                    color: #ccc;
                    font-size: 1.1rem;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                .form-group label {
                    display: block;
                    margin-bottom: 8px;
                    color: #fff;
                    font-weight: 500;
                }
                .form-group input {
                    width: 100%;
                    padding: 12px 16px;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 0.1);
                    color: #fff;
                    font-size: 16px;
                    transition: all 0.3s ease;
                }
                .form-group input:focus {
                    outline: none;
                    border-color: #FFD700;
                    box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.2);
                }
                .form-group input::placeholder {
                    color: #aaa;
                }
                .login-btn {
                    width: 100%;
                    padding: 14px;
                    background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
                    color: #000;
                    border: none;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    margin-top: 10px;
                }
                .login-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3);
                }
                .error {
                    color: #ff6b6b;
                    text-align: center;
                    margin-top: 15px;
                    padding: 10px;
                    background: rgba(255, 107, 107, 0.1);
                    border-radius: 8px;
                    border: 1px solid rgba(255, 107, 107, 0.3);
                }
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="logo">
                    <h1>GoldEarn</h1>
                    <p>لوحة تحكم المدير</p>
                </div>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="username">اسم المستخدم</label>
                        <input type="text" id="username" name="username" placeholder="أدخل اسم المستخدم" required>
                    </div>
                    <div class="form-group">
                        <label for="password">كلمة المرور</label>
                        <input type="password" id="password" name="password" placeholder="أدخل كلمة المرور" required>
                    </div>
                    <button type="submit" class="login-btn">تسجيل الدخول</button>
                    <div id="error" class="error" style="display: none;"></div>
                </form>
            </div>
            
            <script>
                document.getElementById("loginForm").addEventListener("submit", async (e) => {
                    e.preventDefault();
                    const username = document.getElementById("username").value;
                    const password = document.getElementById("password").value;
                    const errorDiv = document.getElementById("error");
                    
                    try {
                        const response = await fetch("/api/admin/login", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({ username, password }),
                            credentials: "include"
                        });
                        
                        const data = await response.json();
                        
                        if (response.ok) {
                            window.location.href = "/api/admin/dashboard";
                        } else {
                            errorDiv.textContent = data.error;
                            errorDiv.style.display = "block";
                        }
                    } catch (error) {
                        errorDiv.textContent = "حدث خطأ في الاتصال";
                        errorDiv.style.display = "block";
                    }
                });
            </script>
        </body>
        </html>
        """
        return login_html
    
    # Handle POST request
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
            session["admin_user"] = username
            return jsonify({"message": "تم تسجيل الدخول بنجاح"}), 200
        else:
            return jsonify({"error": "اسم المستخدم أو كلمة المرور غير صحيح"}), 401
            
    except Exception as e:
        return jsonify({"error": "حدث خطأ في تسجيل الدخول"}), 500

@admin_bp.route("/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_user", None)
    return jsonify({"message": "تم تسجيل الخروج بنجاح"}), 200

@admin_bp.route("/dashboard")
def admin_dashboard():
    if not require_admin():
        return redirect("/api/admin/login")
    
    dashboard_html = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة تحكم المدير - GoldEarn</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                color: #333;
            }
            .header {
                background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
                color: #fff;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header h1 {
                color: #FFD700;
                display: inline-block;
            }
            .logout-btn {
                float: left;
                background: #ff4757;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            }
            .logout-btn:hover {
                background: #ff3742;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border-left: 5px solid #FFD700;
                transition: transform 0.3s ease;
            }
            .stat-card:hover {
                transform: translateY(-5px);
            }
            .stat-card h3 {
                color: #666;
                font-size: 14px;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .stat-card .value {
                font-size: 2.5rem;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 5px;
            }
            .stat-card .change {
                font-size: 14px;
                color: #27ae60;
            }
            .section {
                background: white;
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .section h2 {
                color: #2c3e50;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #FFD700;
            }
            .tabs {
                display: flex;
                margin-bottom: 20px;
                border-bottom: 1px solid #eee;
            }
            .tab {
                padding: 12px 24px;
                cursor: pointer;
                border-bottom: 3px solid transparent;
                transition: all 0.3s ease;
                font-weight: 500;
            }
            .tab.active {
                border-bottom-color: #FFD700;
                color: #FFD700;
            }
            .tab:hover {
                background: #f8f9fa;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            .table th, .table td {
                padding: 12px;
                text-align: right;
                border-bottom: 1px solid #eee;
            }
            .table th {
                background: #f8f9fa;
                font-weight: 600;
                color: #2c3e50;
            }
            .table tr:hover {
                background: #f8f9fa;
            }
            .status {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
            }
            .status.pending {
                background: #fff3cd;
                color: #856404;
            }
            .status.completed {
                background: #d4edda;
                color: #155724;
            }
            .status.rejected {
                background: #f8d7da;
                color: #721c24;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 12px;
                margin: 0 2px;
                transition: all 0.3s ease;
            }
            .btn-approve {
                background: #28a745;
                color: white;
            }
            .btn-approve:hover {
                background: #218838;
            }
            .btn-reject {
                background: #dc3545;
                color: white;
            }
            .btn-reject:hover {
                background: #c82333;
            }
            .btn-view {
                background: #007bff;
                color: white;
            }
            .btn-view:hover {
                background: #0056b3;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .no-data {
                text-align: center;
                padding: 40px;
                color: #999;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>لوحة تحكم المدير - GoldEarn</h1>
            <button class="logout-btn" onclick="logout()">تسجيل الخروج</button>
            <div style="clear: both;"></div>
        </div>
        
        <div class="container">
            <!-- Statistics Cards -->
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>إجمالي المستخدمين</h3>
                    <div class="value" id="totalUsers">-</div>
                    <div class="change">+12% من الشهر الماضي</div>
                </div>
                <div class="stat-card">
                    <h3>المعاملات المعلقة</h3>
                    <div class="value" id="pendingTransactions">-</div>
                    <div class="change">تحتاج مراجعة</div>
                </div>
                <div class="stat-card">
                    <h3>إجمالي الإيداعات</h3>
                    <div class="value" id="totalDeposits">-</div>
                    <div class="change">هذا الشهر</div>
                </div>
                <div class="stat-card">
                    <h3>المستخدمين النشطين</h3>
                    <div class="value" id="activeUsers">-</div>
                    <div class="change">آخر 7 أيام</div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="section">
                <h2>إدارة النظام</h2>
                <div class="tabs">
                    <div class="tab active" onclick="showTab('users')">المستخدمين</div>
                    <div class="tab" onclick="showTab('transactions')">المعاملات</div>
                    <div class="tab" onclick="showTab('vip')">باقات VIP</div>
                    <div class="tab" onclick="showTab('account_info')">معلومات الحسابات</div>
                    <div class="tab" onclick="showTab('reports')">التقارير</div>
                </div>
                
                <!-- Users Tab -->
                <div id="users" class="tab-content active">
                    <div class="loading" id="usersLoading">جاري تحميل المستخدمين...</div>
                    <div id="usersContent" style="display: none;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>رقم الهاتف</th>
                                    <th>مستوى VIP</th>
                                    <th>الرصيد</th>
                                    <th>تاريخ التسجيل</th>
                                    <th>الحالة</th>
                                    <th>الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody id="usersTable">
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Transactions Tab -->
                <div id="transactions" class="tab-content">
                    <div class="loading" id="transactionsLoading">جاري تحميل المعاملات...</div>
                    <div id="transactionsContent" style="display: none;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>المعرف</th>
                                    <th>المستخدم</th>
                                    <th>النوع</th>
                                    <th>المبلغ</th>
                                    <th>الحالة</th>
                                    <th>التاريخ</th>
                                    <th>الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody id="transactionsTable">
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- VIP Packages Tab -->
                <div id="vip" class="tab-content">
                    <div class="loading" id="vipLoading">جاري تحميل باقات VIP...</div>
                    <div id="vipContent" style="display: none;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>المستوى</th>
                                    <th>السعر</th>
                                    <th>الأرباح اليومية</th>
                                    <th>الإجراءات</th>
                                </tr>
                            </thead>
                            <tbody id="vipTable">
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Account Info Tab -->
                <div id="account_info" class="tab-content">
                    <div class="loading" id="accountInfoLoading">جاري تحميل معلومات الحسابات...</div>
                    <div id="accountInfoContent" style="display: none;">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>معرف المستخدم</th>
                                    <th>رقم الهاتف</th>
                                    <th>الرصيد</th>
                                    <th>مستوى VIP</th>
                                    <th>تاريخ التسجيل</th>
                                    <th>الحالة</th>
                                    <th>إجمالي الإيداعات</th>
                                    <th>إجمالي السحوبات</th>
                                    <th>أرباح المهام</th>
                                    <th>أرباح الإحالات</th>
                                </tr>
                            </thead>
                            <tbody id="accountInfoTable">
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Reports Tab -->
                <div id="reports" class="tab-content">
                    <div class="loading" id="reportsLoading">جاري تحميل التقارير...</div>
                    <div id="reportsContent" style="display: none;">
                        <p>إجمالي المستخدمين: <span id="reportTotalUsers">-</span></p>
                        <p>المستخدمون النشطون: <span id="reportActiveUsers">-</span></p>
                        <p>إجمالي الإيداعات: <span id="reportTotalDeposits">-</span></p>
                        <p>إجمالي السحوبات: <span id="reportTotalWithdrawals">-</span></p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function showTab(tabId) {
                document.querySelectorAll(".tab-content").forEach(content => {
                    content.classList.remove("active");
                });
                document.querySelectorAll(".tab").forEach(tab => {
                    tab.classList.remove("active");
                });
                document.getElementById(tabId).classList.add("active");
                document.querySelector(`.tab[onclick="showTab('${tabId}')"]`).classList.add("active");
                
                if (tabId === "users") {
                    fetchUsers();
                } else if (tabId === "transactions") {
                    fetchTransactions();
                } else if (tabId === "vip") {
                    fetchVIPPackages();
                } else if (tabId === "reports") {
                    fetchReports();
                } else if (tabId === "account_info") {
                    fetchAccountInfo();
                }
            }

            async function fetchUsers() {
                const usersLoading = document.getElementById("usersLoading");
                const usersContent = document.getElementById("usersContent");
                const usersTable = document.getElementById("usersTable");
                
                usersLoading.style.display = "block";
                usersContent.style.display = "none";
                usersTable.innerHTML = "";

                try {
                    const response = await fetch("/api/admin/users");
                    const users = await response.json();

                    if (users.length > 0) {
                        users.forEach(user => {
                            const row = usersTable.insertRow();
                            row.innerHTML = `
                                <td>${user.phone_number}</td>
                                <td>${user.vip_level}</td>
                                <td>${user.balance.toFixed(2)} EGP</td>
                                <td>${new Date(user.registration_date).toLocaleDateString("ar-EG")}</td>
                                <td><span class="status ${user.is_active ? "completed" : "rejected"}">${user.is_active ? "نشط" : "مجمد"}</span></td>
                                <td>
                                    <button class="btn btn-view" onclick="viewUser(${user.id})">عرض</button>
                                    <button class="btn ${user.is_active ? "btn-reject" : "btn-approve"}" onclick="toggleUserStatus(${user.id}, ${user.is_active})">${user.is_active ? "تجميد" : "تنشيط"}</button>
                                </td>
                            `;
                        });
                        usersContent.style.display = "block";
                    } else {
                        usersTable.innerHTML = '<tr><td colspan="6" class="no-data">لا يوجد مستخدمون لعرضهم.</td></tr>';
                        usersContent.style.display = "block";
                    }
                } catch (error) {
                    console.error("Error fetching users:", error);
                    usersTable.innerHTML = '<tr><td colspan="6" class="no-data">حدث خطأ أثناء تحميل المستخدمين.</td></tr>';
                    usersContent.style.display = "block";
                } finally {
                    usersLoading.style.display = "none";
                }
            }

            async function toggleUserStatus(userId, currentStatus) {
                const action = currentStatus ? "freeze" : "unfreeze";
                try {
                    const response = await fetch("/api/admin/users/toggle_status", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ user_id: userId, action: action }),
                        credentials: "include"
                    });
                    const data = await response.json();
                    if (response.ok) {
                        alert(data.message);
                        fetchUsers(); // Refresh the user list
                    } else {
                        alert(data.error);
                    }
                } catch (error) {
                    console.error("Error toggling user status:", error);
                    alert("حدث خطأ أثناء تغيير حالة المستخدم.");
                }
            }

            async function viewUser(userId) {
                alert(`عرض تفاصيل المستخدم رقم: ${userId}`);
                // Implement detailed user view logic here
            }

            async function fetchTransactions() {
                const transactionsLoading = document.getElementById("transactionsLoading");
                const transactionsContent = document.getElementById("transactionsContent");
                const transactionsTable = document.getElementById("transactionsTable");
                
                transactionsLoading.style.display = "block";
                transactionsContent.style.display = "none";
                transactionsTable.innerHTML = "";

                try {
                    const response = await fetch("/api/admin/transactions");
                    const transactions = await response.json();

                    if (transactions.length > 0) {
                        transactions.forEach(t => {
                            const row = transactionsTable.insertRow();
                            row.innerHTML = `
                                <td>${t.id}</td>
                                <td>${t.user_id}</td>
                                <td>${t.type === "deposit" ? "إيداع" : "سحب"}</td>
                                <td>${t.amount.toFixed(2)} EGP</td>
                                <td><span class="status ${t.status === "completed" ? "completed" : t.status === "pending" ? "pending" : "rejected"}">${t.status === "completed" ? "مكتمل" : t.status === "pending" ? "قيد الانتظار" : "مرفوض"}</span></td>
                                <td>${new Date(t.timestamp).toLocaleDateString("ar-EG")}</td>
                                <td>
                                    ${t.status === "pending" ? `
                                        <button class="btn btn-approve" onclick="approveTransaction(${t.id})">قبول</button>
                                        <button class="btn btn-reject" onclick="rejectTransaction(${t.id})">رفض</button>
                                    ` : ""} 
                                </td>
                            `;
                        });
                        transactionsContent.style.display = "block";
                    } else {
                        transactionsTable.innerHTML = '<tr><td colspan="7" class="no-data">لا يوجد معاملات لعرضها.</td></tr>';
                        transactionsContent.style.display = "block";
                    }
                } catch (error) {
                    console.error("Error fetching transactions:", error);
                    transactionsTable.innerHTML = '<tr><td colspan="7" class="no-data">حدث خطأ أثناء تحميل المعاملات.</td></tr>';
                    transactionsContent.style.display = "block";
                } finally {
                    transactionsLoading.style.display = "none";
                }
            }

            async function approveTransaction(transactionId) {
                try {
                    const response = await fetch("/api/admin/transactions/approve", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ transaction_id: transactionId }),
                        credentials: "include"
                    });
                    const data = await response.json();
                    if (response.ok) {
                        alert(data.message);
                        fetchTransactions();
                    } else {
                        alert(data.error);
                    }
                } catch (error) {
                    console.error("Error approving transaction:", error);
                    alert("حدث خطأ أثناء قبول المعاملة.");
                }
            }

            async function rejectTransaction(transactionId) {
                try {
                    const response = await fetch("/api/admin/transactions/reject", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ transaction_id: transactionId }),
                        credentials: "include"
                    });
                    const data = await response.json();
                    if (response.ok) {
                        alert(data.message);
                        fetchTransactions();
                    } else {
                        alert(data.error);
                    }
                } catch (error) {
                    console.error("Error rejecting transaction:", error);
                    alert("حدث خطأ أثناء رفض المعاملة.");
                }
            }

            async function fetchVIPPackages() {
                const vipLoading = document.getElementById("vipLoading");
                const vipContent = document.getElementById("vipContent");
                const vipTable = document.getElementById("vipTable");
                
                vipLoading.style.display = "block";
                vipContent.style.display = "none";
                vipTable.innerHTML = "";

                try {
                    const response = await fetch("/api/admin/vip_packages");
                    const packages = await response.json();

                    if (packages.length > 0) {
                        packages.forEach(p => {
                            const row = vipTable.insertRow();
                            row.innerHTML = `
                                <td>${p.level}</td>
                                <td>${p.price.toFixed(2)} EGP</td>
                                <td>${p.daily_earnings.toFixed(2)} EGP</td>
                                <td>
                                    <button class="btn btn-view" onclick="editVIPPackage(${p.id})">تعديل</button>
                                </td>
                            `;
                        });
                        vipContent.style.display = "block";
                    } else {
                        vipTable.innerHTML = '<tr><td colspan="4" class="no-data">لا توجد باقات VIP لعرضها.</td></tr>';
                        vipContent.style.display = "block";
                    }
                } catch (error) {
                    console.error("Error fetching VIP packages:", error);
                    vipTable.innerHTML = '<tr><td colspan="4" class="no-data">حدث خطأ أثناء تحميل باقات VIP.</td></tr>';
                    vipContent.style.display = "block";
                } finally {
                    vipLoading.style.display = "none";
                }
            }

            async function editVIPPackage(packageId) {
                alert(`تعديل باقة VIP رقم: ${packageId}`);
                // Implement VIP package edit logic here
            }

            async function fetchReports() {
                const reportsLoading = document.getElementById("reportsLoading");
                const reportsContent = document.getElementById("reportsContent");
                
                reportsLoading.style.display = "block";
                reportsContent.style.display = "none";

                try {
                    const response = await fetch("/api/admin/reports");
                    const reports = await response.json();

                    document.getElementById("reportTotalUsers").textContent = reports.total_users;
                    document.getElementById("reportActiveUsers").textContent = reports.active_users;
                    document.getElementById("reportTotalDeposits").textContent = reports.total_deposits.toFixed(2) + " EGP";
                    document.getElementById("reportTotalWithdrawals").textContent = reports.total_withdrawals.toFixed(2) + " EGP";
                    
                    reportsContent.style.display = "block";
                } catch (error) {
                    console.error("Error fetching reports:", error);
                    reportsContent.innerHTML = '<p class="no-data">حدث خطأ أثناء تحميل التقارير.</p>';
                    reportsContent.style.display = "block";
                } finally {
                    reportsLoading.style.display = "none";
                }
            }

            async function fetchAccountInfo() {
                const accountInfoLoading = document.getElementById("accountInfoLoading");
                const accountInfoContent = document.getElementById("accountInfoContent");
                const accountInfoTable = document.getElementById("accountInfoTable");
                
                accountInfoLoading.style.display = "block";
                accountInfoContent.style.display = "none";
                accountInfoTable.innerHTML = "";

                try {
                    const response = await fetch("/api/admin/account_info");
                    const accounts = await response.json();

                    if (accounts.length > 0) {
                        accounts.forEach(account => {
                            const row = accountInfoTable.insertRow();
                            row.innerHTML = `
                                <td>${account.user_id}</td>
                                <td>${account.phone_number}</td>
                                <td>${account.balance.toFixed(2)} EGP</td>
                                <td>${account.vip_level}</td>
                                <td>${new Date(account.registration_date).toLocaleDateString("ar-EG")}</td>
                                <td><span class="status ${account.is_active ? "completed" : "rejected"}">${account.is_active ? "نشط" : "مجمد"}</span></td>
                                <td>${account.total_deposits.toFixed(2)} EGP</td>
                                <td>${account.total_withdrawals.toFixed(2)} EGP</td>
                                <td>${account.total_task_earnings.toFixed(2)} EGP</td>
                                <td>${account.total_referral_earnings.toFixed(2)} EGP</td>
                            `;
                        });
                        accountInfoContent.style.display = "block";
                    } else {
                        accountInfoTable.innerHTML = '<tr><td colspan="10" class="no-data">لا توجد معلومات حسابات لعرضها.</td></tr>';
                        accountInfoContent.style.display = "block";
                    }
                } catch (error) {
                    console.error("Error fetching account info:", error);
                    accountInfoTable.innerHTML = '<tr><td colspan="10" class="no-data">حدث خطأ أثناء تحميل معلومات الحسابات.</td></tr>';
                    accountInfoContent.style.display = "block";
                } finally {
                    accountInfoLoading.style.display = "none";
                }
            }

            async function logout() {
                try {
                    const response = await fetch("/api/admin/logout", {
                        method: "POST",
                        credentials: "include"
                    });
                    if (response.ok) {
                        window.location.href = "/api/admin/login";
                    } else {
                        alert("فشل تسجيل الخروج.");
                    }
                } catch (error) {
                    console.error("Error logging out:", error);
                    alert("حدث خطأ أثناء تسجيل الخروج.");
                }
            }

            // Initial load
            document.addEventListener("DOMContentLoaded", () => {
                showTab("users");
            });
        </script>
    </body>
    </html>
    """
    return dashboard_html

@admin_bp.route("/users", methods=["GET"])
def get_users():
    """Get all users for admin dashboard"""
    if not require_admin():
        return jsonify({"error": "غير مصرح"}), 401
    
    try:
        users = User.query.all()
        users_data = []
        
        for user in users:
            users_data.append({
                "id": user.id,
                "phone_number": user.phone_number,
                "balance": float(user.balance),
                "vip_level": user.vip_level,
                "registration_date": user.registration_date.isoformat(),
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        return jsonify(users_data), 200
        
    except Exception as e:
        return jsonify({"error": "حدث خطأ في جلب المستخدمين"}), 500

@admin_bp.route("/users/toggle_status", methods=["POST"])
def toggle_user_status():
    """Toggle user active status (freeze/unfreeze)"""
    if not require_admin():
        return jsonify({"error": "غير مصرح"}), 401
    
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        action = data.get("action")  # "freeze" or "unfreeze"
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "المستخدم غير موجود"}), 404
        
        if action == "freeze":
            user.is_active = False
            message = f"تم تجميد حساب المستخدم {user.phone_number}"
        elif action == "unfreeze":
            user.is_active = True
            message = f"تم تنشيط حساب المستخدم {user.phone_number}"
        else:
            return jsonify({"error": "إجراء غير صحيح"}), 400
        
        db.session.commit()
        return jsonify({"message": message}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "حدث خطأ في تغيير حالة المستخدم"}), 500

@admin_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user_details(user_id):
    """Get detailed information about a specific user"""
    if not require_admin():
        return jsonify({"error": "غير مصرح"}), 401
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "المستخدم غير موجود"}), 404
        
        # Get user transactions
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(desc(Transaction.created_at)).all()
        
        # Get user tasks
        user_tasks = UserTask.query.filter_by(user_id=user_id).all()
        
        # Get referrals
        referrals = Referral.query.filter_by(referrer_id=user_id).all()
        
        # Calculate statistics
        total_deposits = sum([t.amount for t in transactions if t.type == "deposit" and t.status == "completed"])
        total_withdrawals = sum([t.amount for t in transactions if t.type == "withdrawal" and t.status == "completed"])
        total_task_earnings = sum([task.reward for task in user_tasks])
        total_referral_earnings = sum([ref.commission for ref in referrals])
        
        user_data = {
            "id": user.id,
            "phone_number": user.phone_number,
            "balance": float(user.balance),
            "vip_level": user.vip_level,
            "registration_date": user.registration_date.isoformat(),
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "statistics": {
                "total_deposits": float(total_deposits),
                "total_withdrawals": float(total_withdrawals),
                "total_task_earnings": float(total_task_earnings),
                "total_referral_earnings": float(total_referral_earnings),
                "total_transactions": len(transactions),
                "completed_tasks": len(user_tasks),
                "referrals_count": len(referrals)
            },
            "recent_transactions": [
                {
                    "id": t.id,
                    "type": t.type,
                    "amount": float(t.amount),
                    "status": t.status,
                    "created_at": t.created_at.isoformat()
                } for t in transactions[:10]  # Last 10 transactions
            ]
        }
        
        return jsonify(user_data), 200
        
    except Exception as e:
        return jsonify({"error": "حدث خطأ في جلب تفاصيل المستخدم"}), 500

@admin_bp.route("/account_info", methods=["GET"])
def get_account_info():
    """Get comprehensive account information for all users"""
    if not require_admin():
        return jsonify({"error": "غير مصرح"}), 401
    
    try:
        users = User.query.all()
        account_info = []
        
        for user in users:
            # Calculate user statistics
            transactions = Transaction.query.filter_by(user_id=user.id).all()
            user_tasks = UserTask.query.filter_by(user_id=user.id).all()
            referrals = Referral.query.filter_by(referrer_id=user.id).all()
            
            total_deposits = sum([t.amount for t in transactions if t.type == "deposit" and t.status == "completed"])
            total_withdrawals = sum([t.amount for t in transactions if t.type == "withdrawal" and t.status == "completed"])
            total_task_earnings = sum([task.reward for task in user_tasks])
            total_referral_earnings = sum([ref.commission for ref in referrals])
            
            account_info.append({
                "user_id": user.id,
                "phone_number": user.phone_number,
                "balance": float(user.balance),
                "vip_level": user.vip_level,
                "registration_date": user.registration_date.isoformat(),
                "is_active": user.is_active,
                "total_deposits": float(total_deposits),
                "total_withdrawals": float(total_withdrawals),
                "total_task_earnings": float(total_task_earnings),
                "total_referral_earnings": float(total_referral_earnings)
            })
        
        return jsonify(account_info), 200
        
    except Exception as e:
        return jsonify({"error": "حدث خطأ في جلب معلومات الحسابات"}), 500

@admin_bp.route("/transactions", methods=["GET"])
def get_transactions():
    if not require_admin():
        return jsonify({"error": "غير مصرح لك بالوصول"}), 403
    
    transactions = Transaction.query.all()
    transactions_data = [{
        "id": t.id,
        "user_id": t.user_id,
        "type": t.type,
        "amount": t.amount,
        "status": t.status,
        "timestamp": t.timestamp.isoformat()
    } for t in transactions]
    return jsonify(transactions_data), 200

@admin_bp.route("/transactions/approve", methods=["POST"])
def approve_transaction():
    if not require_admin():
        return jsonify({"error": "غير مصرح لك بالوصول"}), 403
    
    data = request.get_json()
    transaction_id = data.get("transaction_id")
    
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "المعاملة غير موجودة"}), 404
    
    if transaction.status != "pending":
        return jsonify({"error": "لا يمكن الموافقة على هذه المعاملة"}), 400
    
    transaction.status = "completed"
    
    # Update user balance if it's a deposit
    if transaction.type == "deposit":
        user = User.query.get(transaction.user_id)
        user.balance += transaction.amount
    
    db.session.commit()
    return jsonify({"message": "تم قبول المعاملة بنجاح"}), 200

@admin_bp.route("/transactions/reject", methods=["POST"])
def reject_transaction():
    if not require_admin():
        return jsonify({"error": "غير مصرح لك بالوصول"}), 403
    
    data = request.get_json()
    transaction_id = data.get("transaction_id")
    
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "المعاملة غير موجودة"}), 404
    
    if transaction.status != "pending":
        return jsonify({"error": "لا يمكن رفض هذه المعاملة"}), 400
    
    transaction.status = "rejected"
    db.session.commit()
    return jsonify({"message": "تم رفض المعاملة بنجاح"}), 200

@admin_bp.route("/vip_packages", methods=["GET"])
def get_vip_packages():
    if not require_admin():
        return jsonify({"error": "غير مصرح لك بالوصول"}), 403
    
    vip_packages = VIPPackage.query.all()
    packages_data = [{
        "id": p.id,
        "level": p.level,
        "price": p.price,
        "daily_earnings": p.daily_earnings
    } for p in vip_packages]
    return jsonify(packages_data), 200

@admin_bp.route("/reports", methods=["GET"])
def get_reports():
    if not require_admin():
        return jsonify({"error": "غير مصرح لك بالوصول"}), 403
    
    # Example report data (can be expanded)
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_deposits = db.session.query(func.sum(Transaction.amount)).filter_by(type="deposit", status="completed").scalar() or 0
    total_withdrawals = db.session.query(func.sum(Transaction.amount)).filter_by(type="withdrawal", status="completed").scalar() or 0

    report_data = {
        "total_users": total_users,
        "active_users": active_users,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals
    }
    return jsonify(report_data), 200

