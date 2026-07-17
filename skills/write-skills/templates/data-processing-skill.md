---
name: data-processor-name
description: Process and analyze [data type] files for [main purpose]. Use when working with [file formats], performing [operations], or when user mentions [keywords].
allowed-tools: Read, Write, Edit, Bash
---

# [Data Type] Processor

Advanced [data type] processing for [primary use case].

## Supported Formats

### Input Formats
- Format 1 (.ext1) - Description
- Format 2 (.ext2) - Description
- Format 3 (.ext3) - Description

### Output Formats
- Format A - Best for X
- Format B - Best for Y
- Format C - Best for Z

## Processing Pipeline

### 1. Data Ingestion
- Load file(s)
- Validate format
- Parse content
- Handle encoding issues

### 2. Data Cleaning
- Remove duplicates
- Handle missing values
- Standardize formats
- Fix inconsistencies

### 3. Data Transformation
- Apply transformations
- Calculate derived fields
- Aggregate data
- Normalize values

### 4. Data Analysis
- Statistical analysis
- Pattern detection
- Anomaly identification
- Trend analysis

### 5. Output Generation
- Format results
- Generate reports
- Create visualizations
- Export data

## Core Operations

### Operation 1: [Name]
Purpose: What this operation does

Process:
1. Step one
2. Step two
3. Step three

Example:
```python
# Code example
def operation_one(data):
    # Implementation
    return processed_data
```

### Operation 2: [Name]
Purpose: What this operation does

Process:
1. Step one
2. Step two

## Configuration Options

```yaml
processing:
  input_format: auto  # auto, csv, json, xml
  output_format: json
  encoding: utf-8
  delimiter: ","

cleaning:
  remove_duplicates: true
  handle_missing: drop  # drop, fill, interpolate
  standardize_dates: true

analysis:
  calculate_statistics: true
  detect_outliers: true
  generate_report: true
```

## Usage Examples

### Basic Processing
```bash
# Simple file processing
python process.py input.csv --output result.json
```

### Advanced Processing
```python
from processor import DataProcessor

# Initialize processor
processor = DataProcessor(config='config.yaml')

# Load data
data = processor.load('input_file.csv')

# Clean data
cleaned = processor.clean(data,
    remove_duplicates=True,
    handle_missing='interpolate'
)

# Transform data
transformed = processor.transform(cleaned,
    operations=['normalize', 'aggregate']
)

# Analyze
results = processor.analyze(transformed)

# Export
processor.export(results, 'output.json')
```

## Data Quality Checks

### Input Validation
- File exists and readable
- Format matches expected
- Schema validation
- Data type checking

### Processing Validation
- Row count consistency
- Column preservation
- Value range checks
- Referential integrity

### Output Validation
- Completeness check
- Format verification
- Size constraints
- Business rules

## Performance Optimization

### Memory Management
- Stream processing for large files
- Chunk-based processing
- Lazy evaluation
- Memory-mapped files

### Speed Optimization
- Parallel processing
- Vectorized operations
- Caching strategies
- Index optimization

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| ParseError | Invalid format | Check file format and encoding |
| MemoryError | File too large | Use chunk processing |
| ValidationError | Schema mismatch | Update schema or fix data |
| TimeoutError | Processing too slow | Optimize or increase timeout |

### Recovery Strategies
1. Automatic retry with backoff
2. Partial processing recovery
3. Error logging and reporting
4. Fallback processing modes

## Monitoring and Logging

### Metrics Tracked
- Processing time
- Memory usage
- Error rate
- Data quality score
- Throughput

### Log Levels
- DEBUG: Detailed processing steps
- INFO: Major milestones
- WARNING: Data quality issues
- ERROR: Processing failures

## Best Practices

1. **Data Validation**
   - Always validate input
   - Check intermediate results
   - Verify output quality

2. **Performance**
   - Profile before optimizing
   - Use appropriate data structures
   - Consider memory constraints

3. **Reliability**
   - Implement checkpointing
   - Handle errors gracefully
   - Provide clear error messages

4. **Documentation**
   - Document data schemas
   - Explain transformations
   - Provide usage examples