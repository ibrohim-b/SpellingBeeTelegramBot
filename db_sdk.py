import datetime
import os.path
import sqlite3

from Word import Word

DB_NAME = "words.db"


class DatabaseRepository:
    def __init__(self):
        self.path = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        self.db = sqlite3.connect(os.path.join(self.path, DB_NAME))

    @staticmethod
    def cursor():
        path = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
        return sqlite3.connect(os.path.join(path, DB_NAME)).cursor()

    def get_random_word(self, user_id: str):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("""
                     SELECT w.word, w.translation, w.word_id
                     FROM words w
                     LEFT JOIN suggestions pw
                     ON w.word_id = pw.word_id AND pw.user_id = ?
                     WHERE (pw.passed = 0 OR pw.passed IS NULL)
                     ORDER BY RANDOM() LIMIT 1;
                 """, (user_id,))
            row = cursor.fetchone()
            word = Word(row[2], row[0], row[1])
        cursor.connection.commit()
        cursor.connection.close()
        return word

    def user_exists(self, user_id: int):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("""SELECT * FROM users WHERE user_id = ? ;""", (user_id,))
            row = cursor.fetchone()
            user_exists = row is not None
        cursor.connection.commit()
        cursor.connection.close()
        return user_exists

    def user_has_name(self, user_id: int):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("""SELECT name FROM users WHERE user_id = ? ;""", (user_id,))
            row = cursor.fetchone()
            user_name_exists = row is not None
        cursor.connection.commit()
        cursor.connection.close()
        return user_name_exists

    def create_user(self, user_id: int, name: str):
        cursor = self.cursor()
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with cursor.connection:
            cursor.execute("INSERT OR IGNORE INTO users(user_id, name,created_at) VALUES (?,?,?)",
                           (user_id, name, current_date,))
        cursor.connection.commit()
        cursor.connection.close()

    def have_tried(self, word_id: str, user_id: int):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("SELECT * FROM suggestions WHERE word_id = ? AND user_id = ?",
                           (word_id, user_id))
            row = cursor.fetchone()
            if row:
                return True
            else:
                return False

    def add_suggestion(self, word_id: str, user_id: int):
        cursor = self.cursor()
        with cursor.connection:
            if not self.have_tried(word_id, user_id):
                cursor.execute("INSERT INTO suggestions(word_id, user_id) VALUES (?, ?)",
                               (word_id, user_id))
                cursor.connection.commit()
            cursor.execute("UPDATE suggestions SET num_tries = num_tries + 1 WHERE word_id = ? AND user_id = ?",
                           (word_id, user_id))
        cursor.connection.commit()
        cursor.connection.close()

    def update_suggestion(self, word_id: str, user_id: int, passed: int):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("UPDATE suggestions SET passed = ? WHERE word_id = ? AND user_id = ?",
                           (passed, word_id, user_id))
        cursor.connection.commit()
        cursor.connection.close()

    def get_total_words_passed_count(self, user_id):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("SELECT COUNT(*) FROM suggestions WHERE passed = 1 AND user_id = ?",
                           (user_id,))
            row = cursor.fetchone()
            return row[0]

    def get_total_words_count(self, ):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("SELECT COUNT(*) FROM words")
            row = cursor.fetchone()
            return row[0]

    def update_user_name(self, user_id: int, user_name):
        cursor = self.cursor()
        with cursor.connection:
            cursor.execute("UPDATE users SET name = ? WHERE user_id = ?",
                           (user_name, user_id))


if __name__ == '__main__':
    db_sdk = DatabaseRepository()
    print(db_sdk.user_exists(1380874424))
    print(db_sdk.user_has_name(1380874424))
