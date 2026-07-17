# Skill Examples

## Example 1: Web Service Integration

### User Request
"Create a skill for interacting with the GitHub API"

### Generated Skill

**SKILL.md:**
```markdown
---
name: github-api
description: Interact with GitHub API for repository management, issues, pull requests, and releases. Use when working with GitHub repos, managing issues, creating PRs, or when user mentions GitHub API operations.
allowed-tools: WebFetch, Read, Write, Bash
---

# GitHub API Integration

Comprehensive GitHub API interaction for repository management and automation.

## Authentication

First, ensure GitHub token is configured:
```bash
export GITHUB_TOKEN=your_token_here
```

## Core Operations

### Repository Management
- List repositories
- Create new repositories
- Update repository settings
- Delete repositories (requires confirmation)

### Issues and Pull Requests
- Create, update, close issues
- Submit and review pull requests
- Manage labels and milestones
- Add comments and reactions

### Releases and Tags
- Create releases with assets
- Manage tags
- Generate release notes
- Upload release artifacts

## API Endpoints

Using the GitHub REST API v3:
- Base URL: `https://api.github.com`
- Authentication: Bearer token in headers
- Rate limiting: 5000 requests/hour (authenticated)

## Usage Examples

### Create Issue
```bash
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/issues \
  -d '{"title":"Bug report","body":"Description here"}'
```

### List Pull Requests
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/pulls
```

## Error Handling

Common status codes:
- 401: Invalid authentication
- 403: Rate limit exceeded
- 404: Resource not found
- 422: Validation failed

Always check response status before processing.
```

## Example 2: Data Processing Skill

### User Request
"Write a skill for analyzing and visualizing CSV data"

### Generated Skill

**SKILL.md:**
```markdown
---
name: csv-analyzer
description: Analyze CSV files for statistics, patterns, and data quality. Generate visualizations and reports. Use when working with CSV data, spreadsheets, or when user needs data analysis, statistics, or data visualization.
---

# CSV Data Analyzer

Professional CSV analysis with statistics, visualization, and quality checks.

## Capabilities

### Data Profiling
- Column statistics (mean, median, mode, std dev)
- Data type detection
- Missing value analysis
- Unique value counts
- Distribution analysis

### Data Quality Checks
- Duplicate detection
- Outlier identification
- Format validation
- Referential integrity
- Completeness metrics

### Visualization
- Histograms and distributions
- Correlation matrices
- Scatter plots
- Time series plots
- Heatmaps

## Analysis Workflow

1. **Load and Inspect**
   - Read CSV file
   - Display first/last rows
   - Show column info
   - Check dimensions

2. **Profile Data**
   - Generate summary statistics
   - Identify data types
   - Find missing values
   - Detect patterns

3. **Quality Assessment**
   - Check for duplicates
   - Identify outliers
   - Validate formats
   - Assess completeness

4. **Visualize Results**
   - Create appropriate charts
   - Generate correlation analysis
   - Plot distributions
   - Export visualizations

## Python Implementation

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_csv(filepath):
    # Load data
    df = pd.read_csv(filepath)

    # Basic info
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")

    # Statistics
    print("\nSummary Statistics:")
    print(df.describe())

    # Missing values
    print("\nMissing Values:")
    print(df.isnull().sum())

    # Data types
    print("\nData Types:")
    print(df.dtypes)

    return df
```

## Output Formats

Results can be exported as:
- Markdown reports
- HTML dashboards
- PDF documents
- Excel workbooks
- JSON summaries
```

## Example 3: Automation Skill

### User Request
"Create a skill for setting up CI/CD pipelines"

### Generated Skill

**SKILL.md:**
```markdown
---
name: cicd-setup
description: Setup and configure CI/CD pipelines for GitHub Actions, GitLab CI, Jenkins, and CircleCI. Use when setting up continuous integration, deployment automation, or when user mentions CI/CD, pipelines, or automated testing.
allowed-tools: Read, Write, Edit, Bash
---

# CI/CD Pipeline Setup

Configure continuous integration and deployment across multiple platforms.

## Supported Platforms

### GitHub Actions
Location: `.github/workflows/`
Format: YAML
Features: Matrix builds, artifacts, secrets

### GitLab CI
Location: `.gitlab-ci.yml`
Format: YAML
Features: Stages, jobs, runners, artifacts

### Jenkins
Location: `Jenkinsfile`
Format: Groovy
Features: Declarative/scripted pipelines

### CircleCI
Location: `.circleci/config.yml`
Format: YAML
Features: Workflows, orbs, parallelism

## Common Pipeline Stages

1. **Build**
   - Compile code
   - Generate artifacts
   - Create containers

2. **Test**
   - Unit tests
   - Integration tests
   - Coverage reports

3. **Security**
   - Dependency scanning
   - SAST/DAST
   - License checks

4. **Deploy**
   - Staging deployment
   - Production deployment
   - Rollback capability

## Implementation Guide

### Analyze Project
- Identify language/framework
- Determine test requirements
- Define deployment targets
- List required secrets

### Create Pipeline
- Choose appropriate platform
- Define stages and jobs
- Configure triggers
- Setup notifications

### Optimize Performance
- Enable caching
- Parallelize jobs
- Use build matrices
- Minimize dependencies

## Templates

See `templates/` directory for:
- Node.js applications
- Python packages
- Docker containers
- Kubernetes deployments
- Mobile applications
```

## Example 4: File Processing Skill

### User Request
"Write a skill to convert between different file formats"

### Generated Skill

**SKILL.md:**
```markdown
---
name: format-converter
description: Convert between file formats including JSON, YAML, XML, CSV, TOML, and Markdown. Use when user needs file conversion, format transformation, or mentions converting between different data formats.
allowed-tools: Read, Write, Edit
---

# Format Converter

Universal file format conversion with validation and formatting.

## Supported Formats

### Data Formats
- JSON ↔ YAML
- JSON ↔ XML
- JSON ↔ CSV
- YAML ↔ TOML
- XML ↔ CSV

### Document Formats
- Markdown → HTML
- Markdown → PDF
- HTML → Markdown
- RST → Markdown

### Configuration Formats
- ENV ↔ JSON
- INI ↔ TOML
- Properties ↔ YAML

## Conversion Process

1. **Validate Source**
   - Check file exists
   - Verify format
   - Parse content
   - Handle errors

2. **Transform Data**
   - Map structure
   - Convert types
   - Preserve metadata
   - Handle special cases

3. **Generate Output**
   - Format correctly
   - Validate result
   - Pretty print
   - Save file

## Special Handling

### CSV Conversions
- Detect headers
- Infer types
- Handle nested data
- Preserve encoding

### XML Conversions
- Preserve attributes
- Handle namespaces
- Maintain CDATA
- Convert entities

### JSON Conversions
- Preserve order (if needed)
- Handle dates/times
- Convert numbers accurately
- Escape special characters

## Examples

### JSON to YAML
Input (data.json):
```json
{
  "name": "project",
  "version": "1.0.0",
  "dependencies": ["lib1", "lib2"]
}
```

Output (data.yaml):
```yaml
name: project
version: 1.0.0
dependencies:
  - lib1
  - lib2
```

### CSV to JSON
Input (data.csv):
```csv
name,age,city
Alice,30,NYC
Bob,25,LA
```

Output (data.json):
```json
[
  {"name": "Alice", "age": 30, "city": "NYC"},
  {"name": "Bob", "age": 25, "city": "LA"}
]
```
```

## Example 5: Testing Skill

### User Request
"Create a skill for comprehensive testing strategies"

### Generated Skill

**SKILL.md:**
```markdown
---
name: test-suite
description: Create and manage comprehensive test suites including unit tests, integration tests, E2E tests, and performance tests. Use when setting up testing, writing tests, or when user mentions test coverage, TDD, or test automation.
allowed-tools: Read, Write, Edit, Bash
---

# Comprehensive Testing Suite

Professional testing strategies across multiple frameworks and languages.

## Test Types

### Unit Tests
- Isolated component testing
- Mock dependencies
- Fast execution
- High coverage targets

### Integration Tests
- Component interaction
- Database testing
- API testing
- Service integration

### End-to-End Tests
- User journey testing
- Browser automation
- Mobile app testing
- Full system validation

### Performance Tests
- Load testing
- Stress testing
- Spike testing
- Endurance testing

## Framework Support

### JavaScript/TypeScript
- Jest, Mocha, Vitest
- React Testing Library
- Cypress, Playwright
- Supertest for APIs

### Python
- pytest, unittest
- Django test framework
- Selenium WebDriver
- Locust for load testing

### Java
- JUnit, TestNG
- Mockito
- Spring Boot Test
- JMeter

### Go
- Built-in testing
- Testify
- Ginkgo/Gomega
- go-stress-testing

## Testing Strategy

1. **Test Pyramid**
   - 70% Unit tests
   - 20% Integration tests
   - 10% E2E tests

2. **Coverage Goals**
   - Line coverage: 80%+
   - Branch coverage: 75%+
   - Function coverage: 90%+

3. **Best Practices**
   - Descriptive test names
   - Arrange-Act-Assert pattern
   - One assertion per test
   - Independent tests
   - Clean test data

## Implementation Examples

### Unit Test Template
```javascript
describe('ComponentName', () => {
  beforeEach(() => {
    // Setup
  });

  afterEach(() => {
    // Cleanup
  });

  it('should perform expected behavior', () => {
    // Arrange
    const input = prepareInput();

    // Act
    const result = functionUnderTest(input);

    // Assert
    expect(result).toBe(expectedValue);
  });
});
```

### Integration Test Template
```python
class APIIntegrationTest(TestCase):
    def setUp(self):
        self.client = TestClient()
        self.test_data = create_test_data()

    def test_full_workflow(self):
        # Create resource
        response = self.client.post('/api/resource', self.test_data)
        self.assertEqual(response.status_code, 201)

        # Verify creation
        resource_id = response.json()['id']
        response = self.client.get(f'/api/resource/{resource_id}')
        self.assertEqual(response.json()['name'], self.test_data['name'])
```

## Continuous Testing

### Pre-commit Hooks
- Run unit tests
- Check coverage
- Lint test files

### CI Pipeline
- Full test suite
- Coverage reports
- Performance benchmarks
- Security scans

### Monitoring
- Test flakiness tracking
- Performance regression detection
- Coverage trend analysis
```