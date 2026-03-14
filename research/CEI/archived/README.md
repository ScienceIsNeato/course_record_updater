# CEI Archived Materials

This directory contains historical demo materials that have been superseded by generic, reusable versions.

## Why Archived?

After the October 2025 CEI demo, we identified the need for generic demo materials that could be used for:

- Product pitches to any institution
- Training new users
- General product showcases
- GIF/video demos for marketing

The CEI-specific materials served their purpose for that pilot demo, but maintaining institution-specific versions would fragment our demo system.

## What Was Moved Here

### LEARNING_OUTCOMES_DEMO_2024-10-24.md (October 24, 2025)

**Original Purpose:** Step-by-step demo script for CEI leadership meeting  
**New Location:** `docs/workflow-walkthroughs/core-workflow-demo.md` (generalized)  
**Changes Made:**

- Removed CEI-specific references (Leslie Jernberg, CEI institution)
- Replaced CEI Excel format with generic CSV format
- Updated test data references to generic demo data
- Kept the same workflow structure (still the primary use case)

### CEI_Demo_Implementation_Plan.md

**Original Purpose:** 8-week follow-up plan to address gaps found in October 2025 demo  
**New Location:** Lessons extracted to `docs/workflow-walkthroughs/demo-lessons-learned.md`  
**Why Archived:** Implementation plan was CEI-specific and time-bound. The lessons learned are more valuable than the specific plan.

## What Remains Active

### CEI_Demo_Follow_ups.md

**Status:** Still in `research/CEI/` (not archived)  
**Why:** Valuable historical record of actual demo feedback. Referenced by demo-lessons-learned.md.

### 2024FA_test_data.xlsx

**Status:** Still in `research/CEI/` (not archived)  
**Why:** Example of CEI's Excel format. Useful for format adapter testing.

### Other CEI Research

**Status:** All other materials in `research/CEI/` remain active  
**Why:** Stakeholder research, format analysis, and pilot information still relevant.

## How to Use Generic Demo Materials

The new generic demo system is located in `docs/workflow-walkthroughs/`:

### Quick Start

```bash
# Seed demo database with generic data
python scripts/seed_db.py --demo --clear --env dev

# Validate setup
python docs/workflow-walkthroughs/scripts/validate_demo.py

# Follow demo script
open docs/workflow-walkthroughs/core-workflow-demo.md
```

### Key Files

- `core-workflow-demo.md` - Full 30-minute end-to-end demo (migrated from CEI version)
- `feature-showcase.md` - Individual feature demonstrations
- `demo-setup.md` - Technical preparation guide
- `demo-lessons-learned.md` - What we learned from the CEI demo

## Migration Date

**Archived:** November 11, 2025  
**Branch:** feature/workflow-walkthroughs  
**Reason:** Transitioning from CEI-specific to generic reusable demo materials

## Historical Context

The CEI demo (October 24, 2025) was our first major product demonstration. It revealed several critical gaps:

- Students took vs. enrolled data model issue
- CLO vs. course-level narrative confusion
- Missing "Never Coming In" status
- Need for flexible due dates
- Course-level enrollment section missing

Many of these gaps have since been addressed in the product. The lessons learned inform our current demo approach and feature prioritization.

## References

For the full story of the CEI demo and what we learned:

- Read: `docs/workflow-walkthroughs/demo-lessons-learned.md`
- Context: `research/CEI/CEI_Demo_Follow_ups.md` (still active)

---

**Note:** These archived materials are kept for historical reference but should not be used for future demos. Use the generic materials in `docs/workflow-walkthroughs/` instead.
