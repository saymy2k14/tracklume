import sqlite3
import os
from config import NOMINATIONS

class Database:
    def __init__(self, db_path="voting.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        """Создает новое соединение с базой данных"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица номинаций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nominations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Таблица участников
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nomination_id INTEGER,
                    name TEXT NOT NULL,
                    FOREIGN KEY (nomination_id) REFERENCES nominations (id)
                )
            ''')
            
            # Таблица голосов с информацией о пользователях
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    nomination_id INTEGER NOT NULL,
                    participant_id INTEGER NOT NULL,
                    FOREIGN KEY (nomination_id) REFERENCES nominations (id),
                    FOREIGN KEY (participant_id) REFERENCES participants (id),
                    UNIQUE(user_id, nomination_id)
                )
            ''')
            
            # Добавляем номинации по умолчанию
            for nomination in NOMINATIONS:
                cursor.execute('INSERT OR IGNORE INTO nominations (name) VALUES (?)', (nomination,))
            
            conn.commit()
    
    def add_participant(self, nomination_id, name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO participants (nomination_id, name) VALUES (?, ?)',
                (nomination_id, name)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_nominations(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name FROM nominations ORDER BY id')
            return cursor.fetchall()
    
    def get_participants(self, nomination_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, name FROM participants WHERE nomination_id = ? ORDER BY id',
                (nomination_id,)
            )
            return cursor.fetchall()
    
    def add_vote(self, user_id, nomination_id, participant_id, first_name=None, last_name=None, username=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Сначала проверяем, есть ли уже голос от этого пользователя в этой номинации
                cursor.execute(
                    'SELECT id FROM votes WHERE user_id = ? AND nomination_id = ?',
                    (user_id, nomination_id)
                )
                existing_vote = cursor.fetchone()
                
                if existing_vote:
                    # Обновляем существующий голос
                    cursor.execute('''
                        UPDATE votes 
                        SET participant_id = ?, first_name = ?, last_name = ?, username = ?
                        WHERE user_id = ? AND nomination_id = ?
                    ''', (participant_id, first_name, last_name, username, user_id, nomination_id))
                else:
                    # Добавляем новый голос
                    cursor.execute('''
                        INSERT INTO votes 
                        (user_id, nomination_id, participant_id, first_name, last_name, username)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, nomination_id, participant_id, first_name, last_name, username))
                
                conn.commit()
                return True
            except Exception as e:
                print(f"Ошибка при добавлении голоса: {e}")
                return False
    
    def get_vote_results(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT n.name, p.name, COUNT(v.id) as votes
                FROM nominations n
                LEFT JOIN participants p ON n.id = p.nomination_id
                LEFT JOIN votes v ON p.id = v.participant_id
                GROUP BY n.id, p.id
                ORDER BY n.name, votes DESC
            ''')
            return cursor.fetchall()
    
    def delete_participant(self, participant_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM participants WHERE id = ?', (participant_id,))
            cursor.execute('DELETE FROM votes WHERE participant_id = ?', (participant_id,))
            conn.commit()
    
    def get_user_votes(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT n.name, p.name 
                FROM votes v
                JOIN nominations n ON v.nomination_id = n.id
                JOIN participants p ON v.participant_id = p.id
                WHERE v.user_id = ?
            ''', (user_id,))
            return cursor.fetchall()
    
    def get_participant_info(self, participant_id):
        """Получить информацию об участнике по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.name, n.name, n.id
                FROM participants p 
                JOIN nominations n ON p.nomination_id = n.id 
                WHERE p.id = ?
            ''', (participant_id,))
            return cursor.fetchone()
    
    def get_voters_info(self):
        """Получить информацию о всех голосующих"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT v.user_id, n.name as nomination, p.name as participant, 
                       v.first_name, v.last_name, v.username
                FROM votes v
                JOIN nominations n ON v.nomination_id = n.id
                JOIN participants p ON v.participant_id = p.id
                ORDER BY v.user_id, n.name
            ''')
            return cursor.fetchall()
    
    def get_total_votes_count(self):
        """Получить общее количество голосов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM votes')
            return cursor.fetchone()[0]