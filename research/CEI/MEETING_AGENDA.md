# CEI Stakeholder Meeting Agenda

**Date:** [TBD]
**Duration:** 60 minutes
**Attendees:** Dr. Leslie Jernberg (Assessment Champion), Dean Matthew R. Taylor, [Development Team]

---

## Meeting Overview (2 minutes)

**Objective:** Validate requirements and establish collaboration framework for CEI's course assessment system pilot.

**Expected Outcomes:**
- Shared understanding of technical approach and timeline
- Validation of user roles and workflows
- Agreement on data requirements and collaboration process
- Clear next steps for development and testing

---

## 1. Introductions (3 minutes)

### Team Introductions
- Brief background and role in the project
- Relevant experience with educational technology and assessment systems

### CEI Team
- Current roles and responsibilities in assessment process
- Experience with current Access database system
- Vision for improved workflow

---

## 2. Personal Motivation & Transparency (5 minutes)

### Why This Project Matters
**Personal motivation for taking on this challenge:**
- [Your personal reasons for pursuing this project]
- Commitment to improving educational assessment workflows
- Belief in technology's role in reducing administrative burden
- Long-term vision for scalable, user-friendly assessment tools

### Project Approach
- Collaborative development with real stakeholder input
- Transparent communication throughout the process
- Focus on solving actual problems, not theoretical ones
- Commitment to delivering practical, usable solutions

---

## 3. Technical Vision & High-Level Flows (7 minutes)

### What We're Building
**Web-based course assessment system** that replaces manual Access database management with:

#### Core Workflow:
1. **Faculty Data Entry** → Clean, responsive web forms (no more Access forms)
2. **Real-Time Validation** → Immediate feedback, no data corruption
3. **Live Data Views** → Always-current dashboards (no report generation delays)
4. **Multi-Format Export** → PDF, Excel, CSV, Access for any submission needs

#### Key Features:
- **Multi-user concurrent access** (solves row locking problems)
- **Institution-customizable forms** (adapt to your specific needs)
- **Role-based access control** (appropriate permissions for each user type)
- **Historical data tracking** (trend analysis and comparisons)
- **Mobile-responsive design** (access from any device)

### User Experience Transformation
**Before:** Faculty struggle with Access forms, data gets corrupted, manual reconciliation
**After:** Faculty use intuitive web forms, data is always accurate, live views available

### Live Demo
**Current prototype demonstration:** [https://course-record-updater-742146226593.us-central1.run.app/](https://course-record-updater-742146226593.us-central1.run.app/)
- Clean, responsive web interface with CEI branding
- Course data entry form with validation
- Live data table with edit/delete capabilities
- Document upload with format-specific adapters
- Real-time feedback and error handling
- Mobile-responsive design for any device
- **Sample data already populated** showing realistic course information

---

## 4. "Bridge Not Cliff" Migration Strategy (8 minutes)

### Risk-Free Pilot Approach
**No wholesale replacement** - we provide a bridge to gradually transition:

#### Phase 1: Parallel Operation (Immediate Value)
- **New web forms** go live for faculty data entry
- **Access export feature** maintains your current workflow
- **Both systems run simultaneously** - no disruption to existing processes
- **Immediate benefits:** Better forms, no concurrency issues, real-time validation

#### Phase 2: Data Migration (When Ready)
- **Import your 1,543 CLO records** into the web system
- **Historical data preserved** with full context and relationships
- **Gradual transition** as you become comfortable with new system
- **Access export continues** as long as you need it

#### Phase 3: Full Transition (Your Timeline)
- **Switch to live data views** when ready
- **Retire Access database** on your schedule
- **Export capabilities maintained** for any legacy needs
- **No forced timeline** - transition at your pace

### Minimal Effort, Maximum Value
- **Start using immediately** - no waiting for full migration
- **Keep existing processes** while gaining new capabilities
- **No data loss risk** - everything is preserved and exportable
- **Cancel anytime** - no long-term commitments during pilot

---

## 5. Collaboration Framework (25 minutes)

### What We Need From You

#### A. User Story Validation (8 minutes)
**Review intended user workflows:**
- Faculty data entry process
- Program administrator oversight
- Multi-program administrator coordination
- System administrator management

**Key Questions:**
- Do these workflows match your current process?
- What's missing or incorrect?
- Which workflows are highest priority?

#### B. Role Structure Validation (7 minutes)
**Proposed user roles:**
- Regular User (Faculty/Staff) - Free
- Program Administrator - $19.99/month + per course
- Multi-Program Administrator - $39.99/month + per course (discounted)
- Site Administrator - Global access

**Key Questions:**
- Do these roles match your organizational structure?
- What permissions does each role need?
- Are there additional roles we should consider?

#### C. Data Model Requirements (10 minutes)
**Core data structure discussion:**
- Course information (number, semester, year, enrollment)
- CLO structure (outcomes, assessments, pass rates, narratives)
- Instructor assignments and permissions
- Institution/program hierarchy

**Exemplar: Course Input Form**
Let's walk through one specific example using the live prototype:
- **Live demo:** [Course creation form walkthrough](https://course-record-updater-742146226593.us-central1.run.app/)
- What fields are required for course creation?
- What validation rules are needed?
- How should dropdowns and selections work?
- What custom fields might CEI need?
- **Interactive feedback:** Try the form and provide immediate input
- **Compare to Access:** Show how this replaces their current problematic forms

### Communication & Collaboration Process
**How we'll work together:**
- Regular check-ins during development
- Prototype reviews and feedback sessions
- Direct access to development team for questions
- Transparent progress updates and timeline adjustments

---

## 6. Specific Requirements Gathering (10 minutes)

### Priority Questions for CEI
*[Reference: CEI_STAKEHOLDER_QUESTIONS.md - Top 13 questions]*

**Focus Areas:**
1. **NWCCU Structure** - CLO → PLO → ILO hierarchy
2. **Data Formats** - Grade formats, assessment methods
3. **User Experience** - Faculty and admin dashboard needs
4. **Timeline** - NWCCU deadlines and current pain points

### Next Steps Planning
- Timeline for prototype development
- Schedule for follow-up meetings
- Access to development environment for testing
- Documentation and training materials

---

## 7. Q&A and Next Steps (10 minutes)

### Open Discussion
- Technical questions about the approach
- Concerns about migration or data security
- Timeline expectations and constraints
- Budget and procurement considerations

### Immediate Next Steps
1. **Technical Requirements Document** - Detailed specifications based on today's discussion
2. **Prototype Development** - Initial version for testing and feedback
3. **Follow-up Meeting** - Schedule next review session
4. **Access Setup** - Provide testing environment access

### Success Metrics
**How we'll measure success of this collaboration:**
- Reduced time spent on data entry and validation
- Elimination of multi-user concurrency issues
- Improved faculty experience with assessment reporting
- Streamlined NWCCU submission process
- Maintained data integrity and historical context

---

## Meeting Materials Referenced
- Video analysis of current Access system workflow
- Spreadsheet analysis of 1,543 CLO records
- User stories for all role types
- Data model specifications
- Bridge strategy technical approach

## Follow-up Actions
- [ ] Meeting notes and action items distribution
- [ ] Technical requirements document creation
- [ ] Prototype development timeline
- [ ] Next meeting scheduling
- [ ] Development environment setup
