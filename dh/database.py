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

        # 대화 기록 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 대화 메시지 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
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

        # 추천 상품 테이블
        c.execute('''
            CREATE TABLE IF NOT EXISTS recommended_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                product_name TEXT NOT NULL,
                brand TEXT,
                price DECIMAL(10,2),
                description TEXT,
                purchase_link TEXT,
                related_category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # 기본 추천 상품 삽입
        recommended_products = [
            ('등산화', '트레일러닝화', '살로몬', 150000, '가벼운 트레일러닝화', 'https://example.com/shoes1', '등산양말'),
            ('등산화', '등산화', '라스포티바', 200000, '안정적인 등산화', 'https://example.com/shoes2', '등산양말'),
            ('등산양말', '등산양말', '스마트울', 25000, '통기성 좋은 등산양말', 'https://example.com/socks1', '등산화'),
            ('배낭', '등산배낭', '오스프리', 180000, '30L 등산배낭', 'https://example.com/backpack1', '등산용품'),
            ('등산용품', '물통', '나이겐', 15000, '1L 물통', 'https://example.com/bottle1', '배낭')
        ]

        for product in recommended_products:
            try:
                c.execute('''
                    INSERT INTO recommended_products 
                    (category, product_name, brand, price, description, purchase_link, related_category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', product)
            except sqlite3.IntegrityError:
                pass

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

    def get_recommended_products(self, category=None, related_category=None):
        """추천 상품 목록 조회"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        if category and related_category:
            c.execute('''
                SELECT * FROM recommended_products 
                WHERE category = ? OR related_category = ?
                ORDER BY category, product_name
            ''', (category, related_category))
        elif category:
            c.execute('''
                SELECT * FROM recommended_products 
                WHERE category = ?
                ORDER BY product_name
            ''', (category,))
        elif related_category:
            c.execute('''
                SELECT * FROM recommended_products 
                WHERE related_category = ?
                ORDER BY category, product_name
            ''', (related_category,))
        else:
            c.execute('SELECT * FROM recommended_products ORDER BY category, product_name')

        products = c.fetchall()
        conn.close()
        return products

    def add_recommended_product(self, product_data):
        """새로운 추천 상품 추가"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO recommended_products 
                (category, product_name, brand, price, description, purchase_link, related_category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_data['category'],
                product_data['product_name'],
                product_data.get('brand'),
                product_data.get('price'),
                product_data.get('description'),
                product_data.get('purchase_link'),
                product_data.get('related_category')
            ))
            product_id = c.lastrowid
            conn.commit()
            return product_id
        except Exception as e:
            print(f"Error adding recommended product: {e}")
            return None
        finally:
            conn.close()

    def create_conversation(self, title, user_id):
        """새로운 대화 세션 생성"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO conversations (title, user_id) VALUES (?, ?)', (title, user_id))
            conversation_id = c.lastrowid
            conn.commit()
            return conversation_id
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
        finally:
            conn.close()

    def save_message(self, conversation_id, role, content):
        """대화 메시지 저장"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO conversation_messages 
                (conversation_id, role, content)
                VALUES (?, ?, ?)
            ''', (conversation_id, role, content))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False
        finally:
            conn.close()

    def get_conversation_messages(self, conversation_id):
        """대화 메시지 조회"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT role, content, created_at 
            FROM conversation_messages 
            WHERE conversation_id = ?
            ORDER BY created_at
        ''', (conversation_id,))
        messages = c.fetchall()
        conn.close()
        return messages
