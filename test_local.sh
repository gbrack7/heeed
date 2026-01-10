#!/bin/bash
# Test script to run the bot locally with environment variables
# Usage: ./test_local.sh

export BYBIT_API_KEY="IQLf80eQtGNRghf7ux"
export BYBIT_API_SECRET="6qcz3FE9j2cXr8afh2JLSAwA4AD5qHSXi7VC"

# Optional: Override settings if needed
# export SYMBOL_LONG="HYPEUSDT"
# export SYMBOL_SHORT="JASMYUSDT"
# export USD_POSITION_SIZE="1500"
# export TRIGGER_DROP_PCT="12"

echo "Starting bot with environment variables..."
python3 hedge_server.py
