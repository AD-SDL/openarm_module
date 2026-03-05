#!/usr/bin/env python3
"""Test IK with reachable positions."""

import numpy as np
from openarm.kinematics.inverse.ikpy import IkpyInverseKinematics

print("=== Testing Reachable Positions ===\n")

ik_solver = IkpyInverseKinematics()

# First, let's see where the arm is at some known joint configurations
print("=== Forward Kinematics Test ===")
print("Testing where the end-effector is at various joint angles:\n")

test_configs = [
    ("All zeros", np.zeros(7)),
    ("J1=45°", np.deg2rad([45, 0, 0, 0, 0, 0, 0])),
    ("J2=45°", np.deg2rad([0, 45, 0, 0, 0, 0, 0])),
    ("J4=90°", np.deg2rad([0, 0, 0, 90, 0, 0, 0])),
    ("Home pose", np.deg2rad([0, -30, 0, 60, 0, 0, 0])),
]

reachable_positions = []

for name, joint_angles in test_configs:
    # Build full joint array (12 links total)
    joint_angles_full = np.zeros(12)
    joint_angles_full[1:8] = joint_angles
    
    # Compute FK
    fk_matrix = ik_solver._right_chain.forward_kinematics(joint_angles_full)
    pos = fk_matrix[:3, 3]
    
    print(f"{name:15s}: x={pos[0]:>7.3f}, y={pos[1]:>7.3f}, z={pos[2]:>7.3f}")
    reachable_positions.append((name, pos))

print("\n=== Inverse Kinematics Test ===")
print("Now testing IK to reach those same positions:\n")

for name, target_pos in reachable_positions:
    print(f"Target: {name} -> x={target_pos[0]:.3f}, y={target_pos[1]:.3f}, z={target_pos[2]:.3f}")
    
    # Solve IK
    joint_solution = ik_solver.solve_right_arm(target_pos)
    joint_solution_deg = np.rad2deg(joint_solution)
    
    # Check if solution is valid (not all zeros)
    if np.allclose(joint_solution, 0, atol=1e-3):
        print("  ✗ IK FAILED (returned zeros)")
    else:
        print(f"  ✓ IK SUCCESS: {joint_solution_deg}")
        
        # Verify with FK
        joint_full = np.zeros(12)
        joint_full[1:8] = joint_solution
        fk_check = ik_solver._right_chain.forward_kinematics(joint_full)
        pos_check = fk_check[:3, 3]
        error = np.linalg.norm(pos_check - target_pos)
        print(f"    Verification: x={pos_check[0]:.3f}, y={pos_check[1]:.3f}, z={pos_check[2]:.3f}")
        print(f"    Error: {error*1000:.2f}mm")
    print()

print("\n=== Workspace Analysis ===")
print("Based on the FK results, the right arm workspace appears to be:")
all_positions = np.array([pos for _, pos in reachable_positions])
print(f"  X range: {all_positions[:, 0].min():.3f} to {all_positions[:, 0].max():.3f}")
print(f"  Y range: {all_positions[:, 1].min():.3f} to {all_positions[:, 1].max():.3f}")
print(f"  Z range: {all_positions[:, 2].min():.3f} to {all_positions[:, 2].max():.3f}")