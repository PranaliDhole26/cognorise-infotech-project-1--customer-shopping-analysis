# Project Document: Customer Churn and Retention Analysis

---

## 📁 1. Project Directory Structure

Create the following folder layout in your workspace:

```text
customer_churn_and_retention_analysis/
│
├── 📂 data/
│   ├── raw/                       # Raw customer activity, transaction, and subscription data
│   └── processed/                 # Cleaned datasets and feature-engineered metrics
│
├── 📂 sql/
│   ├── 01_data_cleaning.sql       # Cleaning & standardization scripts
│   ├── 02_metrics_gen.sql         # Queries for tenure, purchase frequency, inactivity
│   └── 03_segmentation.sql        # Logic for Active, At Risk, and Churned segments
│
├── 📂 scripts/
│   ├── 01_eda_churn.py            # Python EDA & key churn indicator analysis
│   └── 02_feature_summary.py      # Data validation and feature aggregation helper
│
├── 📂 dashboards/
│   └── power_bi_specifications.md # Power BI specs, DAX measures, and visual layouts
│
├── 📂 reports/
│   └── retention_strategy.md     # Practical retention recommendations & action plan
│
└── 📄 README.md                   # Execution guide and project workflow
```

---

## 🛠️ 2. SQL Scripts (`/sql`)

### File: `sql/01_data_cleaning.sql`
```sql
-- Step 1: Clean raw subscription and transaction data
CREATE OR REPLACE TABLE processed_customer_transactions AS
WITH cleaned_data AS (
    SELECT 
        LOWER(TRIM(customer_id)) AS customer_id,
        CAST(transaction_date AS DATE) AS transaction_date,
        CAST(amount AS NUMERIC) AS amount,
        LOWER(TRIM(subscription_type)) AS subscription_type,
        LOWER(TRIM(status)) AS status
    FROM raw_customer_transactions
    WHERE customer_id IS NOT NULL 
      AND transaction_date IS NOT NULL
)
SELECT DISTINCT * FROM cleaned_data;
```

### File: `sql/02_metrics_gen.sql`
```sql
-- Step 2: Create customer-level behavioral metrics
CREATE OR REPLACE TABLE customer_metrics AS
WITH aggregated_metrics AS (
    SELECT 
        customer_id,
        MIN(transaction_date) AS first_activity_date,
        MAX(transaction_date) AS last_activity_date,
        COUNT(DISTINCT transaction_date) AS total_active_days,
        COUNT(transaction_date) AS total_transactions,
        SUM(amount) AS total_spend,
        
        -- Tenure calculation in days
        DATEDIFF('day', MIN(transaction_date), MAX(transaction_date)) + 1 AS tenure_days,
        
        -- Inactivity period relative to current cutoff date
        DATEDIFF('day', MAX(transaction_date), CURRENT_DATE()) AS inactivity_days
    FROM processed_customer_transactions
    GROUP BY customer_id
)
SELECT 
    customer_id,
    first_activity_date,
    last_activity_date,
    tenure_days,
    inactivity_days,
    total_transactions,
    total_spend,
    -- Purchase frequency (Transactions per 30 days of tenure)
    ROUND(total_transactions / NULLIF((tenure_days / 30.0), 0), 2) AS purchase_frequency_per_month
FROM aggregated_metrics;
```

### File: `sql/03_segmentation.sql`
```sql
-- Step 3: Segment customers into Active, At Risk, and Churned groups based on business rules
CREATE OR REPLACE TABLE customer_segments AS
SELECT 
    customer_id,
    tenure_days,
    inactivity_days,
    purchase_frequency_per_month,
    total_spend,
    CASE 
        WHEN inactivity_days <= 30 THEN 'Active'
        WHEN inactivity_days BETWEEN 31 AND 90 THEN 'At Risk'
        ELSE 'Churned'
    END AS customer_segment
FROM customer_metrics;
```

---

## 🐍 3. Python Analysis Script (`/scripts`)

### File: `scripts/01_eda_churn.py`
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def load_and_prep_data(filepath):
    """Loads processed customer metrics and applies churn definitions."""
    df = pd.read_csv(filepath)
    df['customer_segment'] = df['inactivity_days'].apply(
        lambda x: 'Active' if x <= 30 else ('At Risk' if x <= 90 else 'Churned')
    )
    df['is_churned'] = np.where(df['customer_segment'] == 'Churned', 1, 0)
    return df

def perform_eda(df):
    """Executes exploratory data analysis and exports visualizations."""
    print("=== CUSTOMER SEGMENTATION BREAKDOWN ===")
    print(df['customer_segment'].value_counts(normalize=True) * 100)
    
    print("\n=== SUMMARY STATISTICS BY SEGMENT ===")
    print(df.groupby('customer_segment')[['tenure_days', 'total_spend', 'purchase_frequency_per_month']].mean())
    
    # Plotting
    plt.figure(figsize=(14, 6))
    
    # Chart 1: Tenure vs Segment
    plt.subplot(1, 2, 1)
    sns.boxplot(x='customer_segment', y='tenure_days', data=df, palette='Set2')
    plt.title('Tenure Distribution across Customer Segments')
    plt.xlabel('Customer Segment')
    plt.ylabel('Tenure (Days)')
    
    # Chart 2: Correlation Matrix
    plt.subplot(1, 2, 2)
    numeric_df = df.select_dtypes(include=[np.number])
    sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', fmt=".2f")
    plt.title('Feature Correlation Matrix')
    
    plt.tight_layout()
    plt.savefig('../reports/churn_eda_summary.png')
    print("\nVisual summary successfully saved to reports/churn_eda_summary.png")

if __name__ == "__main__":
    data_path = "../data/processed/customer_metrics.csv"
    try:
        data = load_and_prep_data(data_path)
        perform_eda(data)
    except FileNotFoundError:
        print(f"Error: Processed dataset not found at {data_path}. Run SQL/data pipeline first.")
```

---

## 📊 4. Power BI Specifications (`/dashboards`)

### File: `dashboards/power_bi_specifications.md`
```markdown
# Power BI Dashboard Specifications

## Data Model
- **Primary Fact Table:** `customer_segments`
- **Secondary Transaction Table:** `processed_customer_transactions`
- **Relationship:** 1-to-Many on `customer_id`

## Key DAX Measures

1. Total Customers:
   `Total Customers = DISTINCTCOUNT(customer_segments[customer_id])`

2. Churned Customers:
   `Churned Customers = CALCULATE([Total Customers], customer_segments[customer_segment] = "Churned")`

3. Overall Churn Rate:
   `Churn Rate = DIVIDE([Churned Customers], [Total Customers], 0)`

4. At-Risk Customers:
   `At Risk Count = CALCULATE([Total Customers], customer_segments[customer_segment] = "At Risk")`

5. Average Tenure:
   `Avg Tenure (Days) = AVERAGE(customer_segments[tenure_days])`

## Visual Layout Blueprint
- **Header KPI Cards:** Total Revenue | Churn Rate % | At-Risk Customer Count | Average Tenure
- **Row 1 Visuals:**
  - Donut Chart: Customer Share by Segment (Active vs. At Risk vs. Churned)
  - Line Chart: Monthly Churn Rate Trend Over Time
- **Row 2 Visuals:**
  - Clustered Bar Chart: Churn Rate by Tenure Group (0–3 mos, 3–6 mos, 6–12 mos, 12+ mos)
  - Priority Table: High-Value At-Risk Customers (Spend > $500 & Segment = "At Risk")
```

---

## 💡 5. Retention Strategy (`/reports`)

### File: `reports/retention_strategy.md`
```markdown
# Customer Retention Strategies & Action Plan

## 1. Targeted Winback Campaigns for "At Risk" Segment (31–90 Days Inactive)
- **Automated Trigger Alarms:** Dispatch automated re-engagement messaging via email/SMS as soon as a user passes 30 days of inactivity.
- **Incentive Offers:** Provide targeted discounts or value-add bonuses calibrated to past purchase frequency.

## 2. Onboarding Optimization for New Customers (0–90 Days Tenure)
- **Early Dropping Prevention:** Analysis reveals the highest churn probability occurs within the first 60 days of customer tenure.
- **Action Step:** Implement structured onboarding drip sequences, guided feature walkthroughs, and proactive support outreach during Month 1.

## 3. High-Value VIP Retention Protocols
- **Segment:** Active/At Risk users in the top 20% of `total_spend`.
- **Action Step:** Assign dedicated relationship management, grant exclusive product updates, and perform direct feedback check-ins before inactivity reaches 30 days.
```

---

## 📄 6. README Guide (`README.md`)

### File: `README.md`
```markdown
# Customer Churn and Retention Analysis

## Implementation Instructions

1. **Folder Setup:** Recreate the directory structure outlined in Section 1.
2. **Data Pipeline:**
   - Place raw transactional files in `data/raw/`.
   - Execute SQL scripts in order: `01_data_cleaning.sql` → `02_metrics_gen.sql` → `03_segmentation.sql`.
   - Save output as `data/processed/customer_metrics.csv`.
3. **Exploratory Data Analysis:**
   - Run `python scripts/01_eda_churn.py` to produce statistical summaries and churn correlations.
4. **Dashboard Setup:**
   - Import `customer_metrics.csv` into Power BI.
   - Build metrics and visual charts following `dashboards/power_bi_specifications.md`.
5. **Strategy Deployment:**
   - Review actionable recommendations in `reports/retention_strategy.md`.
```