---
name: data_analyst
description: Analyzes data files and generates insights with visualizations
version: "1.0"
author: Assitance Team
tags: [data, analysis, python, visualization]
---

# Data Analyst Skill

## Instructions

When asked to analyze data:

1. First, read the data file using `file_manager` (CSV, JSON, or text format).
2. Use `execute_code_sandboxed` to run Python analysis:
   ```python
   import json, csv
   # Load and analyze the data
   # Use statistics module for basic stats
   # Print summary statistics
   ```
3. Report:
   - **Dataset Overview**: rows, columns, data types
   - **Summary Statistics**: mean, median, min, max for numeric columns
   - **Key Insights**: top 3-5 patterns or anomalies found
   - **Recommendations**: data-driven suggestions
4. If the user wants a chart description, describe it as ASCII art or structured text.
5. Always note data quality issues (missing values, outliers, inconsistencies).
