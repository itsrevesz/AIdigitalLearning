from flask import Flask, request, jsonify
import google.generativeai as genai
from datetime import datetime
import sqlite3
import os
from functools import wraps
import jwt
import hashlib
import uuid
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://127.0.0.1:5500", "http://localhost:5500"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization"]
    }
})

# Konfiguráció
app.config['SECRET_KEY'] = 'titkos_kulcs_ide'  # Éles környezetben változtasd meg!
GOOGLE_API_KEY = "AIzaSyC0rgBqiaSjF-H6iqKAWNDMRqbDO8HtKNg"  # Google API kulcs ide

# Google AI inicializálása
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')


# Adatbázis inicializálása
def init_db():
    conn = sqlite3.connect('quiz_database.db')
    c = conn.cursor()

    # Felhasználók tábla
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, 
                  username TEXT UNIQUE, 
                  password TEXT, 
                  role TEXT)''')

    # Kvízek tábla
    c.execute('''CREATE TABLE IF NOT EXISTS quizzes
                 (id TEXT PRIMARY KEY,
                  teacher_id TEXT,
                  topic TEXT,
                  created_at TEXT,
                  FOREIGN KEY (teacher_id) REFERENCES users(id))''')

    # Kérdések tábla
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id TEXT PRIMARY KEY,
                  quiz_id TEXT,
                  question TEXT,
                  correct_answer TEXT,
                  options TEXT,
                  FOREIGN KEY (quiz_id) REFERENCES quizzes(id))''')

    conn.commit()
    conn.close()


init_db()


# JWT token ellenőrző dekorátor
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token hiányzik!'}), 401

        try:
            data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Érvénytelen token!'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://127.0.0.1:5500')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Regisztráció
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not all(k in data for k in ['username', 'password', 'role']):
        return jsonify({'message': 'Hiányzó adatok!'}), 400

    if data['role'] not in ['teacher', 'student']:
        return jsonify({'message': 'Érvénytelen szerepkör!'}), 400

    hashed_password = hashlib.sha256(data['password'].encode()).hexdigest()
    user_id = str(uuid.uuid4())

    try:
        conn = sqlite3.connect('quiz_database.db')
        c = conn.cursor()
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?)',
                  (user_id, data['username'], hashed_password, data['role']))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Sikeres regisztráció!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'A felhasználónév már foglalt!'}), 400


# Bejelentkezés
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not all(k in data for k in ['username', 'password']):
        return jsonify({'message': 'Hiányzó adatok!'}), 400

    hashed_password = hashlib.sha256(data['password'].encode()).hexdigest()
    expected_role = data.get('expected_role')  # 'teacher' vagy 'student'

    conn = sqlite3.connect('quiz_database.db')
    c = conn.cursor()
    c.execute('SELECT id, role FROM users WHERE username=? AND password=?',
              (data['username'], hashed_password))
    user = c.fetchone()
    conn.close()

    if user and user[1] == expected_role:  # Ellenőrizzük, hogy a megfelelő szerepkörrel rendelkezik-e
        token = jwt.encode({
            'user_id': user[0],
            'role': user[1],
            'exp': datetime.utcnow().timestamp() + 24 * 60 * 60
        }, app.config['SECRET_KEY'])

        return jsonify({
            'token': token,
            'role': user[1]
        })

    return jsonify({'message': 'Hibás bejelentkezési adatok vagy nem megfelelő jogosultság!'}), 401

# Kvíz generálása
@app.route('/generate-quiz', methods=['POST'])
@token_required
def generate_quiz(current_user_id):
    try:
        data = request.get_json()

        if 'topic' not in data:
            return jsonify({'message': 'Hiányzó témakör!'}), 400

        # Prompt módosítása
        prompt = f"""
        Létrehozok egy kvízt erről: {data['topic']}
        Készíts pontosan 5 kérdést az alábbi szigorú formátumban:

        Kérdés: [Egyértelmű, teljes mondatos kérdés]
        A) [Tömör, érthető válaszlehetőség]
        B) [Tömör, érthető válaszlehetőség]
        C) [Tömör, érthető válaszlehetőség]
        D) [Tömör, érthető válaszlehetőség]
        Helyes válasz: [A, B, C vagy D betű]
        ---

        Fontos:
        - Minden kérdésnél pontosan 4 válaszlehetőség legyen
        - Ne használj vesszőt a válaszban
        - Ne használj semmilyen formázást
        - A válaszok legyenek egyértelműek és különbözőek
        - Minden válasz után új sor következzen
        - Minden kérdés után szerepeljen a helyes válasz betűjele
        - Minden kérdés után legyen elválasztó (---)
        """

        response = model.generate_content(prompt)
        quiz_content = response.text
        print("AI válasz:", quiz_content)  # Debug log

        # Kvíz létrehozása
        quiz_id = str(uuid.uuid4())

        # Kérdések feldolgozása
        questions = []
        current_question = None
        options = []

        for line in quiz_content.split('\n'):
            line = line.strip()
            print(f"Feldolgozás alatt: {line}")  # Debug log

            if not line or line == '---':
                if current_question and options:
                    print(f"Kérdés mentése: {current_question}")  # Debug log
                    questions.append(current_question)
                    current_question = None
                    options = []
                continue

            if "Kérdés" in line:
                if current_question and options:
                    questions.append(current_question)
                question_text = line.split("Kérdés:", 1)[1].strip()
                if ":" in question_text:  # Ha van még kettőspont a szövegben
                    question_text = question_text.split(":", 1)[1].strip()
                current_question = {
                    'question': question_text,
                    'options': [],
                    'correct_answer': None
                }
                options = []
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                option = line[3:].strip()
                options.append(option)
                if current_question:
                    current_question['options'] = options
            elif "Helyes válasz:" in line:
                if current_question:
                    answer_letter = line.split("Helyes válasz:", 1)[1].strip()
                    if answer_letter in ['A', 'B', 'C', 'D']:
                        answer_index = ord(answer_letter) - ord('A')
                        if 0 <= answer_index < len(options):
                            current_question['correct_answer'] = options[answer_index]

        # Utolsó kérdés mentése
        if current_question and options:
            questions.append(current_question)

        print(f"Feldolgozott kérdések: {questions}")  # Debug log

        try:
            conn = sqlite3.connect('quiz_database.db')
            c = conn.cursor()

            # Kvíz alapadatok mentése
            c.execute('INSERT INTO quizzes VALUES (?, ?, ?, ?)',
                      (quiz_id, current_user_id, data['topic'],
                       datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            # Kérdések mentése
            for question in questions:
                if not all(k in question for k in ['question', 'options', 'correct_answer']):
                    print(f"Hiányos kérdés adat: {question}")  # Debug log
                    continue

                question_id = str(uuid.uuid4())
                c.execute('INSERT INTO questions VALUES (?, ?, ?, ?, ?)',
                          (question_id, quiz_id, question['question'],
                           question['correct_answer'], ','.join(question['options'])))

            conn.commit()
            conn.close()

            return jsonify({
                'message': 'Kvíz sikeresen létrehozva!',
                'quiz_id': quiz_id,
                'questions': questions
            }), 201

        except sqlite3.Error as e:
            print(f"SQLite hiba: {e}")  # Debug log
            return jsonify({'message': f'Adatbázis hiba: {str(e)}'}), 500

    except Exception as e:
        print(f"Általános hiba: {e}")  # Debug log
        return jsonify({'message': f'Hiba történt: {str(e)}'}), 500

# Kvízek lekérése
@app.route('/quizzes', methods=['GET'])
@token_required
def get_quizzes(current_user_id):
    try:
        conn = sqlite3.connect('quiz_database.db')
        c = conn.cursor()

        # Csak létező kvízeket kérjünk le
        c.execute('''
            SELECT q.id, q.topic, q.created_at 
            FROM quizzes q 
            WHERE EXISTS (
                SELECT 1 
                FROM questions 
                WHERE quiz_id = q.id
            )
            ORDER BY q.created_at DESC
        ''')

        quizzes = [{
            'id': row[0],
            'topic': row[1],
            'created_at': row[2]
        } for row in c.fetchall()]

        conn.close()
        return jsonify(quizzes)

    except Exception as e:
        print(f"Lekérdezési hiba: {str(e)}")
        return jsonify({'message': 'Hiba történt a kvízek lekérésénél'}), 500


# Kvíz lekérése
@app.route('/quiz/<quiz_id>', methods=['GET'])
@token_required
def get_quiz(current_user_id, quiz_id):
    try:
        conn = sqlite3.connect('quiz_database.db')
        c = conn.cursor()
        
        c.execute('''SELECT q.topic, q.created_at 
                     FROM quizzes q 
                     WHERE q.id = ?''', (quiz_id,))
        quiz_data = c.fetchone()

        if not quiz_data:
            conn.close()
            return jsonify({'message': 'A kvíz nem található!'}), 404

        c.execute('''SELECT question, correct_answer, options 
                     FROM questions 
                     WHERE quiz_id = ?''', (quiz_id,))

        questions = []
        for row in c.fetchall():
            questions.append({
                'question': row[0],
                'correct_answer': row[1],
                'options': row[2].split(',') if row[2] else []
            })

        conn.close()
        return jsonify({
            'topic': quiz_data[0],
            'created_at': quiz_data[1],
            'questions': questions
        })

    except Exception as e:
        return jsonify({'message': f'Hiba történt: {str(e)}'}), 500

# Kvíz törlése külön route-ban
@app.route('/delete-quiz/<quiz_id>', methods=['DELETE'])
@token_required
def delete_quiz(current_user_id, quiz_id):
    try:
        conn = sqlite3.connect('quiz_database.db')
        c = conn.cursor()

        # Először töröljük a kérdéseket, függetlenül a kvíz tulajdonosától
        c.execute('DELETE FROM questions WHERE quiz_id = ?', (quiz_id,))
        
        # Aztán töröljük magát a kvízt
        c.execute('DELETE FROM quizzes WHERE id = ?', (quiz_id,))

        conn.commit()
        conn.close()
        return jsonify({'message': 'Kvíz sikeresen törölve!'}), 200

    except Exception as e:
        return jsonify({'message': f'Hiba: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)