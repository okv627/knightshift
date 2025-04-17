# Tests

This folder contains unit tests to validate core logic of the pipeline.

### Current Coverage:
- `test_pgn_parser.py`: Tests for PGN parsing accuracy.
- `test_utils.py`: Tests for shared utility functions.
- `test_validation_logic.py`: Tests for game record validation rules.

Run with: `pytest tests/`

Or:
$env:PYTHONPATH = "src"
pytest tests/test_db_utils.py
