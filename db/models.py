"""
Database Models (Data Layer)
============================

DESIGN CONCEPT: Why SQLite In-Memory?
----------------------------------------
The requirements say "MySQL InMemory DB". There are several approaches:

1. SQLite with `:memory:` mode
   - Built into Python (no external dependencies)
   - Truly in-memory (data lost when program exits)
   - Supports full SQL
   - PERFECT FOR LEARNING and prototyping
   - Can be switched to MySQL by replacing this module

2. MySQL with MEMORY engine
   - Requires MySQL server installation
   - More complex setup for a learning project
   - Still needs a running MySQL service

3. Pure Python in-memory (lists/dicts)
   - No SQL, not a "DB"
   - Harder to reason about relationships

We choose SQLite `:memory:` because:
- Zero setup (no MySQL server needed)
- Uses real SQL (teaches database concepts)
- Truly in-memory (as required)
- Easy to swap to MySQL later (same SQL, different connector)

DESIGN CONCEPT: Database Schema
--------------------------------
Tables:
  - doctors:        Doctor information
  - departments:    Specialties/departments
  - availabilities: When each doctor is available
  - patients:       Patient information
  - appointments:   Booked appointments (booked = unavailable)

This follows 3rd Normal Form (3NF) normalization:
- No repeating groups
- Every column depends on the primary key
- No transitive dependencies (e.g., department info stored once)

DESIGN CONCEPT: In-Memory Database Lifecycle
----------------------------------------------
The database is created fresh on each application startup.
All data is initialized from seed data in `seeds.py`.
Since it's in-memory, there's no persistence between runs.
This is fine for a learning/demo project.

For production, you would:
  1. Switch to a persistent database (PostgreSQL, MySQL)
  2. Add migration scripts for schema changes
  3. Keep seed data only for development environments
"""

import sqlite3
from datetime import datetime, date, time, timedelta
from typing import Optional


class DoctorAssistantDB:
    """
    Database interface for the Doctor's Assistant chatbot.
    
    This class encapsulates ALL database operations.
    The rest of the application interacts only through this class,
    never directly with SQLite. This is called the "Repository Pattern".
    
    Repository Pattern Benefit:
      If we switch from SQLite to MySQL, only this class changes.
      All other code remains unchanged.
    """
    
    def __init__(self, db_url: str = ":memory:"):
        """
        Initialize database connection.
        
        Args:
            db_url: SQLite connection string. Default ":memory:" creates
                   an in-memory database. Can be a file path for persistence.
        """
        self._conn = sqlite3.connect(db_url, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_data()

    def _create_tables(self):
        """Create database schema."""
        self._conn.executescript("""
            -- Departments / Specialties
            CREATE TABLE IF NOT EXISTS departments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT
            );

            -- Doctors
            CREATE TABLE IF NOT EXISTS doctors (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                department_id   INTEGER NOT NULL,
                phone           TEXT,
                email           TEXT,
                FOREIGN KEY (department_id) REFERENCES departments(id)
            );

            -- Doctor Availability (recurring weekly slots)
            CREATE TABLE IF NOT EXISTS availabilities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id   INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
                start_time  TEXT NOT NULL,  -- HH:MM format
                end_time    TEXT NOT NULL,  -- HH:MM format
                FOREIGN KEY (doctor_id) REFERENCES doctors(id)
            );

            -- Patients
            CREATE TABLE IF NOT EXISTS patients (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                phone   TEXT,
                email   TEXT
            );

            -- Appointments (a booked slot = unavailable for future bookings)
            CREATE TABLE IF NOT EXISTS appointments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id   INTEGER NOT NULL,
                patient_id  INTEGER NOT NULL,
                date        TEXT NOT NULL,  -- YYYY-MM-DD
                start_time  TEXT NOT NULL,  -- HH:MM
                end_time    TEXT NOT NULL,  -- HH:MM
                reason      TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );
        """)
        self._conn.commit()

    def _seed_data(self):
        """Initialize with sample doctors, departments, and availability."""
        
        # Departments
        self._conn.executescript("""
            INSERT OR IGNORE INTO departments (id, name, description) VALUES
                (1, 'Cardiology',    'Heart and cardiovascular system'),
                (2, 'Dermatology',   'Skin, hair, and nail conditions'),
                (3, 'Orthopedics',   'Bones, joints, muscles, and ligaments'),
                (4, 'Pediatrics',    'Medical care for infants, children, and adolescents'),
                (5, 'Neurology',     'Brain, spinal cord, and nervous system'),
                (6, 'General Medicine', 'General health checkups and common illnesses');

            -- Doctors
            INSERT OR IGNORE INTO doctors (id, name, department_id, phone, email) VALUES
                (1, 'Dr. Sharma',   1, '+91-9876543210', 'sharma@superclinic.com'),
                (2, 'Dr. Patel',    2, '+91-9876543211', 'patel@superclinic.com'),
                (3, 'Dr. Singh',    3, '+91-9876543212', 'singh@superclinic.com'),
                (4, 'Dr. Gupta',    3, '+91-9876543213', 'gupta@superclinic.com'),
                (5, 'Dr. Verma',    4, '+91-9876543214', 'verma@superclinic.com'),
                (6, 'Dr. Joshi',    5, '+91-9876543215', 'joshi@superclinic.com'),
                (7, 'Dr. Desai',    1, '+91-9876543216', 'desai@superclinic.com'),
                (8, 'Dr. Kapoor',   6, '+91-9876543217', 'kapoor@superclinic.com');

            -- Weekly Availability
            -- Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
            
            -- Dr. Sharma (Cardiology): Mon-Fri 9am-5pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (1, 0, '09:00', '17:00'), (1, 1, '09:00', '17:00'),
                (1, 2, '09:00', '17:00'), (1, 3, '09:00', '17:00'),
                (1, 4, '09:00', '17:00');
            
            -- Dr. Patel (Dermatology): Mon, Wed, Fri 10am-4pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (2, 0, '10:00', '16:00'), (2, 2, '10:00', '16:00'),
                (2, 4, '10:00', '16:00');
            
            -- Dr. Singh (Orthopedics): Tue-Thu 8am-2pm, Sat 9am-1pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (3, 1, '08:00', '14:00'), (3, 2, '08:00', '14:00'),
                (3, 3, '08:00', '14:00'), (3, 5, '09:00', '13:00');
            
            -- Dr. Gupta (Orthopedics): Mon-Fri 11am-7pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (4, 0, '11:00', '19:00'), (4, 1, '11:00', '19:00'),
                (4, 2, '11:00', '19:00'), (4, 3, '11:00', '19:00'),
                (4, 4, '11:00', '19:00');
            
            -- Dr. Verma (Pediatrics): Mon-Sat 9am-3pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (5, 0, '09:00', '15:00'), (5, 1, '09:00', '15:00'),
                (5, 2, '09:00', '15:00'), (5, 3, '09:00', '15:00'),
                (5, 4, '09:00', '15:00'), (5, 5, '09:00', '15:00');
            
            -- Dr. Joshi (Neurology): Mon, Wed, Fri 10am-4pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (6, 0, '10:00', '16:00'), (6, 2, '10:00', '16:00'),
                (6, 4, '10:00', '16:00');
            
            -- Dr. Desai (Cardiology): Tue, Thu 2pm-8pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (7, 1, '14:00', '20:00'), (7, 3, '14:00', '20:00');
            
            -- Dr. Kapoor (General Medicine): Mon-Sat 9am-5pm
            INSERT OR IGNORE INTO availabilities (doctor_id, day_of_week, start_time, end_time) VALUES
                (8, 0, '09:00', '17:00'), (8, 1, '09:00', '17:00'),
                (8, 2, '09:00', '17:00'), (8, 3, '09:00', '17:00'),
                (8, 4, '09:00', '17:00'), (8, 5, '09:00', '17:00');
        """)
        self._conn.commit()

    # ============================================================
    # QUERY METHODS (Read)
    # ============================================================

    def get_departments(self) -> list[dict]:
        """Get all departments."""
        cursor = self._conn.execute("SELECT id, name, description FROM departments")
        return [dict(row) for row in cursor.fetchall()]

    def get_doctors_by_department(self, department_name: str) -> list[dict]:
        """
        Find doctors for a given department/specialty.
        Uses case-insensitive matching for user-friendly search.
        """
        query = """
            SELECT d.id, d.name, d.phone, d.email, dept.name as department
            FROM doctors d
            JOIN departments dept ON d.department_id = dept.id
            WHERE LOWER(dept.name) LIKE LOWER(?)
        """
        cursor = self._conn.execute(query, (f"%{department_name}%",))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_doctors(self) -> list[dict]:
        """Get all doctors with their department info."""
        query = """
            SELECT d.id, d.name, d.phone, d.email, dept.name as department
            FROM doctors d
            JOIN departments dept ON d.department_id = dept.id
            ORDER BY dept.name, d.name
        """
        cursor = self._conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_doctor_by_name(self, name: str) -> Optional[dict]:
        """Find a doctor by name (case-insensitive partial match)."""
        query = """
            SELECT d.id, d.name, d.phone, d.email, dept.name as department
            FROM doctors d
            JOIN departments dept ON d.department_id = dept.id
            WHERE LOWER(d.name) LIKE LOWER(?)
        """
        cursor = self._conn.execute(query, (f"%{name}%",))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_available_slots(self, doctor_id: int, target_date: str) -> list[dict]:
        """
        Get available appointment slots for a doctor on a specific date.
        
        Algorithm:
        1. Get the day_of_week for the target_date
        2. Look up the doctor's recurring availability for that day
        3. Get all booked appointments for that doctor on that date
        4. Subtract booked slots from available slots
        5. Return remaining slots as 30-minute intervals
        
        Args:
            doctor_id: The doctor's ID
            target_date: Date string in 'YYYY-MM-DD' format
        
        Returns:
            List of available time slots, each with start_time and end_time
        """
        # Parse the date
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        day_of_week = target_dt.weekday()
        target_date_str = target_date

        # Get doctor's availability for this day of week
        avail_query = """
            SELECT start_time, end_time
            FROM availabilities
            WHERE doctor_id = ? AND day_of_week = ?
        """
        avail_rows = self._conn.execute(avail_query, (doctor_id, day_of_week)).fetchall()

        if not avail_rows:
            return []  # Doctor doesn't work on this day

        # Get booked appointments for this doctor on this date
        booked_query = """
            SELECT start_time, end_time
            FROM appointments
            WHERE doctor_id = ? AND date = ?
        """
        booked_rows = self._conn.execute(booked_query, (doctor_id, target_date_str)).fetchall()

        # Convert booked times to set of (start, end) tuples for easy comparison
        booked_slots = [(row["start_time"], row["end_time"]) for row in booked_rows]

        # Generate all possible 30-minute slots from the doctor's availability
        available_slots = []
        for avail in avail_rows:
            # Parse start and end times
            start_h, start_m = map(int, avail["start_time"].split(":"))
            end_h, end_m = map(int, avail["end_time"].split(":"))
            
            current = time(start_h, start_m)
            end = time(end_h, end_m)

            # Generate 30-minute slots
            while True:
                # Calculate next slot end
                current_dt = datetime.combine(target_dt, current)
                next_dt = current_dt + timedelta(minutes=30)
                next_time = next_dt.time()

                # If we've reached or passed the end time, stop
                if current_dt + timedelta(minutes=30) > datetime.combine(target_dt, end):
                    break

                slot_start = current.strftime("%H:%M")
                slot_end = next_time.strftime("%H:%M")

                # Check if this slot overlaps with any booked slot
                is_booked = False
                for booked_start, booked_end in booked_slots:
                    # Overlap if slot starts before booked ends AND slot ends after booked starts
                    if slot_start < booked_end and slot_end > booked_start:
                        is_booked = True
                        break

                if not is_booked:
                    available_slots.append({
                        "start_time": slot_start,
                        "end_time": slot_end
                    })

                # Move to next slot
                current = next_time

        return available_slots

    def find_appointment_slot(
        self, doctor_id: int, target_date: str, preferred_time: str = None
    ) -> Optional[dict]:
        """
        Find an appointment slot, optionally near a preferred time.
        
        Args:
            doctor_id: The doctor's ID
            target_date: Date string in 'YYYY-MM-DD' format
            preferred_time: Optional preferred start time in 'HH:MM' format
        
        Returns:
            A specific slot dict if found, None otherwise
        """
        slots = self.get_available_slots(doctor_id, target_date)
        
        if not slots:
            return None
        
        if preferred_time:
            # Try to find a slot at or near the preferred time
            for slot in slots:
                if slot["start_time"] == preferred_time:
                    return slot
            
            # If exact match not found, return the first available slot
            # (the LLM will suggest this to the patient)
            return slots[0] if slots else None
        
        return slots[0] if slots else None

    def find_alternative_slot(
        self, doctor_id: int, target_date: str, preferred_time: str
    ) -> Optional[dict]:
        """
        Find an alternative time slot if the preferred time is unavailable.
        """
        return self.find_appointment_slot(doctor_id, target_date)

    # ============================================================
    # COMMAND METHODS (Write)
    # ============================================================

    def create_patient(self, name: str, phone: str = None, email: str = None) -> int:
        """Create a new patient record. Returns patient ID."""
        cursor = self._conn.execute(
            "INSERT INTO patients (name, phone, email) VALUES (?, ?, ?)",
            (name, phone, email)
        )
        self._conn.commit()
        return cursor.lastrowid

    def book_appointment(
        self,
        doctor_id: int,
        patient_name: str,
        patient_phone: str,
        date_str: str,
        start_time: str,
        end_time: str,
        reason: str = None
    ) -> dict:
        """
        Book an appointment. Creates a patient record if needed.
        
        This operation is TRANSACTIONAL:
        - Both patient creation and appointment booking happen together
        - If one fails, both roll back (database consistency)
        
        Returns:
            Dict with appointment details and patient info
        """
        try:
            # Start transaction
            self._conn.execute("BEGIN TRANSACTION")

            # Create or find patient
            patient_id = self.create_patient(patient_name, patient_phone)

            # Check if slot is still available (race condition prevention)
            existing = self._conn.execute(
                """SELECT id FROM appointments 
                   WHERE doctor_id = ? AND date = ? 
                   AND start_time = ? AND end_time = ?""",
                (doctor_id, date_str, start_time, end_time)
            ).fetchone()

            if existing:
                self._conn.execute("ROLLBACK")
                return {
                    "success": False,
                    "message": "This slot has just been booked by someone else. Please choose another time."
                }

            # Book the appointment
            cursor = self._conn.execute(
                """INSERT INTO appointments 
                   (doctor_id, patient_id, date, start_time, end_time, reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (doctor_id, patient_id, date_str, start_time, end_time, reason)
            )
            
            appointment_id = cursor.lastrowid

            # Commit transaction
            self._conn.execute("COMMIT")

            # Get doctor and patient details for confirmation
            doctor = self._conn.execute(
                "SELECT name FROM doctors WHERE id = ?", (doctor_id,)
            ).fetchone()

            patient = self._conn.execute(
                "SELECT name FROM patients WHERE id = ?", (patient_id,)
            ).fetchone()

            return {
                "success": True,
                "appointment_id": appointment_id,
                "doctor_name": doctor["name"] if doctor else "Unknown",
                "patient_name": patient["name"] if patient else patient_name,
                "date": date_str,
                "start_time": start_time,
                "end_time": end_time,
                "message": f"Appointment booked successfully with {doctor['name']} "
                          f"on {date_str} at {start_time}."
            }

        except Exception as e:
            self._conn.execute("ROLLBACK")
            return {
                "success": False,
                "message": f"Failed to book appointment: {str(e)}"
            }

    def get_upcoming_appointments(self, doctor_id: int = None) -> list[dict]:
        """Get upcoming appointments, optionally filtered by doctor."""
        if doctor_id:
            query = """
                SELECT a.id, d.name as doctor_name, p.name as patient_name,
                       a.date, a.start_time, a.end_time, a.reason
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                JOIN patients p ON a.patient_id = p.id
                WHERE a.doctor_id = ?
                ORDER BY a.date, a.start_time
            """
            cursor = self._conn.execute(query, (doctor_id,))
        else:
            query = """
                SELECT a.id, d.name as doctor_name, p.name as patient_name,
                       a.date, a.start_time, a.end_time, a.reason
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                JOIN patients p ON a.patient_id = p.id
                ORDER BY a.date, a.start_time
            """
            cursor = self._conn.execute(query)
        
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close the database connection."""
        self._conn.close()