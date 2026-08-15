"""In-app notification service.

Notifications are materialized lazily from live analytics on first read and
deduplicated by a per-user fingerprint, so the 60s polling loop on the frontend
never creates duplicates and existing records (shortlists, announcements) show
up retroactively without event hooks.

Sources by role:
  student  -> at-risk alerts, earned badges, placement shortlists
  placement/lecturer/admin -> drive summaries
  everyone -> announcements matching their role (or "all")
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Announcement, Notification, PlacementDrive, PlacementNotification, User
from app.services import student_growth, students

MAX_ENTRIES = 50

ROLE_HOME = {
    "student": "/student",
    "lecturer": "/faculty",
    "placement": "/placement",
    "admin": "/admin",
}

ROLE_LABELS = {
    "student": "Student",
    "lecturer": "Faculty",
    "placement": "Placement",
    "admin": "Admin",
}


def _candidates(db: Session, user: User) -> list[dict]:
    out: list[dict] = []
    role = user.role

    if role == "student":
        student = students.resolve_student(db, user)
        if student is not None:
            for alert in students.get_alerts(db, student):
                detail = (f"{alert.get('detail', '')} {alert.get('recommendation', '')}").strip()
                out.append(
                    {
                        "fingerprint": f"risk:{alert['title']}",
                        "type": "risk",
                        "severity": alert.get("severity", "medium"),
                        "title": alert["title"],
                        "body": detail,
                        "link": "/student/insights",
                    }
                )
            gam = student_growth.get_gamification(db, student)
            for badge in gam.get("badges", []):
                if badge.get("earned"):
                    out.append(
                        {
                            "fingerprint": f"milestone:{badge['id']}",
                            "type": "milestone",
                            "severity": "low",
                            "title": "Milestone unlocked",
                            "body": f"You earned the '{badge['name']}' badge. {badge.get('description', '')}".strip(),
                            "link": "/student/community",
                        }
                    )
            rows = db.execute(
                select(PlacementNotification).where(PlacementNotification.student_id == student.id)
            ).scalars().all()
            for n in rows:
                out.append(
                    {
                        "fingerprint": f"shortlist:{n.drive_id or n.id}",
                        "type": "shortlist",
                        "severity": "medium",
                        "title": n.title,
                        "body": n.body,
                        "link": "/student/community",
                    }
                )

    if role in ("placement", "lecturer", "admin"):
        drives = db.execute(select(PlacementDrive)).scalars().all()
        for drive in drives:
            notified = db.execute(
                select(func.count(PlacementNotification.id)).where(PlacementNotification.drive_id == drive.id)
            ).scalar_one()
            if notified:
                out.append(
                    {
                        "fingerprint": f"drive:{drive.id}",
                        "type": "drive",
                        "severity": "medium",
                        "title": f"Drive updates · {drive.title}",
                        "body": f"{notified} student(s) notified for this drive.",
                        "link": "/placement/drives",
                    }
                )

    announcements = db.execute(select(Announcement).order_by(Announcement.created_at.desc())).scalars().all()
    creator_names = [a.created_by for a in announcements if a.created_by]
    creator_roles: dict[str, str] = {}
    if creator_names:
        creator_roles = {
            u.username: u.role
            for u in db.execute(select(User).where(User.username.in_(creator_names))).scalars()
        }
    for a in announcements:
        if a.audience in ("all", role):
            who = ""
            if a.created_by:
                role_label = ROLE_LABELS.get(creator_roles.get(a.created_by, ""), "")
                who = f"{a.created_by} ({role_label}) · " if role_label else f"{a.created_by} · "
            out.append(
                {
                    "fingerprint": f"announcement:{a.id}",
                    "type": "announcement",
                    "severity": "low",
                    "title": f"{who}{a.title}",
                    "body": a.body,
                    "link": "/admin/announcements" if role == "admin" else ROLE_HOME.get(role, "/"),
                }
            )
    return out


def materialize(db: Session, user: User) -> None:
    existing_rows = db.execute(
        select(Notification).where(Notification.user_id == user.id)
    ).scalars().all()
    existing = {n.fingerprint: n for n in existing_rows}
    changed = False
    for candidate in _candidates(db, user):
        row = existing.get(candidate["fingerprint"])
        if row is None:
            db.add(Notification(user_id=user.id, **candidate))
            changed = True
        else:
            if (
                row.title != candidate["title"]
                or row.body != candidate["body"]
                or row.link != candidate["link"]
            ):
                row.title = candidate["title"]
                row.body = candidate["body"]
                row.link = candidate["link"]
                changed = True
    if changed:
        db.commit()


def list_notifications(db: Session, user: User) -> dict:
    materialize(db, user)
    rows = (
        db.execute(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(MAX_ENTRIES)
        )
        .scalars()
        .all()
    )
    entries = [
        {
            "id": n.id,
            "type": n.type,
            "severity": n.severity,
            "title": n.title,
            "body": n.body,
            "link": n.link,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]
    unread = db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id, Notification.read.is_(False)
        )
    ).scalar_one()
    return {"entries": entries, "unread_count": unread}


def mark_read(db: Session, user: User, notification_id: str) -> dict:
    n = db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    ).scalar_one_or_none()
    if n is None:
        raise ValueError("notification not found")
    n.read = True
    db.commit()
    return {"id": n.id, "read": True}


def mark_all_read(db: Session, user: User) -> dict:
    rows = db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.read.is_(False))
    ).scalars().all()
    for n in rows:
        n.read = True
    db.commit()
    return {"updated": len(rows)}
