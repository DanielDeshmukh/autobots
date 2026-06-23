# Financial Calculator Skill

## Purpose
Structured financial modeling — ROI, burn rate, projections. For bots handling business logic or cost estimation in proposals.

## Core Calculations

### Return on Investment (ROI)
```python
def roi(investment, returns):
    """Calculate ROI as percentage."""
    return ((returns - investment) / investment) * 100

# Example: $10k investment returns $15k
# roi(10000, 15000) = 50%
```

### Burn Rate
```python
def burn_rate(monthly_costs, revenue=0):
    """Monthly cash consumption."""
    return monthly_costs - revenue

def runway(cash_on_hand, burn_rate):
    """Months until cash runs out."""
    if burn_rate <= 0:
        return float('inf')
    return cash_on_hand / burn_rate
```

### Compound Growth
```python
def future_value(principal, rate, periods):
    """FV = PV * (1 + r)^n"""
    return principal * (1 + rate) ** periods

def present_value(future_value, rate, periods):
    """PV = FV / (1 + r)^n"""
    return future_value / (1 + rate) ** periods
```

### Break-Even Analysis
```python
def break_even(fixed_costs, price_per_unit, variable_cost_per_unit):
    """Units needed to break even."""
    contribution_margin = price_per_unit - variable_cost_per_unit
    if contribution_margin <= 0:
        return float('inf')
    return fixed_costs / contribution_margin
```

## Projection Templates

### Revenue Projection
```python
def project_revenue(base_revenue, growth_rate, months):
    projections = []
    for month in range(months):
        revenue = future_value(base_revenue, growth_rate / 12, month)
        projections.append({
            'month': month + 1,
            'revenue': round(revenue, 2)
        })
    return projections
```

### Cost Projection
```python
def project_costs(base_costs, inflation_rate, months):
    projections = []
    for month in range(months):
        costs = future_value(base_costs, inflation_rate / 12, month)
        projections.append({
            'month': month + 1,
            'costs': round(costs, 2)
        })
    return projections
```

### Profitability Analysis
```python
def profitability(revenue projections, cost_projections):
    analysis = []
    for rev, cost in zip(revenue_projections, cost_projections):
        profit = rev['revenue'] - cost['costs']
        margin = (profit / rev['revenue'] * 100) if rev['revenue'] > 0 else 0
        analysis.append({
            'month': rev['month'],
            'revenue': rev['revenue'],
            'costs': cost['costs'],
            'profit': round(profit, 2),
            'margin': round(margin, 1)
        })
    return analysis
```

## Unit Economics

### Customer Acquisition Cost (CAC)
```python
def cac(total_marketing_spend, new_customers):
    return total_marketing_spend / new_customers if new_customers > 0 else 0
```

### Lifetime Value (LTV)
```python
def ltv(avg_revenue_per_customer, avg_lifespan_months):
    return avg_revenue_per_customer * avg_lifespan_months
```

### LTV:CAC Ratio
```python
def ltv_cac_ratio(ltv, cac):
    if cac <= 0:
        return float('inf')
    return ltv / cac
    # Healthy: > 3:1
```

## Quality Checklist
- [ ] Input validation
- [ ] Division by zero protection
- [ ] Rounding appropriate to context
- [ ] Units clearly labeled
- [ ] Assumptions documented