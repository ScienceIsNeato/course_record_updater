# Architecture: UUID vs Natural Key Usage

## Problem Statement

Using UUIDs as primary session identifiers creates instability across database operations:

- **Session invalidation**: User sessions become invalid after database reseeds
- **Logical instability**: Deleting and recreating "Biology 101" generates a new UUID, breaking references
- **Demo workflow breaks**: Every `--clear` operation invalidates all sessions
- **No semantic identity**: Two "Harvard" institutions should never coexist, but UUIDs treat them as completely distinct

## Solution: Natural Key Architecture

We use a **hybrid approach**: UUIDs for database relationships, natural keys for session stability.

### Core Principle

**Sessions store natural keys. Database uses UUIDs. Resolve on each request.**

## Implementation

### 1. Session Layer (Natural Keys)

Sessions store stable, human-meaningful identifiers:

```python
session["email"] = "user@example.com"  # User's natural key
session["institution_short_name"] = "DEMO2025"  # Institution's natural key
session["role"] = "institution_admin"
```

**Why**: These keys remain valid even if database is cleared and reseeded with same data.

### 2. Database Layer (UUIDs)

Database continues using UUIDs for primary keys and foreign key relationships:

```python
class Institution:
    id = Column(String, primary_key=True)  # UUID
    short_name = Column(String, unique=True, nullable=False)  # Natural key

class User:
    user_id = Column(String, primary_key=True)  # UUID
    email = Column(String, unique=True, nullable=False)  # Natural key
    institution_id = Column(String, ForeignKey("institutions.id"))  # UUID relationship
```

**Why**: UUIDs prevent collisions, enable distributed systems, and simplify relationships.

### 3. Resolution Layer (Bridge)

Helper functions resolve natural keys to UUIDs when needed:

```python
def get_current_institution_id() -> Optional[str]:
    """Resolve institution UUID from session's natural key."""
    institution_short_name = session.get("institution_short_name")
    institution = db.get_institution_by_short_name(institution_short_name)
    return institution.get("id") if institution else None
```

**API routes call this once per request:**

```python
@api.route("/dashboard/data")
@login_required
def get_dashboard_data():
    institution_id = get_current_institution_id()  # Resolves natural key → UUID
    data = dashboard_service.get_data(institution_id)  # Uses UUID
    return jsonify(data)
```

## Natural Keys by Entity

| Entity          | Natural Key                                | Notes                                                |
| --------------- | ------------------------------------------ | ---------------------------------------------------- |
| **Institution** | `short_name`                               | Unique, stable (e.g., "DEMO2025", "MIT", "STANFORD") |
| **User**        | `email`                                    | Unique, stable, user-controlled                      |
| **Course**      | `course_number` + `institution_short_name` | Composite key (e.g., "BIOL-101" at "MIT")            |
| **Program**     | `name` + `institution_short_name`          | Composite key (e.g., "Biology" at "MIT")             |
| **Term**        | `term_code` + `institution_short_name`     | Composite key (e.g., "FA2024" at "MIT")              |

## Benefits

### ✅ Session Persistence

**Before:**

```bash
# Seed database
python seed_db.py --demo --clear --env dev
# Login as demo2025.admin@example.com
# Session stores institution_id: "abc123-uuid..."

# Reseed database
python seed_db.py --demo --clear --env dev
# New institution_id: "def456-uuid..."
# ❌ Session invalid! User sees empty dashboard
```

**After:**

```bash
# Seed database
python seed_db.py --demo --clear --env dev
# Login as demo2025.admin@example.com
# Session stores institution_short_name: "DEMO2025"

# Reseed database
python seed_db.py --demo --clear --env dev
# Institution short_name still "DEMO2025" (stable!)
# ✅ Session valid! Dashboard shows new data
```

### ✅ Logical Identity

**Before:**

```python
# Admin deletes "Biology 101" course
delete_course(course_id="abc123-uuid")

# Admin recreates "Biology 101" course
new_course_id = create_course(number="BIOL-101")  # new_course_id="def456-uuid"

# ❌ Old program mappings, enrollments, outcomes all broken!
```

**After:**

```python
# Lookups use natural keys
course = get_course_by_number("BIOL-101", institution_short_name="MIT")

# If recreated, same natural key resolves to new UUID automatically
# ✅ System recognizes it as "the BIOL-101 course"
```

### ✅ Demo Workflow Stability

- Developers can reseed demo data without invalidating browser sessions
- QA testers can reset test environments without re-logging in
- Demos can be repeated consistently without session management overhead

## Migration Path

### Completed

1. ✅ Session management updated to store `institution_short_name`
2. ✅ Login service passes natural keys to session
3. ✅ `get_current_institution_id()` resolves natural keys to UUIDs
4. ✅ All API routes use resolver (no code changes needed!)
5. ✅ Demo seed script uses stable `short_name="DEMO2025"`

### Future Enhancements

1. **Add natural-key lookups for other entities:**

   ```python
   get_course_by_number_and_institution(course_number, institution_short_name)
   get_program_by_name_and_institution(program_name, institution_short_name)
   get_term_by_code_and_institution(term_code, institution_short_name)
   ```

2. **Session natural keys for programs:**

   ```python
   session["current_program_name"] = "Biological Sciences"  # Instead of UUID
   ```

3. **Audit existing lookups:**
   - Find places that store entity UUIDs in application state
   - Consider converting to natural keys where appropriate

## Design Principles

### When to Use UUIDs

- **Database primary keys**: Always
- **Foreign key relationships**: Always
- **Internal service APIs**: Prefer UUIDs for performance
- **Temporary references within single request**: UUIDs are fine

### When to Use Natural Keys

- **Session storage**: Always (for stability)
- **User-facing identifiers**: Always (e.g., course numbers, usernames)
- **Cross-system integration**: Prefer natural keys (stable across rebuilds)
- **Configuration**: Prefer natural keys (e.g., institution short_name in config files)

### Resolution Strategy

- **Resolve at request boundary**: Don't pass natural keys deep into service layers
- **Cache cautiously**: Natural key → UUID mappings can change across reseeds
- **Fail gracefully**: If natural key doesn't resolve, provide clear error (don't fail silently)

## Testing

To verify natural key architecture works:

```bash
# 1. Seed and login
python scripts/seed_db.py --demo --clear --env dev
./restart_server.sh dev
# Login at http://localhost:3001 with demo2025.admin@example.com / Demo2024!
# Verify dashboard shows data

# 2. Reseed WITHOUT restarting server or browser
python scripts/seed_db.py --demo --clear --env dev

# 3. Refresh browser
# ✅ Should still be logged in and see newly seeded data
# ❌ Before this architecture: would see empty dashboard or be logged out
```

## References

- **Session Management**: `session/manager.py`
- **Natural Key Resolution**: `auth_service.py::get_current_institution_id()`
- **Login with Natural Keys**: `login_service.py`
- **Demo Seeding**: `scripts/seed_db.py::DemoSeeder`

---

_Last Updated: 2025-11-13_
_Author: Architecture refactor to address session stability issues_
