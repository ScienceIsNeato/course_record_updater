# Excel Import Logs
*Captured during simulated course import flow*

```
2025-11-20 00:05:02,973 - simulate_actions - INFO - Simulating Course Import...
2025-11-20 00:05:02,982 - simulate_actions - INFO - Created import file: demo_data/course_import_template.xlsx
2025-11-20 00:05:02 - ImportService - INFO - [Import] Starting import from: demo_data/course_import_template.xlsx
2025-11-20 00:05:02 - ImportService - INFO - [Import] Conflict strategy: use_theirs
2025-11-20 00:05:02 - ImportService - INFO - [Import] Mode: EXECUTE
2025-11-20 00:05:02 - ImportService - INFO - [Import] File validation passed: File compatible with CEI Excel format (test). Found 2 sample records.
2025-11-20 00:05:02 - ImportService - INFO - [Import] Successfully parsed file with adapter cei_excel_format_v1
2025-11-20 00:05:02 - ImportService - INFO - [Import] Found 2 courses records
2025-11-20 00:05:02 - ImportService - INFO - [Import] Found 2 users records
2025-11-20 00:05:02 - ImportService - INFO - [Import] Found 1 terms records
2025-11-20 00:05:02 - ImportService - INFO - [Import] Found 2 offerings records
2025-11-20 00:05:02 - ImportService - INFO - [Import] Found 2 sections records
2025-11-20 00:05:03 - ImportService - INFO - Updated course: CHEM-101
2025-11-20 00:05:03 - ImportService - INFO - Updated course: PHYS-101
2025-11-20 00:05:03 - ImportService - INFO - Term already exists: 2024 Fall
2025-11-20 00:05:03 - ImportService - INFO - Updated offering: CHEM-101 - 2024 Fall
2025-11-20 00:05:03 - ImportService - INFO - Updated offering: PHYS-101 - 2024 Fall
2025-11-20 00:05:03 - ImportService - INFO - Created section 001 for CHEM-101 in 2024 Fall
2025-11-20 00:05:03 - ImportService - INFO - Created section 001 for PHYS-101 in 2024 Fall
2025-11-20 00:05:03,025 - simulate_actions - INFO - Import Result: Success=True, Created=2, Updated=6
```

