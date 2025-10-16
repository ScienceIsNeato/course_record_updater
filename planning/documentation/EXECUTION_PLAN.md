# **Project Plan – Learning Outcomes AsSaaSment**
**Pilot: College of Eastern Idaho (MockU) – NWCCU Accreditation**

---

## 1. Purpose
This document outlines the phased plan for developing a lightweight SaaS tool to help departments at U.S. community colleges track and report **student learning outcomes (SLOs)** for accreditation. The first pilot will be with **MockU’s Biology Department**, aligned to **NWCCU** standards.

---

## 2. Objectives
- Replace error-prone spreadsheets with a simple, department-level web tool.
- Enable **self-service adoption** without requiring institution-wide IT buy-in.
- Provide **low-cost, per-course pricing** that undercuts enterprise competitors.
- Build the product with a modular **adapter system** to scale across accrediting regions.

---

## 3. Stakeholders
- **Pilot Institution:** College of Eastern Idaho
- **Primary Accreditor:** NWCCU
- **Primary Users:** Department Deans (Biology initially), faculty contributors
- **Secondary Users:** Institutional Research staff, admins compiling accreditation reports

---

## 4. Execution Plan (Phased)

### **Phase 1 – Requirements Validation (MockU/NWCCU)**
- Meet with MockU Biology leadership (Matt + boss).
- Validate assumptions: required data fields, report format, cadence, workflow.
- Collect sample NWCCU reports/templates.
- Deliverables:
  - Confirmed data model
  - Example report to model Report Builder
  - Success criteria for pilot (e.g., Fall 2025 report <30 minutes, <5% error)

### **Phase 2 – MVP Build (Pilot Only)**
- Core workflows:
  - Manual entry form (course + outcomes data)
  - File upload + adapter parsing (initially just NWCCU/MockU style)
  - Ledger view (sortable/searchable)
  - Report Builder (Word/PDF export modeled on MockU submission format)
- Costs:
  - Cloud hosting (Cloud Run/Firestore): $25–50/month
  - Domain & SSL: ~$20/year
  - Development: sweat equity
  - One-time adapter development: ~20–40 hrs

### **Phase 3 – Pilot Test & Feedback**
- Biology department at MockU runs one cycle using the tool.
- Feedback collected from faculty, admins, and dean.
- Iterations: UI polish, adapter tweaks, export refinements.

### **Phase 4 – Regional Expansion (NWCCU colleges)**
- Build **NWCCU adapter v2** generalized for multiple departments/institutions.
- Market to other NWCCU-accredited community colleges (150+ potential).
- Pricing: $8.99/course/month with first course free trial.

### **Phase 5 – Multi-Region Expansion**
- Add new adapters for other accreditors:
  - HLC (Midwest, largest accreditor)
  - SACSCOC (South)
  - ACCJC (California)
- Each accreditor requires:
  - Data model alignment
  - Export template/report builder customization

---

## 5. User Stories

### **Data Entry**
- As a faculty member, I can manually add a course and outcomes so they’re stored centrally.
- As a dean, I can upload existing Word/Excel reports and let the adapter parse them.
- As a dean, I can duplicate a course from a past term so I don’t have to re-enter static details.
- As a user, I can edit a course inline in the ledger table for quick fixes.
- As a user, I can delete a course if it was added in error.

### **Maintenance**
- As a department, I can archive past reports by term.
- As a dean, I can update outcomes/courses without breaking historical records.
- As an admin, I can view all historical versions of a course for audit purposes.
- As a user, I can attach supporting documents (rubrics, syllabi) to courses for future reference.

### **Reporting**
- As a dean, I can generate a report in the NWCCU template format.
- As a college, I can export past cycles to demonstrate longitudinal improvement.
- As a dean, I can download the report in both Word (editable) and PDF (submission-ready).
- As a user, I can filter reports by aim, course, or term for custom slices.
- As a department, I can generate a summary view that highlights gaps (courses without aims mapped).

### **Quality Assurance**
- As a dean, I can run a pre-submission “validation check” to catch missing or invalid data before exporting.
- As an admin, I can lock a report once submitted, ensuring integrity of past submissions.

### **Future Enhancements (Post-MVP)**
- As an institution, I can grant multiple users access with role-based permissions.
- As a faculty member, I can enter assessment results directly (scores/percentages).
- As an admin, I can auto-import data from LMS exports with minimal formatting changes.

---

## 6. Validation Meeting Agenda (MockU Pilot)

**A. Current Workflow**
- How is the NWCCU report currently produced?
- Which tools (Excel, Word, LMS) are in use?

**B. Data Requirements**
- Required metrics? (grades, pass rates, student outcome attainment)
- Targets/benchmarks needed?
- Rubrics or only grades?

**C. Reporting**
- File format NWCCU expects (Word/PDF)?
- Standard templates?
- Cadence (annual, mid-cycle, year-7)?

**D. Roles & Permissions**
- Who enters data?
- Who approves/signs off?

**E. Maintenance**
- How often do courses/outcomes change?
- Should past reports be versioned?

**F. Automation**
- Value of spreadsheet adapters?
- Manual entry acceptable?

---

## 7. Costs (Pilot Focus)
| Item | Cost |
|------|------|
| Domain & SSL | $20/year |
| Cloud Run + Firestore | $25–50/month |
| Development | Sweat equity |
| Adapter Dev (MockU/NWCCU) | ~20–40 hrs (your time) |
| Expansion Adapter (future) | ~$500/region if outsourced |

---

## 8. Revenue Potential (Back-of-Envelope)

**Assumptions:** $8.99/course/month, 1 account per institution.
- Small dept (~10 courses): $899/year
- Medium dept (~25 courses): $2,697/year
- Large dept (~50 courses): $5,394/year

**Regional penetration (NWCCU, ~150 CCs):**
- 10% adoption (15 schools, avg 25 courses): ~$40K ARR
- 25% adoption (38 schools, avg 25 courses): ~$101K ARR
- 50% adoption (75 schools, avg 25 courses): ~$202K ARR

---

## 9. Key References
- [NWCCU Accreditation Standards](https://nwccu.org/accreditation/standards-policies/)
- [NWCCU Resources](https://nwccu.org/resources/)
- [College of Eastern Idaho – Accreditation](https://mocku.test/accreditation)

---

## 10. Next Steps
1. Meet with Matt’s boss → validate assumptions.
2. Capture actual MockU/NWCCU reporting templates.
3. Update data model + user flows.
4. Build MockU/NWCCU adapter + MVP.
5. Run pilot Fall 2025.
6. Iterate + expand to other NWCCU colleges.
