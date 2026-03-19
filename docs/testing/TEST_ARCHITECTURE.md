# Test Architecture - Directory-Based Separation

## Overview

We've implemented **proper test separation** using directory structure instead of pytest markers, addressing the architectural concern that "they should just be totally different folders."

## Directory Structure

```
tests/
├── __init__.py
├── unit/                    # Fast unit tests (3.04s)
│   ├── __init__.py
│   ├── test_base_adapter.py         # Adapter logic
│   ├── test_business_sample_adapter.py  # Parsing logic
│   ├── test_dummy_adapter.py        # Simple logic
│   ├── test_file_adapter_dispatcher.py  # Dispatcher logic
│   ├── test_import_service_conflict_bug.py  # Conflict resolution
│   ├── test_models.py               # Data models
│   ├── test_nursing_sample_adapter.py   # Parsing logic
│   └── test_term_utils.py           # Term generation
└── integration/             # Slow integration tests (14.09s)
    ├── __init__.py
    ├── test_database_service_integration.py  # SQLite-backed persistence flows
    ├── test_frontend_smoke.py        # Selenium browser tests
    └── test_import_business_logic.py  # File I/O + Database
```

## Performance Results

### Unit Tests (`tests/unit/`)

- **56 tests** in **3.04 seconds**
- **All tests <0.5s each** (performance threshold met)
- **Pure logic, no I/O, no external dependencies**
- **Instant feedback for developers**

### Integration Tests (`tests/integration/`)

- **18 tests** in **14.09 seconds**
- **File I/O, database operations, browser automation**
- **Comprehensive end-to-end validation**
- **Run separately or in CI parallel workers**

## Quality Gate Integration

### Before (Marker-Based)

```bash
pytest -m "not integration"  # Complex filtering
```

### After (Directory-Based)

```bash
pytest tests/unit/           # Simple, clear separation
pytest tests/integration/    # Run when needed
```

## Benefits

1. **🎯 Clear Architectural Boundaries**: No ambiguity about test categorization
2. **⚡ Fast Development Feedback**: Unit tests provide instant validation (3s)
3. **🔧 Simple CI/CD**: Easy to parallelize different test types
4. **📁 Intuitive Organization**: Developers immediately understand structure
5. **🚫 No Complex Markers**: Eliminates pytest marker management overhead

## Running Tests

### Development (Fast Feedback)

```bash
# Run only unit tests for quick validation
pytest tests/unit/
```

### Comprehensive Testing

```bash
# Run all tests
pytest

# Or run separately
pytest tests/unit/
pytest tests/integration/
```

### Quality Gate

```bash
# Preferred unit-test validation gate
sm swab -g overconfidence:untested-code.py --verbose
```

## Test Categorization Guidelines

### Unit Tests (`tests/unit/`)

- ✅ Pure business logic
- ✅ Data model validation
- ✅ Algorithm testing
- ✅ Mocked external dependencies
- ✅ <0.5 seconds execution time

### Integration Tests (`tests/integration/`)

- ✅ Database I/O operations
- ✅ File system interactions
- ✅ Browser automation (Selenium)
- ✅ API endpoint testing
- ✅ Multi-component workflows

This architecture ensures fast development cycles while maintaining comprehensive test coverage.
