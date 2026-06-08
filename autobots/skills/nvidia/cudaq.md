# CUDA-Q Quantum Computing Guide

## Circuit Definition
```python
import cudaq

@cudaq.kernel
def bell_state():
    q = cudaq.qvector(2)
    h(q[0])
    cx(q[0], q[1])
    mz(q)
```

## Simulation
```python
# State vector simulation
result = cudaq.sample(bell_state, shots_count=1000)
print(result)  # { 00: 502, 11: 498 }

# Density matrix simulation
dm = cudaq.density_matrix(bell_state)
```

## Hybrid Quantum-Classical
```python
@cudaq.kernel
def variational_ansatz(params: list[float], q: cudaq.qview):
    for i in range(len(q)):
        ry(params[i], q[i])
    for i in range(len(q) - 1):
        cx(q[i], q[i+1])

# Classical optimizer
def cost_function(params):
    return cudaq.sample(variational_ansatz, params).get_expectation("Z")

optimizer = cudaq.optimizers.COBYLA()
result = optimizer.minimize(cost_function, initial_params)
```

## QPU Hardware Targets
```python
# Simulate on different backends
cudaq.set_target("nvidia")           # GPU simulator
cudaq.set_target("qpp")              # CPU simulator
cudaq.set_target("quantinuum", machine="H1-1")  # Hardware
cudaq.set_target("ionq", machine="simulator")    # Hardware
```

## Key Concepts
- **Qubit**: Quantum bit, exists in superposition of |0⟩ and |1⟩
- **Gate**: Quantum operation (H, CNOT, Ry, etc.)
- **Measurement**: Collapse superposition to classical bit
- **Entanglement**: Correlated qubits across distance
- **Noise Model**: Simulate real hardware errors
