#!/usr/bin/env python
"""
Rich demo data seed script for Beru Campus AI.

Creates realistic data for all three personas:
- Student: courses, grades, attendance, predictions, alerts
- Faculty: courses taught, at-risk students, interventions
- Placement: companies, JDs, drives, selections, analytics

Usage:
    python -m scripts.seed_demo
    # or from backend dir: python scripts/seed_demo.py
"""

import random
from datetime import date, datetime, time, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.models.entities import (
    Announcement,
    AttendanceRecord,
    CampusResource,
    Company,
    Course,
    Enrollment,
    InterventionPlan,
    JobDescription,
    Lecturer,
    PlacementDrive,
    PlacementNotification,
    PlacementSelection,
    RecruitmentRound,
    Result,
    Room,
    Student,
    TimetableEntry,
    User,
)


# ============================================================
# CONFIGURATION
# ============================================================

SEMESTER = "2026-S1"
DEPARTMENTS = [
    "Computer Science",
    "Electronics & Communication",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Information Technology",
    "AI & Data Science",
]

COURSE_CATALOG = [
    # CS Core
    ("CS101", "Programming Fundamentals", 3, "Computer Science", []),
    ("CS102", "Data Structures", 3, "Computer Science", ["CS101"]),
    ("CS201", "Algorithms", 4, "Computer Science", ["CS102"]),
    ("CS202", "Database Systems", 3, "Computer Science", ["CS101"]),
    ("CS203", "Operating Systems", 4, "Computer Science", ["CS101"]),
    ("CS301", "Computer Networks", 3, "Computer Science", ["CS203"]),
    ("CS302", "Software Engineering", 4, "Computer Science", ["CS201"]),
    ("CS303", "Machine Learning", 4, "Computer Science", ["CS201", "MA201"]),
    ("CS401", "Distributed Systems", 4, "Computer Science", ["CS301"]),
    ("CS402", "Capstone Project", 6, "Computer Science", ["CS302"]),
    # AI&DS Specific
    ("AD101", "Introduction to AI", 3, "AI & Data Science", []),
    ("AD201", "Statistical Learning", 4, "AI & Data Science", ["MA201"]),
    ("AD202", "Deep Learning", 4, "AI & Data Science", ["AD201"]),
    ("AD301", "NLP", 3, "AI & Data Science", ["AD202"]),
    ("AD302", "Computer Vision", 3, "AI & Data Science", ["AD202"]),
    ("AD401", "MLOps", 3, "AI & Data Science", ["AD301", "AD302"]),
    # Math
    ("MA101", "Calculus I", 4, "Mathematics", []),
    ("MA102", "Linear Algebra", 3, "Mathematics", []),
    ("MA201", "Probability & Statistics", 4, "Mathematics", ["MA101"]),
    ("MA202", "Optimization", 3, "Mathematics", ["MA201"]),
    # Electronics
    ("EC101", "Basic Electronics", 3, "Electronics & Communication", []),
    ("EC201", "Digital Logic Design", 4, "Electronics & Communication", ["EC101"]),
    ("EC301", "Microprocessors", 4, "Electronics & Communication", ["EC201"]),
]

STUDENT_NAMES = [
    ("STU2024001", "Arjun Kumar", 3.8, 2),
    ("STU2024002", "Priya Sharma", 3.6, 2),
    ("STU2024003", "Rahul Singh", 2.9, 2),
    ("STU2024004", "Anjali Patel", 3.4, 3),
    ("STU2024005", "Vikram Reddy", 2.2, 2),
    ("STU2024006", "Sneha Gupta", 3.9, 3),
    ("STU2024007", "Karan Mehta", 2.5, 1),
    ("STU2024008", "Divya Nair", 3.2, 2),
    ("STU2024009", "Amit Joshi", 1.8, 2),
    ("STU2024010", "Riya Agarwal", 3.7, 3),
    ("STU2024011", "Siddharth Rao", 2.8, 1),
    ("STU2024012", "Meera Iyer", 3.5, 2),
    ("STU2024013", "Nikhil Desai", 2.1, 1),
    ("STU2024014", "Pooja Malhotra", 3.3, 3),
    ("STU2024015", "Aditya Verma", 2.6, 2),
    ("STU2024016", "Kavya Krishnan", 3.1, 2),
    ("STU2024017", "Rohit Bansal", 2.3, 1),
    ("STU2024018", "Ishita Kapoor", 3.8, 3),
    ("STU2024019", "Varun Saxena", 2.7, 2),
    ("STU2024020", "Tanya Choudhary", 3.4, 2),
]

LECTURER_NAMES = [
    ("LEC001", "Dr. S. Rajagopalan", "Computer Science"),
    ("LEC002", "Prof. Meera Subramanian", "Computer Science"),
    ("LEC003", "Dr. A. Venkatesh", "AI & Data Science"),
    ("LEC004", "Prof. Lakshmi Narayanan", "Mathematics"),
    ("LEC005", "Dr. R. Krishnamurthy", "Electronics & Communication"),
    ("LEC006", "Prof. S. Ganesh", "Electrical Engineering"),
]

COMPANIES = [
    ("TechCorp Solutions", "Technology", "Bangalore", "hr@techcorp.com", "+91-80-12345678"),
    ("DataMind Analytics", "Data Science", "Hyderabad", "careers@datamind.ai", "+91-40-87654321"),
    ("CloudScale Systems", "Cloud Computing", "Pune", "jobs@cloudscale.io", "+91-20-11223344"),
    ("FinTech Innovations", "FinTech", "Mumbai", "hiring@fintech.in", "+91-22-99887766"),
    ("HealthTech India", "Healthcare Tech", "Chennai", "talent@healthtech.co.in", "+91-44-55667788"),
    ("AutoTech Motors", "Automotive", "Chennai", "recruit@autotech.com", "+91-44-33445566"),
    ("Edutech Global", "EdTech", "Delhi", "jobs@edutechglobal.com", "+91-11-77889900"),
    ("CyberSecure Ltd", "Cybersecurity", "Bangalore", "careers@cybersecure.in", "+91-80-22334455"),
]

JOB_ROLES = [
    ("Software Engineer", "software", ["Python", "Java", "SQL", "Git", "REST APIs"], 7.0, 12.0),
    ("Data Scientist", "data_science", ["Python", "ML", "Statistics", "SQL", "Tableau"], 8.0, 15.0),
    ("ML Engineer", "ml_engineering", ["Python", "PyTorch", "TensorFlow", "MLOps", "Docker"], 9.0, 18.0),
    ("Backend Developer", "software", ["Java", "Spring Boot", "PostgreSQL", "Kafka", "AWS"], 7.5, 14.0),
    ("Full Stack Developer", "software", ["React", "Node.js", "MongoDB", "TypeScript", "GraphQL"], 6.5, 13.0),
    ("DevOps Engineer", "devops", ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD"], 8.0, 16.0),
    ("AI Research Intern", "research", ["Python", "PyTorch", "Research", "NLP", "CV"], 5.0, 8.0),
    ("Cybersecurity Analyst", "security", ["Network Security", "SIEM", "Pen Testing", "Python", "Compliance"], 6.0, 12.0),
]

ROOMS = [
    ("CS-LAB-1", 60, "lab"),
    ("CS-LAB-2", 60, "lab"),
    ("CS-LAB-3", 40, "lab"),
    ("LECTURE-HALL-A", 120, "classroom"),
    ("LECTURE-HALL-B", 120, "classroom"),
    ("LECTURE-HALL-C", 80, "classroom"),
    ("SEMINAR-1", 30, "seminar"),
    ("SEMINAR-2", 30, "seminar"),
    ("AI-LAB-1", 40, "lab"),
    ("AI-LAB-2", 40, "lab"),
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance, True


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_time(start_hour: int, end_hour: int) -> time:
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.choice([0, 30])
    return time(hour, minute)


# ============================================================
# SEEDING FUNCTIONS
# ============================================================

def seed_users_and_roles(db):
    """Create demo users for all roles."""
    print("🔐 Seeding users and roles...")
    
    # Admin
    get_or_create(db, User, {
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "email": "admin@beru.edu",
    }, username="admin")
    
    # Default demo users (match config.py)
    demo_users = [
        ("student", "student123", "student", "student@beru.edu"),
        ("lecturer", "lecturer123", "lecturer", "lecturer@beru.edu"),
        ("placement", "placement123", "placement", "placement@beru.edu"),
    ]
    for username, password, role, email in demo_users:
        get_or_create(db, User, {
            "password_hash": hash_password(password),
            "role": role,
            "email": email,
        }, username=username)
    
    # Student users
    for student_id, name, gpa, year in STUDENT_NAMES:
        email = f"{student_id.lower()}@beru.edu"
        user, _ = get_or_create(db, User, {
            "password_hash": hash_password("student123"),
            "role": "student",
            "email": email,
        }, username=student_id)
        
        get_or_create(db, Student, {
            "user_id": user.id,
            "student_id": student_id,
            "year": year,
            "program": "B.Tech Computer Science" if year <= 2 else "B.Tech AI & Data Science",
            "gpa": gpa,
        }, student_id=student_id)
    
    # Lecturer users
    for staff_id, name, dept in LECTURER_NAMES:
        email = f"{staff_id.lower()}@beru.edu"
        user, _ = get_or_create(db, User, {
            "password_hash": hash_password("lecturer123"),
            "role": "lecturer",
            "email": email,
        }, username=staff_id)
        
        get_or_create(db, Lecturer, {
            "user_id": user.id,
            "staff_id": staff_id,
            "department": dept,
            "max_hours": 20,
        }, staff_id=staff_id)
    
    # Placement officer
    user, _ = get_or_create(db, User, {
        "password_hash": hash_password("placement123"),
        "role": "placement",
        "email": "placement.officer@beru.edu",
    }, username="placement_officer")
    
    db.commit()
    print("✅ Users and roles seeded")


def seed_courses(db):
    """Create course catalog."""
    print("📚 Seeding courses...")
    
    for code, title, credits, dept, prereqs in COURSE_CATALOG:
        get_or_create(db, Course, {
            "title": title,
            "credits": credits,
            "capacity": 60,
            "department": dept,
            "prerequisites": prereqs,
        }, code=code)
    
    db.commit()
    print("✅ Courses seeded")


def seed_rooms(db):
    """Create rooms."""
    print("🏫 Seeding rooms...")
    
    for room_no, capacity, kind in ROOMS:
        get_or_create(db, Room, {
            "capacity": capacity,
            "kind": kind,
        }, room_no=room_no)
    
    db.commit()
    print("✅ Rooms seeded")


def seed_enrollments_and_grades(db):
    """Enroll students in courses with realistic grades and attendance."""
    print("📝 Seeding enrollments, grades, and attendance...")
    
    students_list = db.execute(select(Student)).scalars().all()
    courses_list = db.execute(select(Course)).scalars().all()
    
    # Define course progression by year
    year_courses = {
        1: ["CS101", "MA101", "EC101", "CS102", "MA102"],
        2: ["CS201", "CS202", "CS203", "MA201", "AD101", "EC201"],
        3: ["CS301", "CS302", "CS303", "AD201", "AD202", "EC301", "MA202"],
        4: ["CS401", "CS402", "AD301", "AD302", "AD401"],
    }
    
    course_map = {c.code: c for c in courses_list}
    
    for student in students_list:
        # Get courses for student's year + some from previous years
        eligible_codes = []
        for y in range(1, student.year + 1):
            eligible_codes.extend(year_courses.get(y, []))
        
        # Enroll in 5-7 courses
        num_courses = random.randint(5, min(7, len(eligible_codes)))
        enrolled_codes = random.sample(eligible_codes, num_courses)
        
        for code in enrolled_codes:
            course = course_map.get(code)
            if not course:
                continue
            
            # Check prerequisites
            prereqs = course.prerequisites or []
            passed_codes = set()
            for e in student.enrollments:
                if e.result and e.result.grade not in ("", "F"):
                    passed_codes.add(e.course.code)
            
            if not all(p in passed_codes for p in prereqs):
                continue  # Skip if prereqs not met
            
            enrollment, created = get_or_create(db, Enrollment, {
                "student_id": student.id,
                "course_id": course.id,
                "status": "approved",
            }, student_id=student.id, course_id=course.id)
            
            if not created:
                continue
            
            # Generate realistic performance based on student GPA
            base_performance = student.gpa / 4.0  # 0.0 to 1.0
            noise = random.uniform(-0.15, 0.15)
            performance = max(0.1, min(1.0, base_performance + noise))
            
            # Grade determination
            if performance >= 0.9:
                grade, marks = "A", round(90 + random.uniform(0, 10), 1)
            elif performance >= 0.8:
                grade, marks = "B", round(80 + random.uniform(0, 10), 1)
            elif performance >= 0.7:
                grade, marks = "C", round(70 + random.uniform(0, 10), 1)
            elif performance >= 0.6:
                grade, marks = "D", round(60 + random.uniform(0, 10), 1)
            elif performance >= 0.5:
                grade, marks = "E", round(50 + random.uniform(0, 10), 1)
            else:
                grade, marks = "F", round(20 + random.uniform(0, 30), 1)
            
            # Attendance correlated with performance
            attendance_rate = max(0.3, min(1.0, performance + random.uniform(-0.1, 0.2)))
            
            db.add(Result(
                enrollment_id=enrollment.id,
                marks=marks,
                grade=grade,
                semester=SEMESTER,
            ))
            
            # Attendance records (20 sessions)
            for i in range(20):
                session_date = date(2026, 2, 1) + timedelta(days=i * 3)
                status = "present" if random.random() < attendance_rate else "absent"
                db.add(AttendanceRecord(
                    enrollment_id=enrollment.id,
                    day=session_date,
                    status=status,
                ))
    
    db.commit()
    print("✅ Enrollments, grades, and attendance seeded")


def seed_timetable(db):
    """Create timetable entries."""
    print("📅 Seeding timetable...")
    
    courses_list = db.execute(select(Course)).scalars().all()
    lecturers_list = db.execute(select(Lecturer)).scalars().all()
    rooms_list = db.execute(select(Room)).scalars().all()
    
    lecturer_map = {l.department: l for l in lecturers_list}
    lab_rooms = [r for r in rooms_list if r.kind == "lab"]
    lecture_rooms = [r for r in rooms_list if r.kind == "classroom"]
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    for course in courses_list:
        lecturer = lecturer_map.get(course.department)
        if not lecturer:
            continue
        
        room_pool = lab_rooms if "LAB" in course.code or course.credits >= 4 else lecture_rooms
        if not room_pool:
            continue
        
        room = random.choice(room_pool)
        
        # 2-3 sessions per week
        num_sessions = random.randint(2, 3)
        selected_days = random.sample(days, num_sessions)
        
        for day in selected_days:
            start = random_time(8, 14)
            end_hour = start.hour + course.credits
            end = time(min(end_hour, 18), start.minute)
            
            get_or_create(db, TimetableEntry, {
                "course_id": course.id,
                "room_id": room.id,
                "lecturer_id": lecturer.id,
                "day": day,
                "start_time": start,
                "end_time": end,
                "term": SEMESTER,
            }, course_id=course.id, room_id=room.id, lecturer_id=lecturer.id, day=day)
    
    db.commit()
    print("✅ Timetable seeded")


def seed_placement(db):
    """Create placement data: companies, JDs, drives, selections."""
    print("💼 Seeding placement data...")
    
    students_list = db.execute(select(Student)).scalars().all()
    
    # Companies
    company_objects = []
    for name, sector, location, email, phone in COMPANIES:
        company, _ = get_or_create(db, Company, {
            "sector": sector,
            "location": location,
            "contact_email": email,
            "contact_phone": phone,
            "notes": f"Partner since {random.randint(2020, 2024)}",
        }, name=name)
        company_objects.append(company)
    
    # Job Descriptions
    jd_objects = []
    for company in company_objects:
        num_jds = random.randint(1, 3)
        for _ in range(num_jds):
            title, role_type, skills, ctc_min, ctc_max = random.choice(JOB_ROLES)
            jd, _ = get_or_create(db, JobDescription, {
                "company_id": company.id,
                "title": f"{title} - {company.name}",
                "raw_text": f"We are looking for a {title} with expertise in {', '.join(skills)}...",
                "skills": skills,
                "role_type": role_type,
                "min_gpa": round(random.uniform(6.0, 8.0), 1),
                "max_backlogs": random.randint(0, 2),
                "year_required": random.choice([3, 4]),
                "ctc_min": ctc_min,
                "ctc_max": ctc_max,
                "openings": random.randint(2, 8),
                "location": company.location,
                "mode": random.choice(["online", "offline", "hybrid"]),
                "status": "open",
            }, company_id=company.id, title=f"{title} - {company.name}")
            jd_objects.append(jd)
    
    # Drives
    drive_objects = []
    for jd in jd_objects:
        if random.random() < 0.7:  # 70% of JDs get a drive
            drive_date = date(2026, random.randint(8, 12), random.randint(1, 28))
            drive, _ = get_or_create(db, PlacementDrive, {
                "company_id": jd.company_id,
                "jd_id": jd.id,
                "title": f"{jd.company.name} Campus Drive - {drive_date.strftime('%b %Y')}",
                "drive_date": drive_date,
                "mode": jd.mode,
                "location": jd.location,
                "status": random.choice(["scheduled", "ongoing", "completed"]),
            }, title=f"{jd.company.name} Campus Drive - {drive_date.strftime('%b %Y')}")
            drive_objects.append(drive)
            
            # Rounds
            round_names = ["Online Test", "Technical Interview", "HR Interview"]
            for i, round_name in enumerate(round_names):
                round_date = drive_date + timedelta(days=random.randint(1, 14))
                get_or_create(db, RecruitmentRound, {
                    "drive_id": drive.id,
                    "name": round_name,
                    "round_order": i + 1,
                    "round_date": round_date,
                    "status": "scheduled",
                }, drive_id=drive.id, name=round_name)
            
            # Notifications to eligible students
            eligible_students = [s for s in students_list 
                               if s.gpa >= jd.min_gpa and s.year >= jd.year_required]
            for student in random.sample(eligible_students, min(len(eligible_students), jd.openings * 2)):
                get_or_create(db, PlacementNotification, {
                    "drive_id": drive.id,
                    "student_id": student.id,
                    "title": f"Campus Drive: {drive.title}",
                    "body": f"You are invited to participate in {drive.title}. Register by {drive_date - timedelta(days=7)}.",
                    "status": "sent",
                }, drive_id=drive.id, student_id=student.id)
            
            # Selections for completed drives
            if drive.status == "completed":
                num_selected = random.randint(1, min(jd.openings, len(eligible_students)))
                for student in random.sample(eligible_students, num_selected):
                    rounds = ["Online Test", "Technical Interview", "HR Interview"]
                    round_reached = random.choice(rounds)
                    offered = round_reached == "HR Interview"
                    
                    get_or_create(db, PlacementSelection, {
                        "drive_id": drive.id,
                        "student_id": student.id,
                        "round_reached": round_reached,
                        "offered_ctc": round(random.uniform(jd.ctc_min, jd.ctc_max), 2) if offered else 0.0,
                        "offer_status": "offered" if offered else "rejected",
                        "decided_at": datetime.now() if offered else None,
                    }, drive_id=drive.id, student_id=student.id)
    
    db.commit()
    print("✅ Placement data seeded")


def seed_interventions(db):
    """Create intervention plans for at-risk students."""
    print("🎯 Seeding interventions...")
    
    students_list = db.execute(select(Student)).scalars().all()
    lecturers_list = db.execute(select(Lecturer)).scalars().all()
    courses_list = db.execute(select(Course)).scalars().all()
    
    # Find at-risk students (low GPA, failed courses)
    at_risk = []
    for student in students_list:
        failed_courses = []
        for enrollment in student.enrollments:
            if enrollment.result and enrollment.result.grade == "F":
                failed_courses.append(enrollment.course.code)
        
        if student.gpa < 2.5 or failed_courses:
            at_risk.append((student, failed_courses))
    
    for student, failed_codes in at_risk[:10]:  # Top 10 at-risk
        lecturer = random.choice(lecturers_list)
        course_code = random.choice(failed_codes) if failed_codes else random.choice([c.code for c in courses_list])
        
        get_or_create(db, InterventionPlan, {
            "student_id": student.id,
            "course_code": course_code,
            "plan_text": (
                f"Student {student.student_id} is at risk in {course_code}. "
                f"Recommended actions: (1) Weekly 1-on-1 tutoring sessions, "
                f"(2) Additional practice assignments, (3) Peer study group assignment, "
                f"(4) Mid-term progress review in 4 weeks."
            ),
            "status": random.choice(["drafted", "approved", "in_progress", "completed"]),
            "notified_lecturer_id": lecturer.id,
        }, student_id=student.id, course_code=course_code)
    
    db.commit()
    print("✅ Interventions seeded")


def seed_announcements(db):
    """Create campus announcements."""
    print("📢 Seeding announcements...")
    
    announcements = [
        ("Semester Registration Open", 
         "Registration for Semester 2026-S2 opens on July 15. Please complete your course selection by July 31.",
         "all", True),
        ("Library Extended Hours",
         "Central library will be open until 11 PM during exam period (Dec 1-20).",
         "student", False),
        ("Faculty Development Workshop",
         "Workshop on 'AI in Education' scheduled for Aug 15-16. Registration required.",
         "lecturer", True),
        ("Placement Drive - TechCorp Solutions",
         "TechCorp visiting campus on Sep 20. Eligible students: CGPA >= 7.0, no active backlogs.",
         "student", True),
        ("Campus Fest - Beru Utsav 2026",
         "Annual cultural fest scheduled for Nov 15-17. Student coordinators needed.",
         "all", False),
    ]
    
    for title, body, audience, pinned in announcements:
        get_or_create(db, Announcement, {
            "body": body,
            "audience": audience,
            "created_by": "admin",
            "pinned": pinned,
        }, title=title)
    
    db.commit()
    print("✅ Announcements seeded")


def seed_campus_resources(db):
    """Create campus resources."""
    print("🏗️ Seeding campus resources...")
    
    resources = [
        ("Central Library", "library", 500, "Main Campus", "active", 0.75, "Main academic library"),
        ("CS Computer Lab 1", "lab", 60, "CS Block", "active", 0.85, "Primary programming lab"),
        ("CS Computer Lab 2", "lab", 60, "CS Block", "active", 0.70, "Secondary programming lab"),
        ("AI Research Lab", "lab", 30, "AI Block", "active", 0.90, "GPU cluster for ML research"),
        ("Electronics Lab", "lab", 40, "EC Block", "active", 0.65, "Hardware and circuits lab"),
        ("Auditorium", "auditorium", 300, "Main Campus", "active", 0.40, "Events and conferences"),
        ("Seminar Hall A", "seminar", 50, "Admin Block", "active", 0.55, "Department seminars"),
        ("Cafeteria", "food", 200, "Student Center", "active", 0.80, "Main dining facility"),
        ("Sports Complex", "sports", 100, "Sports Block", "active", 0.60, "Indoor and outdoor facilities"),
        ("Hostel Block A", "hostel", 200, "Residential Area", "active", 0.95, "Boys hostel"),
        ("Hostel Block B", "hostel", 180, "Residential Area", "active", 0.92, "Girls hostel"),
    ]
    
    for name, rtype, capacity, location, status, util, notes in resources:
        get_or_create(db, CampusResource, {
            "resource_type": rtype,
            "capacity": capacity,
            "location": location,
            "status": status,
            "utilization": util,
            "notes": notes,
        }, name=name)
    
    db.commit()
    print("✅ Campus resources seeded")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🌱 Beru Campus AI - Rich Demo Data Seeder")
    print("=" * 60)
    
    init_db()
    db = SessionLocal()
    
    try:
        seed_users_and_roles(db)
        seed_courses(db)
        seed_rooms(db)
        seed_enrollments_and_grades(db)
        seed_timetable(db)
        seed_placement(db)
        seed_interventions(db)
        seed_announcements(db)
        seed_campus_resources(db)
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMO DATA SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📋 Demo Credentials:")
        print("  Student:   STU2024001 / student123  (3.8 GPA, strong)")
        print("  Student:   STU2024005 / student123  (2.2 GPA, at-risk)")
        print("  Student:   STU2024009 / student123  (1.8 GPA, critical)")
        print("  Faculty:   LEC001 / lecturer123")
        print("  Placement: placement / placement123")
        print("  Admin:     admin / admin123")
        print("\n🚀 Start the stack: docker compose up")
        print("🌐 Frontend: http://localhost:5173")
        print("📡 Backend:  http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()