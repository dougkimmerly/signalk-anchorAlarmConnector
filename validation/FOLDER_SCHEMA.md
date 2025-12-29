# Validation Framework Folder Schema

This document defines the standard folder structure for the validation framework. All agents and scripts MUST follow this schema.

## Directory Structure

```
validation/
├── .claude/
│   └── agents/           # Agent instruction files
│       ├── python-coder.md
│       └── test-analyzer.md
│
├── scripts/              # Executable test runners and harnesses
│   ├── overnight_test_runner.py     # Main overnight test suite
│   ├── quick_validation_test.py     # Quick 4-corner validation
│   ├── pre_test_reset.sh            # Test environment reset
│   └── check_test_status.sh         # Test status monitoring
│
├── analysis/             # Reusable analysis tools
│   ├── analyze_overnight_results.py # Automated test analysis
│   ├── analyze_boat_movement.py     # Movement pattern analysis
│   ├── analyze_physics.py           # Physics validation
│   ├── score_tests.py               # Test scoring system
│   ├── test_analyzer.py             # General test analyzer
│   └── analyze_*.py                 # Ad-hoc analysis scripts
│
├── utils/                # Shared Python utilities
│   ├── signalk_auth.py              # SignalK authentication
│   └── signalk_helpers.py           # API helper functions
│
├── unit/                 # JavaScript unit tests
│   ├── physics.test.js              # Physics engine tests
│   └── integration.test.js          # Integration tests
│
├── data/                 # Test execution data (runtime/temporary)
│   ├── overnight_tests_YYYYMMDD_HHMMSS/  # Overnight test sessions
│   │   ├── TEST_LOG.md              # Test execution log
│   │   ├── raw_data/                # Individual test JSON files
│   │   │   └── test_*.json
│   │   └── FINAL_REPORT.md          # Session summary
│   └── quick_tests/                 # Quick validation test data
│
├── results/              # Analysis reports and findings
│   ├── ANALYSIS_REPORT.txt          # Latest automated analysis
│   ├── *_ANALYSIS_REPORT.md         # Dated analysis reports
│   └── docs/                        # Historical analysis documentation
│
├── logs/                 # System logs and debug output
│   └── *.log
│
├── legacy/               # Archived/deprecated files
│
├── docs/                 # Validation framework documentation
│   ├── OVERNIGHT_TEST_GUIDE.md      # How to run overnight tests
│   ├── QUICK_TEST_GUIDE.md          # Quick validation guide
│   └── TROUBLESHOOTING.md           # Common issues and solutions
│
├── FOLDER_SCHEMA.md      # This file - folder structure reference
├── CLAUDE.md             # Validation framework guide for AI agents
└── AGENT_GUIDE.md        # Quick reference for agent usage

```

## Directory Purposes

### `.claude/agents/` - Agent Instructions
- **Purpose**: Agent configuration and instruction files
- **Who uses it**: Claude Code task system
- **Who writes to it**: Manual editing only
- **File format**: Markdown instruction files

### `scripts/` - Executable Test Runners
- **Purpose**: Main test execution scripts and harnesses
- **Who uses it**: Developers, CI/CD systems, cron jobs
- **Who writes to it**: python-coder agent (when creating test runners)
- **File format**: Python (.py), Bash (.sh)
- **Examples**:
  - Test runners that execute test suites
  - Test harness scripts
  - Environment setup/teardown scripts
  - Test status monitoring tools

### `analysis/` - Reusable Analysis Tools
- **Purpose**: Standalone analysis tools that process test data
- **Who uses it**: test-analyzer agent, developers
- **Who writes to it**: python-coder agent (when creating analysis tools)
- **File format**: Python (.py)
- **Examples**:
  - Scripts that analyze JSON test results
  - Tools that generate statistics from test data
  - Visualization generators
  - Data processing utilities
- **NOT for**: One-off analysis scripts that won't be reused

### `utils/` - Shared Python Utilities
- **Purpose**: Common helper functions used across multiple scripts
- **Who uses it**: All Python scripts in validation framework
- **Who writes to it**: python-coder agent (when creating shared utilities)
- **File format**: Python modules (.py)
- **Examples**:
  - SignalK API authentication
  - Common API helper functions
  - Shared data processing functions
  - Configuration loaders

### `unit/` - JavaScript Unit Tests
- **Purpose**: Unit tests for JavaScript physics engine and integration tests
- **Who uses it**: Developers, CI/CD
- **Who writes to it**: js-coder agent, manual editing
- **File format**: JavaScript (.js)
- **Run with**: `node validation/unit/physics.test.js`

### `data/` - Test Execution Data
- **Purpose**: Runtime test data and results from test executions
- **Who uses it**: Test runners, analysis tools
- **Who writes to it**: Test runner scripts (overnight_test_runner.py, etc.)
- **File format**: JSON, Markdown, directories
- **Subdirectories**:
  - `overnight_tests_YYYYMMDD_HHMMSS/` - Overnight test session folders
  - `quick_tests/` - Quick validation test data
- **Retention**: Keep recent sessions, archive/delete old sessions as needed
- **NOT tracked in git**: Add to .gitignore (except .gitkeep)

### `results/` - Analysis Reports
- **Purpose**: Finalized analysis reports and findings
- **Who uses it**: Developers, test-analyzer agent
- **Who writes to it**: Analysis scripts, test-analyzer agent
- **File format**: Markdown (.md), Text (.txt)
- **Examples**:
  - `ANALYSIS_REPORT.txt` - Latest automated analysis
  - `SLACK_MOTOR_ANALYSIS_REPORT.md` - Specific feature analysis
  - Dated analysis reports with timestamps
- **Subdirectories**:
  - `docs/` - Historical/archived analysis documentation
- **Retention**: Keep indefinitely, archive to docs/ when superseded

### `logs/` - System Logs
- **Purpose**: Debug output, error logs, system diagnostics
- **Who uses it**: Debugging, troubleshooting
- **Who writes to it**: Test scripts, system processes
- **File format**: .log files
- **Retention**: Rotate/clean up periodically

### `legacy/` - Archived Files
- **Purpose**: Deprecated or superseded files kept for reference
- **Who uses it**: Historical reference only
- **Who writes to it**: Manual archival
- **File format**: Any

### `docs/` - Framework Documentation
- **Purpose**: User guides and framework documentation
- **Who uses it**: Developers, new users
- **Who writes to it**: Manual editing, documentation agents
- **File format**: Markdown (.md)
- **Examples**: Test guides, troubleshooting guides, setup instructions

## File Naming Conventions

### Test Data Files
```
test_[testType]_[windSpeed]kn_[depth]m_[timestamp].json
Example: test_autoDrop_1kn_3m_20251206_111434.json
```

### Test Session Folders
```
overnight_tests_YYYYMMDD_HHMMSS/
Example: overnight_tests_20251206_110625/
```

### Analysis Reports
```
[TOPIC]_ANALYSIS_REPORT.[md|txt]
Example: SLACK_MOTOR_ANALYSIS_REPORT.md
         ANALYSIS_REPORT.txt
```

### Analysis Scripts
```
analyze_[specific_topic].py
Example: analyze_slack.py
         analyze_boat_movement.py
```

## Agent Workflow

### test-analyzer Agent
1. Read test data from `data/overnight_tests_*/`
2. Use existing tools in `analysis/` if available
3. If new analysis tool needed: **Spawn python-coder agent**
4. Write reports to `results/`
5. **NEVER** write Python code directly

### python-coder Agent
1. **For test runners**: Create in `scripts/`
2. **For analysis tools**: Create in `analysis/`
3. **For shared utilities**: Create in `utils/`
4. **NEVER** create Python files in `validation/` root

### Test Runner Scripts
1. Write test data to `data/overnight_tests_YYYYMMDD_HHMMSS/`
2. Write logs to `logs/` (optional)
3. Call analysis scripts from `analysis/`
4. Generate reports in test session folder or `results/`

## Path References in Code

### Reading Test Data
```python
# Correct - use data/ directory
test_dir = "validation/data/overnight_tests_20251206_110625"
data_file = f"{test_dir}/raw_data/test_autoDrop_1kn_3m.json"
```

### Writing Reports
```python
# Correct - use results/ directory
report_path = "validation/results/ANALYSIS_REPORT.txt"
```

### Importing Utilities
```python
# Correct - import from utils/
from validation.utils.signalk_auth import get_auth_token
from validation.utils.signalk_helpers import get_path_value
```

## Migration Notes

This schema was established on 2025-12-06. Prior structure had:
- `analysis/docs/` for reports → Moved to `results/docs/`
- `overnight_tests_*/` in validation root → Moved to `data/`
- Analysis reports scattered → Consolidated to `results/`

## Maintenance

- Review and clean up `data/` periodically (keep last 30 days)
- Archive old reports from `results/` to `results/docs/`
- Clean up `logs/` periodically (keep last 7 days)
- Update this schema when adding new directory purposes
