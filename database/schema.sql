-- Create Tablespace if needed
-- CREATE TABLESPACE attendance_ts DATAFILE 'attendance.dbf' SIZE 100M;

-- 1. Students Table - Oracle uses VARCHAR2 and CLOB for encoding
CREATE TABLE students (
  student_id VARCHAR2(20) PRIMARY KEY,
  name VARCHAR2(100) NOT NULL,
  dept VARCHAR2(20),
  face_encoding CLOB NOT NULL, -- Stores 128-d JSON encoding
  created_at DATE DEFAULT SYSDATE
);

-- 2. Attendance Logs - Use SEQUENCE + TRIGGER instead of AUTO_INCREMENT
CREATE TABLE attendance_logs (
  log_id NUMBER PRIMARY KEY,
  student_id VARCHAR2(20),
  att_date DATE DEFAULT TRUNC(SYSDATE),
  time_in TIMESTAMP DEFAULT SYSTIMESTAMP,
  status VARCHAR2(20) CHECK (status IN ('PRESENT','SPOOF','REJECTED')),
  confidence NUMBER(5,2),
  liveness_passed NUMBER(1), -- 1=TRUE, 0=FALSE in Oracle
  ip_address VARCHAR2(50),
  CONSTRAINT fk_att_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- 3. Spoof Attempts Table
CREATE TABLE spoof_attempts (
  attempt_id NUMBER PRIMARY KEY,
  student_id VARCHAR2(20),
  attempt_time TIMESTAMP DEFAULT SYSTIMESTAMP,
  attempt_type VARCHAR2(50), -- NO_BLINK, PHOTO_SPOOF, VIDEO_REPLAY
  image_path VARCHAR2(255),
  CONSTRAINT fk_spoof_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE SET NULL
);

-- SEQUENCES for Oracle (replaces MySQL AUTO_INCREMENT)
CREATE SEQUENCE seq_log_id START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_attempt_id START WITH 1 INCREMENT BY 1;

-- TRIGGERS to auto-insert ID
CREATE OR REPLACE TRIGGER trg_attendance_id
BEFORE INSERT ON attendance_logs
FOR EACH ROW
BEGIN
  :NEW.log_id := seq_log_id.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER trg_spoof_id
BEFORE INSERT ON spoof_attempts
FOR EACH ROW
BEGIN
  :NEW.attempt_id := seq_attempt_id.NEXTVAL;
END;
/

-- INDEXES for fast frontend queries
CREATE INDEX idx_att_date ON attendance_logs(att_date);
CREATE INDEX idx_att_student_date ON attendance_logs(student_id, att_date);

COMMIT;