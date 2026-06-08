# cuOpt Numerical Optimization API

## Linear Programming (LP)
```python
from cuopt import linear_programming

# Minimize: 3x + 5y
# Subject to: x + y <= 4, 2x + y <= 6
problem = linear_programming.LP(
    c=[3, 5],  # objective coefficients
    A=[[1, 1], [2, 1]],  # constraint matrix
    b=[4, 6],  # constraint bounds
    bounds=[(0, None), (0, None)],  # variable bounds
)

solution = linear_programming.solve(problem)
# solution.x = [2.0, 2.0], solution.fun = 16.0
```

## Mixed Integer Linear Programming (MILP)
```python
problem = linear_programming.MILP(
    c=[3, 5],
    A=[[1, 1], [2, 1]],
    b=[4, 6],
    bounds=[(0, None), (0, None)],
    integrality=[1, 1],  # integer variables
)

solution = linear_programming.solve(problem)
```

## Quadratic Programming (QP)
```python
from cuopt import quadratic_programming

problem = quadratic_programming.QP(
    P=[[2, 0], [0, 2]],  # quadratic cost matrix
    q=[0, 0],  # linear cost vector
    A=[[1, 1]],  # inequality constraints
    b=[1],
)

solution = quadratic_programming.solve(problem)
```

## GPU Acceleration
```python
# All solving on GPU
solution = linear_programming.solve(
    problem,
    device="gpu",
    time_limit=60,
)
```

## Solution Format
```python
{
    "x": [2.0, 2.0],       # optimal variables
    "fun": 16.0,            # optimal objective value
    "status": "optimal",    # solver status
    "iterations": 42,       # solver iterations
}
```
