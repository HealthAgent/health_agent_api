import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_path="hiking_gear.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """데이터베이스 초기화 및 테이블 생성"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 사용자 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 등산 용품 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS hiking_gear (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                brand TEXT,
                purchase_date DATE,
                price DECIMAL(10,2),
                weight_g INTEGER,
                notes TEXT,
                condition TEXT DEFAULT 'new',
                last_used_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 카테고리 마스터 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS gear_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        
        # 기본 카테고리 삽입
        categories = [
            ('신발', '등산화, 트레일러닝화 등'),
            ('의류', '자켓, 팬츠, 양말 등'),
            ('배낭', '배낭, 가방류'),
            ('장비', '텐트, 스틱, 랜턴 등'),
            ('안전장비', '응급키트, 생존장비 등')
        ]
        
        for category in categories:
            try:
                c.execute('INSERT INTO gear_categories (category_name, description) VALUES (?, ?)', category)
            except sqlite3.IntegrityError:
                pass  # 이미 존재하는 카테고리는 무시
        
        conn.commit()
        conn.close()

    def create_user(self, username, email=None):
        """새로운 사용자 생성"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, email) VALUES (?, ?)', (username, email))
            user_id = c.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_user(self, username):
        """사용자 정보 조회"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        return user

    def add_hiking_gear(self, user_id, item_data):
        """새로운 등산 용품 추가"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO hiking_gear 
                (user_id, item_name, category, brand, purchase_date, price, 
                weight_g, notes, condition, last_used_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                item_data['item_name'],
                item_data['category'],
                item_data.get('brand'),
                item_data.get('purchase_date'),
                item_data.get('price'),
                item_data.get('weight_g'),
                item_data.get('notes'),
                item_data.get('condition', 'new'),
                item_data.get('last_used_date')
            ))
            gear_id = c.lastrowid
            conn.commit()
            return gear_id
        except Exception as e:
            print(f"Error adding hiking gear: {e}")
            return None
        finally:
            conn.close()

    def get_user_gear(self, user_id):
        """사용자의 등산 용품 목록 조회"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT hg.*, gc.category_name 
            FROM hiking_gear hg
            JOIN gear_categories gc ON hg.category = gc.category_name
            WHERE hg.user_id = ?
            ORDER BY hg.category, hg.item_name
        ''', (user_id,))
        items = c.fetchall()
        conn.close()
        return items

    def update_gear_condition(self, gear_id, condition, last_used_date=None):
        """등산 용품 상태 업데이트"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            if last_used_date:
                c.execute('''
                    UPDATE hiking_gear 
                    SET condition = ?, last_used_date = ?
                    WHERE id = ?
                ''', (condition, last_used_date, gear_id))
            else:
                c.execute('''
                    UPDATE hiking_gear 
                    SET condition = ?
                    WHERE id = ?
                ''', (condition, gear_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating gear condition: {e}")
            return False
        finally:
            conn.close()

    def get_categories(self):
        """등산 용품 카테고리 목록 조회"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT category_name, description FROM gear_categories')
        categories = c.fetchall()
        conn.close()
        return categories
