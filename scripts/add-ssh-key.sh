#!/bin/bash
# Add SSH key to Hetzner server
# Run this if you have password access

SERVER="root@178.156.139.210"
SSH_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIja7XvuHg62bd7TXxOyPTxDiU5NQZx2zkJbEryKWqT0 logan.glosser@gmail.com"

echo "Adding SSH key to $SERVER..."

ssh "$SERVER" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$SSH_KEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '✅ Key added successfully'"

echo "Testing new key..."
ssh "$SERVER" "echo '✅ SSH key authentication working!'"
