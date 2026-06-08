# cuOpt Routing API

## Vehicle Routing Problem (VRP)
```python
from cuopt import routing

# Define cost matrix
cost_matrix = routing.CostMatrix(
    data=[[0, 10, 15, 20],
          [10, 0, 35, 25],
          [15, 35, 0, 30],
          [20, 25, 30, 0]],
    type="distance"
)

# Solve VRP
solution = routing.solve(
    cost_matrix=cost_matrix,
    num_vehicles=2,
    depot=0,
)
```

## Traveling Salesman Problem (TSP)
```python
solution = routing.solve_tsp(
    cost_matrix=cost_matrix,
    method="nearest_neighbor",
)
```

## Pickup and Delivery (PDP)
```python
solution = routing.solve_pdp(
    cost_matrix=cost_matrix,
    pickups=[1, 2],
    deliveries=[3, 4],
    num_vehicles=2,
)
```

## GPU-Accelerated Solving
```python
# All solving happens on GPU automatically
solution = routing.solve(
    cost_matrix=cost_matrix,
    num_vehicles=10,
    time_limit=30,  # seconds
    device="gpu",
)
```

## Solution Format
```python
{
    "vehicle_routes": [
        {"vehicle_id": 0, "route": [0, 1, 3, 0], "cost": 45},
        {"vehicle_id": 1, "route": [0, 2, 4, 0], "cost": 55},
    ],
    "total_cost": 100,
    "status": "optimal|feasible",
}
```
