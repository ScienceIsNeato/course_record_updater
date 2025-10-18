# Project Structure Guide

## 📁 Directory Organization

### `/src/` - Source Code
- Main application code
- Keep separate from planning/research materials
- Ready for development when planning phase completes

### `/planning/` - Project Planning
- **`documentation/`** - All planning docs (moved from `/docs/`)
  - `AUTH_REQUIREMENTS.md`
  - `DATA_MODEL.md`
  - `PRICING_STRATEGY.md`
  - `STAKEHOLDER_QUESTIONS.md`
  - `PERMISSION_MATRIX.md`
  - etc.
- **`meetings/`** - Meeting notes and outcomes
- Clean separation of planning from implementation

### `/research/` - Market & Stakeholder Research
- **`MockU/`** - College of Eastern Idaho research data
  - Real stakeholder data and requirements
  - Video walkthroughs of current processes
  - Actual data files for analysis
- **`stakeholder-data/`** - Data from other institutions
- **`competitor-analysis/`** - Market research on existing solutions

### Root Files
- Core project files (README.md, requirements.txt, etc.)
- Configuration files
- This structure guide

## 🎯 Current Phase: Requirements Validation

### Priority 1: MockU Stakeholder Research
1. **Analyze MockU video** - understand current workflow
2. **Review MockU data files** - map to our data model
3. **Prepare stakeholder meeting** - use planning docs
4. **Validate assumptions** - test our planning against reality

### Priority 2: Documentation Updates
- Update planning docs based on MockU insights
- Refine data model with real-world requirements
- Adjust pricing strategy based on stakeholder feedback

## 🚀 Benefits of This Structure

### Clean Separation
- **Planning** materials separate from **source code**
- **Research** data organized by stakeholder/source
- Easy to find relevant documents

### Stakeholder Ready
- All planning docs in one place
- Research materials easily shareable
- Meeting materials organized and accessible

### Development Ready
- Clear `/src/` directory for implementation
- Planning phase outputs ready to guide development
- No mixing of concerns

## 📋 Next Actions

1. **Review MockU materials** in `/research/MockU/`
2. **Prepare meeting** using `/planning/documentation/`
3. **Update planning docs** based on stakeholder feedback
4. **Begin development** in `/src/` when ready

This structure supports our current planning phase while preparing for smooth transition to development.
