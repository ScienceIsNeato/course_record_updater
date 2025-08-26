# CEI Analysis Session Summary

**Date:** August 26, 2025
**Session Focus:** Video analysis, spreadsheet deep dive, strategic refinement

## 🎯 Major Discoveries

### **Missing Primary Entity: Course Learning Outcomes (CLOs)**
- **1,543 CLO records** in CEI's system across 173 courses
- **CLOs are the primary assessment unit**, not courses
- Each course has multiple CLOs (1:many relationship)
- Each CLO assessed independently with S/U determination

### **Real System Architecture (From CEI Data):**
```
Institution (CEI)
├── Programs (Biology, Nursing, etc.)
├── Courses (ACC-201, ENGL-101, etc.)
└── CLOs (ACC-201.1, ACC-201.2, etc.) ← PRIMARY ASSESSMENT LEVEL
```

### **Current System Pain Points Validated:**
- Microsoft Access "held together with bubble gum and duct tape"
- Multi-user concurrency issues (row locking, data corruption)
- Poor form UX ("I can't build forms, but it's functional")
- Manual data reconciliation and math validation

## 🌉 Strategic Pivot: Bridge Strategy

### **Key Insight:** Migration risk is the biggest barrier
**Solution:** Provide Access export functionality to enable parallel operation

### **Bridge Features:**
- Export web data to Access-compatible formats
- Course-level and bulk export options
- "Use at your own risk" import scripts
- No direct Access database modification

### **Benefits:**
- Eliminates migration fear
- Allows gradual adoption
- Maintains existing workflow during evaluation
- Builds trust through collaboration vs. disruption

## 📊 Technical Refinements

### **Data Model Updates:**
- Added **CourseOutcome (CLO)** as primary entity
- CLO fields: assessment_tool, pass rates, S/U results, narratives
- 75% threshold for S/U determination
- celebrations/challenges/changes workflow

### **Export Integration:**
- Multiple format options (Excel, CSV, SQL)
- Field mapping documentation
- Sample import scripts with disclaimers
- Clear liability boundaries

### **Pricing Strategy:**
- Basic Access export included in all tiers
- Advanced export features in higher tiers
- Custom branding (CSS upload) capability

## 🤔 Remaining Questions

### **Hierarchy Above CLOs:**
- How do CLOs roll up to Program Learning Outcomes (PLOs)?
- Are there Institutional Learning Outcomes (ILOs)?
- What's the complete NWCCU reporting structure?

### **Views & Reporting Focus:**
- What reports does NWCCU actually require?
- Who needs what views of the data?
- Real-time dashboards vs. static reports?
- PDF export requirements for submissions?

## 📋 Updated Stakeholder Questions

**Added 20 new CEI-specific questions:**
- Hierarchy and structure (CLO → PLO → ILO?)
- Current system pain points (quantify the problems)
- Reporting requirements (what NWCCU actually needs)
- Views and dashboards (who sees what data)
- Migration and integration (Access export value)

## 🎯 Meeting Strategy

### **Lead with Understanding:**
- Reference specific CEI data (1,543 CLO records, Abbigail's ACC-201 course)
- Acknowledge their Access system investment
- Show we understand the CLO-centric assessment model

### **Focus on Views, Not Reports:**
- Ask what data views they need
- Understand the complete hierarchy above CLOs
- Design live dashboards with export capabilities
- Avoid building static reports

### **Emphasize Collaboration:**
- Bridge strategy reduces risk
- Access export maintains existing workflow
- Parallel operation during evaluation
- Technical solutions without marketing fluff

## 🚀 Next Steps

### **Immediate Actions:**
1. Update all planning documentation with CLO model
2. Prepare meeting materials focusing on views/hierarchy questions
3. Design mockups showing CLO-centric interface
4. Plan Access export technical implementation

### **Meeting Preparation:**
- Use updated stakeholder questions (60 targeted questions)
- Focus on understanding complete hierarchy
- Validate bridge strategy value
- Get specific reporting requirements

### **Technical Planning:**
- Design CourseOutcome entity and relationships
- Plan Access export engine architecture
- Consider view-based reporting system
- Prepare CSS customization capability

## 💡 Key Insights

### **Product Strategy:**
- **Bridge, not cliff** - work with existing systems
- **Views, not reports** - live data with export capability
- **CLO-centric design** - assessment is the primary workflow
- **Technical focus** - let capabilities speak for themselves

### **Competitive Advantage:**
- Most SaaS forces migration; we enable coexistence
- Deep understanding of accreditation workflow
- Real data from actual stakeholder validates approach
- Bridge strategy reduces adoption friction

This session transformed our understanding from theoretical to practical, with real data and stakeholder insights driving technical decisions.
