#!/bin/bash
# One-time system setup for OpenArm module
# Installs system packages and configures auto CAN setup

set -e

echo "=== OpenArm System Setup ==="

# 1. Add OpenArm PPA and install system packages
echo "Installing OpenArm system packages..."
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:openarm/main
sudo apt-get update
sudo apt-get install -y \
  can-utils \
  iproute2 \
  libopenarm-can-dev \
  openarm-can-utils

echo "✓ OpenArm CLI tools installed (openarm-can-zero-position-calibration, etc.)"

# 2. Setup udev rules for automatic CAN configuration on USB connection
echo ""
echo "Setting up automatic CAN configuration..."

sudo tee /etc/udev/rules.d/99-openarm-can.rules > /dev/null <<'EOF'
# OpenArm CAN interfaces - auto-configure when USB devices are connected
# This triggers whenever can0 or can1 interface is added to the system

ACTION=="add", SUBSYSTEM=="net", KERNEL=="can0", RUN+="/bin/bash -c 'sleep 1 && /usr/bin/ip link set can0 type can bitrate 1000000 dbitrate 5000000 fd on && /usr/bin/ip link set up can0'"

ACTION=="add", SUBSYSTEM=="net", KERNEL=="can1", RUN+="/bin/bash -c 'sleep 1 && /usr/bin/ip link set can1 type can bitrate 1000000 dbitrate 5000000 fd on && /usr/bin/ip link set up can1'"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "✓ udev rules installed - CAN interfaces will auto-configure on USB connection"

# 3. Configure CAN now (for current session)
echo ""
echo "Configuring CAN interfaces for current session..."
sudo ip link set can0 type can bitrate 1000000 dbitrate 5000000 fd on 2>/dev/null || true
sudo ip link set up can0 2>/dev/null || true
sudo ip link set can1 type can bitrate 1000000 dbitrate 5000000 fd on 2>/dev/null || true
sudo ip link set up can1 2>/dev/null || true

# Check status
echo ""
echo "=== CAN Interface Status ==="
ip link show can0 2>/dev/null && echo "✓ can0 is up" || echo "⚠ can0 not found (plug in USB adapter)"
ip link show can1 2>/dev/null && echo "✓ can1 is up" || echo "⚠ can1 not found (plug in USB adapter)"

echo ""
echo "✓ System setup complete!"
echo ""
echo "Next steps:"
echo "  1. Plug in OpenArm USB-CAN adapters (if not already connected)"
echo "  2. Verify CAN: ip link show can0 can1"
echo "  3. Calibrate hardware:"
echo "     openarm-can-zero-position-calibration --canport can0 --arm-side right_arm"
echo "     openarm-can-zero-position-calibration --canport can1 --arm-side left_arm"
echo "  4. Sync with LeRobot:"
echo "     python scripts/sync_calibration.py"