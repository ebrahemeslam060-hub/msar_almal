"""
====================================================================
Project Name : مسار المال (Masar Al-Mal) - Smart Financial & Shopping Planner
Developer    : إسلام إبراهيم (Eslam Ibrahim)
Version      : v3.1.2 (Optimized & Cleaned)
Watermark    : Developed with precision & dedication by إسلام إبراهيم
====================================================================
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os
from datetime import datetime
import sqlite3
import csv
import json

app = Flask(__name__)
app.secret_key = 'masar_al_mal_ultra_secure_key'

DB_NAME = "masar.db"
SHARED_SECRET = "JBSWY3DPEHPK3PXP" 

APP_INFO = {
    "name": "مسار المال (Masar Al-Mal)",
    "developer": "إسلام إبراهيم (Eslam Ibrahim)",
    "version": "3.1.2",
    "watermark": "Powered by Masar Al-Mal Engine | Created by Eslam Ibrahim"
}

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def generate_shopping_list_data():
    shopping_list = {
        "المنزل": {
            "صدور دجاج": "6 كيلو",
            "لحم مفروم": "3 كيلو",
            "سمك طازج": "3 كيلو",
            "بطاطس": "16 كيلو",
            "خيار": "12 كيلو",
            "بصل وثوم": "10 كيلو",
            "طماطم": "8 كيلو",
            "كوسة": "8 كيلو",
            "فلفل رومي وألوان": "4 كيلو",
            "فاكهة موسمية": "8 كيلو",
            "أرز أبيض": "9 كيلو",
            "مكرونة متنوعة": "6 كيلو",
            "بيض بلدي": "120 بيضة",
            "جبن قريش وثلاجة": "8 كيلو",
            "بقوليات (عدس + فول)": "2 كيلو"
        },
        "القطط": {
            "صدور دجاج مسلوقة": "5 كيلو",
            "كبدة دجاج": "2 كيلو",
            "سمك مخلى": "2 كيلو",
            "بطاطس مسلوقة": "1 كيلو",
            "كوسة مسلوقة": "1 كيلو",
            "أرز مسلوق": "2 كيلو",
            "بيض مسلوق": "16 بيضة",
            "زبادي سادة": "32 علبة"
        }
    }
    
    daily_nutrition_avg = {
        "المنزل (لكل فرد يومياً)": {
            "البروتين المتوسط": "92 جرام",
            "الكربوهيدرات المتوسطة": "210 جرام",
            "الدهون الصحية": "45 جرام",
            "السعرات الحرارية المقدرة": "1613 سعرة حرارية"
        },
        "القطط (لكل قطة يومياً)": {
            "البروتين المتوسط": "38 جرام",
            "الكربوهيدرات المتوسطة": "12 جرام",
            "الدهون المتوسطة": "8 جرام",
            "السعرات الحرارية المقدرة": "272 سعرة حرارية"
        }
    }

    return shopping_list, daily_nutrition_avg

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                phone TEXT,
                role TEXT DEFAULT 'user'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                salary REAL,
                days INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                time TEXT,
                action_type TEXT,
                category TEXT,
                cat_type TEXT,
                amount REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                type TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_meal_state (
                user_id INTEGER PRIMARY KEY,
                shopping_list_json TEXT,
                daily_nutrition_json TEXT,
                last_updated TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        for table in ['settings', 'transactions', 'categories']:
            try:
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN user_id INTEGER')
            except sqlite3.OperationalError:
                pass
        
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (username, password, role) VALUES (?, ?, ?)
            ''', ('admin', 'admin123', 'admin'))
            admin_id = cursor.lastrowid
            
            default_cats = [
                ("طعام", "operational"),
                ("طلب خاص", "operational"),
                ("🧾 فاتورة الموبيل", "fixed"),
                ("🚨 طوارئ", "emergency")
            ]
            for name, cat_type in default_cats:
                cursor.execute('INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)', (admin_id, name, cat_type))
                
            s_list, d_nutr = generate_shopping_list_data()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute('''
                INSERT OR REPLACE INTO user_meal_state (user_id, shopping_list_json, daily_nutrition_json, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (admin_id, json.dumps(s_list, ensure_ascii=False), json.dumps(d_nutr, ensure_ascii=False), now_str))

        conn.commit()

init_db()

DEFAULT_CATEGORIES = [
    ("طعام", "operational"),
    ("طلب خاص", "operational"),
    ("🧾 فاتورة الموبيل", "fixed"),
    ("🚨 طوارئ", "emergency")
]

class RecipeNutritionalCalculator:
    def __init__(self):
        self.database = {
            "لحمة حمراء": {"protein": 0.22, "carbs": 0.00, "fat": 0.06, "water": 0.70},
            "لحمة مفرومة": {"protein": 0.18, "carbs": 0.00, "fat": 0.20, "water": 0.60},
            "اسماك": {"protein": 0.20, "carbs": 0.00, "fat": 0.017, "water": 0.78},
            "دجاج": {"protein": 0.23, "carbs": 0.00, "fat": 0.025, "water": 0.74},
            "كبدة واوانص": {"protein": 0.19, "carbs": 0.01, "fat": 0.05, "water": 0.73},
            "فراخ": {"protein": 0.16, "carbs": 0.12, "fat": 0.06, "water": 0.64},
            "بيض": {"protein": 0.13, "carbs": 0.01, "fat": 0.095, "water": 0.76},
            "طماطم": {"protein": 0.009, "carbs": 0.039, "fat": 0.002, "water": 0.94},
            "خيار": {"protein": 0.007, "carbs": 0.036, "fat": 0.001, "water": 0.95},
            "بصل": {"protein": 0.011, "carbs": 0.093, "fat": 0.001, "water": 0.89},
            "بطاطس": {"protein": 0.020, "carbs": 0.170, "fat": 0.001, "water": 0.79},
            "كوسة": {"protein": 0.012, "carbs": 0.031, "fat": 0.003, "water": 0.94},
            "بسلة": {"protein": 0.054, "carbs": 0.145, "fat": 0.004, "water": 0.78},
            "جزر": {"protein": 0.009, "carbs": 0.096, "fat": 0.002, "water": 0.88},
            "فاصوليا خضراء": {"protein": 0.018, "carbs": 0.070, "fat": 0.002, "water": 0.90},
            "خص": {"protein": 0.014, "carbs": 0.029, "fat": 0.002, "water": 0.95},
            "فلفل رومي": {"protein": 0.009, "carbs": 0.046, "fat": 0.002, "water": 0.92},
            "سمنة نباتي": {"protein": 0.00, "carbs": 0.00, "fat": 1.00, "water": 0.001},
            "زيت زيتون": {"protein": 0.00, "carbs": 0.00, "fat": 1.00, "water": 0.00},
            "زيت نباتي": {"protein": 0.00, "carbs": 0.00, "fat": 1.00, "water": 0.00},
            "فول": {"protein": 0.26, "carbs": 0.58, "fat": 0.015, "water": 0.11},
            "شوفان": {"protein": 0.17, "carbs": 0.66, "fat": 0.07, "water": 0.08},
            "فريك": {"protein": 0.13, "carbs": 0.71, "fat": 0.025, "water": 0.10},
            "قمح": {"protein": 0.125, "carbs": 0.71, "fat": 0.02, "water": 0.11},
            "أرز": {"protein": 0.07, "carbs": 0.80, "fat": 0.006, "water": 0.12},
            "مكرونة": {"protein": 0.13, "carbs": 0.75, "fat": 0.015, "water": 0.10},
            "الخبز البلدي": {"protein": 0.09, "carbs": 0.50, "fat": 0.012, "water": 0.36},
            "حليب": {"protein": 0.032, "carbs": 0.048, "fat": 0.033, "water": 0.88},
            "جبنة قريش": {"protein": 0.110, "carbs": 0.034, "fat": 0.043, "water": 0.80},
            "جبنة ثلاجة": {"protein": 0.140, "carbs": 0.040, "fat": 0.200, "water": 0.55}
        }

    def calculate_meal(self, ingredients_dict):
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_water = 0.0
        details = []

        for item, grams in ingredients_dict.items():
            if item in self.database and grams > 0:
                p = self.database[item]["protein"] * grams
                c = self.database[item]["carbs"] * grams
                f = self.database[item]["fat"] * grams
                w = self.database[item]["water"] * grams
                
                total_protein += p
                total_carbs += c
                total_fat += f
                total_water += w
                
                details.append({
                    "item": item,
                    "grams": grams,
                    "protein": round(p, 2),
                    "carbs": round(c, 2),
                    "fat": round(f, 2)
                })

        estimated_calories = (total_protein * 4) + (total_carbs * 4) + (total_fat * 9)

        return {
            "details": details,
            "totals": {
                "protein": round(total_protein, 2),
                "carbs": round(total_carbs, 2),
                "fat": round(total_fat, 2),
                "water": round(total_water, 2),
                "calories": round(estimated_calories, 2)
            }
        }

diet_calculator = RecipeNutritionalCalculator()

@app.context_processor
def inject_app_info():
    return dict(app_info=APP_INFO)

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
            user = cursor.fetchone()

            if user:
                session.permanent = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                
                if user['role'] == 'admin':
                    if request.is_json:
                        return jsonify({'status': 'success', 'redirect': '/admin'})
                    return redirect(url_for('admin_dashboard'))
                
                if request.is_json:
                    return jsonify({'status': 'success', 'redirect': '/tracker'})
                return redirect(url_for('index'))
            else:
                msg = "اسم المستخدم أو كلمة المرور غير صحيحة"
                if request.is_json:
                    return jsonify({'status': 'error', 'message': msg})
                return render_template('login.html', error=msg, secret=SHARED_SECRET)

    return render_template('login.html', secret=SHARED_SECRET)

@app.route('/login-as-guest', methods=['GET', 'POST'])
def login_as_guest():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', ('guest_user',))
        guest = cursor.fetchone()
        
        if not guest:
            cursor.execute('''
                INSERT INTO users (username, password, role) VALUES (?, ?, ?)
            ''', ('guest_user', 'guest123', 'guest'))
            guest_id = cursor.lastrowid
            
            for name, cat_type in DEFAULT_CATEGORIES:
                cursor.execute('INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)', (guest_id, name, cat_type))
                
            s_list, d_nutr = generate_shopping_list_data()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute('''
                INSERT OR REPLACE INTO user_meal_state (user_id, shopping_list_json, daily_nutrition_json, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (guest_id, json.dumps(s_list, ensure_ascii=False), json.dumps(d_nutr, ensure_ascii=False), now_str))
            
            cursor.execute('''
                INSERT OR REPLACE INTO settings (user_id, salary, days) VALUES (?, ?, ?)
            ''', (guest_id, 10000.0, 30))
            
            conn.commit()
        else:
            guest_id = guest['id']
            cursor.execute('SELECT salary FROM settings WHERE user_id = ?', (guest_id,))
            if not cursor.fetchone():
                cursor.execute('INSERT OR REPLACE INTO settings (user_id, salary, days) VALUES (?, ?, ?)', (guest_id, 10000.0, 30))
                conn.commit()

        session.permanent = True
        session['user_id'] = guest_id
        session['username'] = 'زائر النظام'
        session['role'] = 'guest'

    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('register.html', error="برجاء إدخال اسم المستخدم وكلمة المرور!")

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                user_id = cursor.lastrowid
                
                for name, cat_type in DEFAULT_CATEGORIES:
                    cursor.execute('INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)', (user_id, name, cat_type))
                
                s_list, d_nutr = generate_shopping_list_data()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute('''
                    INSERT OR REPLACE INTO user_meal_state (user_id, shopping_list_json, daily_nutrition_json, last_updated)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, json.dumps(s_list, ensure_ascii=False), json.dumps(d_nutr, ensure_ascii=False), now_str))
                
                conn.commit()
                
                session.permanent = True
                session['user_id'] = user_id
                session['username'] = username
                session['role'] = 'user'
                
                return redirect(url_for('setup'))
            except sqlite3.IntegrityError:
                return render_template('register.html', error="اسم المستخدم مستخدم بالفعل، اختر اسماً آخر.")
                
    return render_template('register.html')

@app.route('/')
@app.route('/tracker')
def index():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT salary, days FROM settings WHERE user_id = ?', (user_id,))
        setting = cursor.fetchone()
        
        if not setting or setting['salary'] is None:
            return redirect(url_for('setup'))

        salary = float(setting['salary'])
        days = int(setting['days'])

        cursor.execute('SELECT id, name, type FROM categories WHERE user_id = ?', (user_id,))
        categories = [dict(row) for row in cursor.fetchall()]

        # فلترة العمليات حسب الاختيار (مصروف أو دخل إضافي)
        action_filter = request.args.get('action_filter')
        if action_filter in ['مصروف', 'دخل إضافي']:
            cursor.execute('SELECT id, time, action_type, category, cat_type, amount FROM transactions WHERE user_id = ? AND action_type = ? ORDER BY id DESC', (user_id, action_filter))
        else:
            cursor.execute('SELECT id, time, action_type, category, cat_type, amount FROM transactions WHERE user_id = ? ORDER BY id DESC', (user_id,))
            
        transactions = [dict(row) for row in cursor.fetchall()]

    budget_fixed = salary * 0.50
    budget_investment = salary * 0.20
    budget_assets = salary * 0.10
    budget_skills = salary * 0.10
    budget_entertainment = salary * 0.05
    budget_emergency = salary * 0.05
        
    total_fixed = sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'fixed' and tx['action_type'] == 'مصروف') - sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'fixed' and tx['action_type'] == 'دخل إضافي')
    total_investment = sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'investment' and tx['action_type'] == 'مصروف') - sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'investment' and tx['action_type'] == 'دخل إضافي')
    total_assets = sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'assets' and tx['action_type'] == 'مصروف') - sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'assets' and tx['action_type'] == 'دخل إضافي')
    total_skills = sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'skills' and tx['action_type'] == 'مصروف') - sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'skills' and tx['action_type'] == 'دخل إضافي')
    total_entertainment = sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'entertainment' and tx['action_type'] == 'مصروف') - sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'entertainment' and tx['action_type'] == 'دخل إضافي')
    total_emergency = sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'emergency' and tx['action_type'] == 'مصروف') - sum(tx['amount'] for tx in transactions if tx['cat_type'] == 'emergency' and tx['action_type'] == 'دخل إضافي')

    return render_template(
        'tracker.html', 
        username=session.get('username'),
        role=session.get('role'),
        transactions=transactions,
        categories=categories,
        total_fixed_expenses=total_fixed,
        total_investment_expenses=total_investment,
        total_assets_expenses=total_assets,
        total_skills_expenses=total_skills,
        total_entertainment_expenses=total_entertainment,
        total_emergency_expenses=total_emergency,
        budget_fixed=budget_fixed,
        budget_investment=budget_investment,
        budget_assets=budget_assets,
        budget_skills=budget_skills,
        budget_entertainment=budget_entertainment,
        budget_emergency=budget_emergency,
        rem_fixed=budget_fixed - total_fixed,
        rem_investment=budget_investment - total_investment,
        rem_assets=budget_assets - total_assets,
        rem_skills=budget_skills - total_skills,
        rem_entertainment=budget_entertainment - total_entertainment,
        rem_emergency=budget_emergency - total_emergency,
        daily_current=budget_fixed / days if days > 0 else 0,
        current_filter=action_filter
    )

@app.route('/api/get_planner_state', methods=['GET'])
def get_planner_state():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shopping_list_json, daily_nutrition_json, last_updated FROM user_meal_state WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()

    if not row:
        s_list, d_nutr = generate_shopping_list_data()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_meal_state (user_id, shopping_list_json, daily_nutrition_json, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (user_id, json.dumps(s_list, ensure_ascii=False), json.dumps(d_nutr, ensure_ascii=False), now_str))
            conn.commit()
        return jsonify({
            'status': 'success',
            'shopping_list': s_list,
            'daily_nutrition': d_nutr,
            'last_updated': now_str
        })

    return jsonify({
        'status': 'success',
        'shopping_list': json.loads(row['shopping_list_json']),
        'daily_nutrition': json.loads(row['daily_nutrition_json']),
        'last_updated': row['last_updated']
    })

@app.route('/calculate-meal-nutrition', methods=['POST'])
def calculate_meal_nutrition():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.json or {}
    ingredients = data.get('ingredients', {}) 
    
    result = diet_calculator.calculate_meal(ingredients)
    return jsonify({'status': 'success', 'nutrition': result, 'watermark': APP_INFO['watermark']})

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        salary_val = request.form.get('main_salary') or request.form.get('salary') or request.form.get('budget') or 0
        days_val = request.form.get('days_count') or request.form.get('days') or 30

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO settings (user_id, salary, days) VALUES (?, ?, ?)', (user_id, float(salary_val), int(days_val)))
            cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            conn.commit()
            
        return redirect(url_for('index'))
        
    return render_template('setup.html')

@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC', (user_id,))
        transactions = [dict(row) for row in cursor.fetchall()]
        
    return render_template('history.html', transactions=transactions)

@app.route('/save_daily_report', methods=['POST'])
def save_daily_report():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    target_dir = os.path.join(os.getcwd(), 'daily_reports')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    filename = f'Masar_Al_Mal_Report_User_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    file_path = os.path.join(target_dir, filename)

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT time, action_type, category, cat_type, amount FROM transactions WHERE user_id = ? ORDER BY id DESC', (user_id,))
            rows = cursor.fetchall()

        with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([f"# Report Generated by {APP_INFO['name']} - Developer: {APP_INFO['developer']} - Version: {APP_INFO['version']}"])
            writer.writerow(['التاريخ والوقت', 'نوع الحركة', 'التصنيف الفرعي', 'نوع الميزانية', 'المبلغ'])
            for row in rows:
                writer.writerow([row['time'], row['action_type'], row['category'], row['cat_type'], row['amount']])
        
        return send_from_directory(target_dir, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/add_expense', methods=['POST'])
def add_expense():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    action_type = request.form.get('action_type')
    category_name = request.form.get('category')
    custom_date = request.form.get('transaction_date')
    amount = float(request.form.get('amount', 0))

    if custom_date:
        try:
            formatted_time = datetime.strptime(custom_date, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT type FROM categories WHERE user_id = ? AND name = ?', (user_id, category_name))
        row = cursor.fetchone()
        cat_type = row['type'] if row else "fixed"

        cursor.execute(
            'INSERT INTO transactions (user_id, time, action_type, category, cat_type, amount) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, formatted_time, action_type, category_name, cat_type, amount)
        )
        conn.commit()

    return redirect(url_for('index'))

@app.route('/add_category', methods=['POST'])
def add_category():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    cat_name = request.form.get('category_name') or request.form.get('name') or request.form.get('title')
    cat_type = request.form.get('category_type') or request.form.get('type') or 'fixed'

    if cat_name:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM categories WHERE user_id = ? AND name = ?', (user_id, cat_name))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)', (user_id, cat_name, cat_type))
                conn.commit()

    return redirect(url_for('index'))

@app.route('/delete_category/<int:cat_id>', methods=['POST', 'GET'])
def delete_category(cat_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM categories WHERE id = ? AND user_id = ?', (cat_id, user_id))
        conn.commit()

    return redirect(url_for('index'))

@app.route('/delete_transaction/<int:tx_id>', methods=['POST', 'GET'])
def delete_transaction(tx_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (tx_id, user_id))
        conn.commit()

    return redirect(url_for('index'))

@app.route('/reset_all', methods=['POST'])
def reset_all():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        conn.commit()

    return jsonify({'status': 'success', 'redirect': url_for('index')})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def is_admin():
    return session.get('role') == 'admin'

@app.route('/admin')
def admin_dashboard():
    if not session.get('user_id') or not is_admin():
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/admin/users', methods=['GET'])
def get_users():
    if not is_admin():
        return jsonify({'status': 'error', 'message': 'غير مصرح لك بالوصول'}), 403
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, phone FROM users")
        users = [dict(row) for row in cursor.fetchall()]
        
    return jsonify({'status': 'success', 'users': users})

@app.route('/admin/reset_password', methods=['POST'])
def admin_reset_password():
    if not is_admin():
        return jsonify({'status': 'error', 'message': 'غير مصرح لك بالوصول'}), 403
        
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('new_password')
    
    if not username or not new_password:
        return jsonify({'status': 'error', 'message': 'برجاء إدخال اسم المستخدم وكلمة المرور الجديدة'}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'المستخدم غير موجود'})
            
    return jsonify({'status': 'success', 'message': f'تم تغيير كلمة المرور للمستخدم [{username}] بنجاح!'})

@app.route('/admin/delete_user/<int:target_user_id>', methods=['DELETE'])
def admin_delete_user(target_user_id):
    if not is_admin():
        return jsonify({'status': 'error', 'message': 'غير مصرح لك بالوصول'}), 403
        
    if target_user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': 'لا يمكنك حذف حسابك الشخصي كمسؤول.'}), 400
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (target_user_id,))
        cursor.execute("DELETE FROM categories WHERE user_id = ?", (target_user_id,))
        cursor.execute("DELETE FROM settings WHERE user_id = ?", (target_user_id,))
        cursor.execute("DELETE FROM user_meal_state WHERE user_id = ?", (target_user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
        conn.commit()
        
    return jsonify({'status': 'success', 'message': 'تم حذف المستخدم وكافة بياناته المرتبطة نهائياً.'})

if __name__ == '__main__':
    print(f"[*] Starting {APP_INFO['name']} v{APP_INFO['version']} by {APP_INFO['developer']}...")
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
