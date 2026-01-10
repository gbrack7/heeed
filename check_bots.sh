#!/bin/bash
echo "=== Running Hedge Bots ==="
ps aux | grep -i "hedge_server\|python.*hedge" | grep -v grep | awk '{print "PID: "$2" | Started: "$9" "$10" | Command: "$11" "$12}'
echo ""
echo "=== Current Bot Settings ==="
grep -E "symbol_long|symbol_short|trigger_drop_pct|usd_position_size" /Users/gideonbrack/Desktop/heeed/hedge_server.py | head -4
