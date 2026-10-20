import os
import base64
import json
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from datetime import datetime

# --- ORACLE IMPORT WITH FALLBACK ---
try:
    import oracledb
    try:
        # If you downloaded instant client, uncomment and set path:
        # oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_20")
        oracledb.init_oracle_client()
        print("Thick mode enabled")
    except:
        print("Running in Thin mode - will use thick if needed for 11g")
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False
    print("oracledb not installed")

app = Flask(__name__)
CORS(app)

# --- DATABASE SETUP: Try Oracle, else use SQLite (so project completes) ---
db_type = "sqlite"
oracle_conn = None

if ORACLE_AVAILABLE:
    for dsn in ["localhost:1521/XE", "localhost:1521/XEPDB1", "127.0.0.1:1521/XE"]:
        try:
            print(f"Trying Oracle {dsn}...")
            oracle_conn = oracledb.connect(user="astha1", password="456", dsn=dsn)
            db_type = "oracle"
            print(f"SUCCESS: Oracle Connected as astha1 on {dsn}!")
            break
        except Exception as e:
            print(f"Oracle failed on {dsn}: {e}")

if db_type == "sqlite":
    print("Using SQLite fallback - Project will still work for demo")
    oracle_conn = sqlite3.connect("attendance.db", check_same_thread=False)

cursor = oracle_conn.cursor()

# Create tables (works for both)
if db_type == "oracle":
    try:
        cursor.execute("CREATE TABLE students (id NUMBER PRIMARY KEY, name VARCHAR2(100), roll VARCHAR2(50) UNIQUE, face_encoding CLOB)")
        cursor.execute("CREATE TABLE attendance (id NUMBER PRIMARY KEY, roll VARCHAR2(50), date_str VARCHAR2(50), time_str VARCHAR2(50))")
        cursor.execute("CREATE SEQUENCE seq_stud START WITH 1")
        cursor.execute("CREATE SEQUENCE seq_att START WITH 1")
        oracle_conn.commit()
    except: pass
else:
    cursor.execute("CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, roll TEXT UNIQUE, face_encoding TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, roll TEXT, date_str TEXT, time_str TEXT)")
    oracle_conn.commit()

# --- FAKE FACE MODE (For Windows) ---
print("FAKE MODE for Windows - face_recognition skipped")

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data['name']
    roll = data['roll']
    # Save dummy encoding, not real face
    enc_str = json.dumps([0.1]*128)

    try:
        if db_type == "oracle":
            sid = cursor.execute("SELECT seq_stud.NEXTVAL FROM DUAL").fetchone()[0]
            cursor.execute("INSERT INTO students (id, name, roll, face_encoding) VALUES (:1, :2, :3, :4)", (sid, name, roll, enc_str))
        else:
            cursor.execute("INSERT INTO students (name, roll, face_encoding) VALUES (?,?,?)", (name, roll, enc_str))
        oracle_conn.commit()
        return jsonify({"msg": f"Student {name} ({roll}) Registered! DB: {db_type}"})
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 400

@app.route('/api/mark', methods=['POST'])
def mark():
    data = request.json
    roll = data.get('roll', 'UNKNOWN')
    # In fake mode, we just mark attendance for given roll
    # If roll not given, pick first student
    if roll == "UNKNOWN":
        cursor.execute("SELECT roll FROM students" if db_type=="sqlite" else "SELECT roll FROM students WHERE ROWNUM=1")
        r = cursor.fetchone()
        if not r: return jsonify({"msg": "No students registered"}), 400
        roll = r[0]

    now = datetime.now()
    d_str = now.strftime("%Y-%m-%d")
    t_str = now.strftime("%H:%M:%S")
    try:
        if db_type == "oracle":
            aid = cursor.execute("SELECT seq_att.NEXTVAL FROM DUAL").fetchone()[0]
            cursor.execute("INSERT INTO attendance (id, roll, date_str, time_str) VALUES (:1, :2, :3, :4)", (aid, roll, d_str, t_str))
        else:
            cursor.execute("INSERT INTO attendance (roll, date_str, time_str) VALUES (?,?,?)", (roll, d_str, t_str))
        oracle_conn.commit()
        return jsonify({"msg": f"Attendance marked for {roll} at {t_str}"})
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 400

@app.route('/api/attendance', methods=['GET'])
def get_att():
    cursor.execute("SELECT roll, date_str, time_str FROM attendance ORDER BY id DESC")
    rows = cursor.fetchall()
    result = [{"roll": r[0], "date": r[1], "time": r[2]} for r in rows]
    return jsonify(result)

@app.route('/')
def home():
    return jsonify({"status": f"Backend running with {db_type}. FAKE MODE ON"})

if __name__ == '__main__':
    print(f"Final DB in use: {db_type}")
    app.run(host='0.0.0.0', port=5000, debug=True)