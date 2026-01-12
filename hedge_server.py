
import os
import sys
import time
import hmac
import hashlib
import math
import requests
import uuid
from datetime import datetime

# Force unbuffered output for cloud logging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Define get_timestamp first so we can use it in fallback logic
def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# === 🔑 BYBIT API KEYS (from environment, with local fallback) ===
# For cloud deployment: Use environment variables (more secure)
# For local testing: Fall back to hardcoded keys if env vars not set
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")

# Fallback for local testing (only used if env vars not set)
if not API_KEY or not API_SECRET:
    # Check if we're running in a cloud environment (Railway, Render, etc.)
    is_cloud = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or os.getenv("DYNO") or os.getenv("FLY_APP_NAME")
    
    if not is_cloud:
        # Local development - use hardcoded keys for convenience
        print(f"[{get_timestamp()}] ⚠️ Environment variables not set. Using hardcoded keys for local testing.", flush=True)
        API_KEY = "IQLf80eQtGNRghf7ux"
        API_SECRET = "6qcz3FE9j2cXr8afh2JLSAwA4AD5qHSXi7VC"
    else:
        # Cloud environment requires env vars (more secure)
        API_KEY = None
        API_SECRET = None

# Debug: Print all environment variables that start with BYBIT
print("=== ENVIRONMENT VARIABLES DEBUG ===")
for key, value in sorted(os.environ.items()):
    if 'BYBIT' in key.upper():
        print(f"{key} = {value[:10]}... (length: {len(value)})" if value else f"{key} = None/Empty")
print("=== END DEBUG ===")

# === ⚙️ SETTINGS ===
# Option 1: Use individual environment variables (if set)
# Option 2: Use BOT_CONFIG string (format: "SYMBOL_LONG|SYMBOL_SHORT|TRIGGER_PCT|POSITION_SIZE|SCALE_IN|LEGS|STEP")
# Example: "HYPEUSDT|JASMYUSDT|12|1500|True|3|2"

bot_config = os.getenv("BOT_CONFIG")
if bot_config:
    # Parse config string: SYMBOL_LONG|SYMBOL_SHORT|TRIGGER_PCT|POSITION_SIZE|SCALE_IN|LEGS|STEP
    parts = bot_config.split("|")
    if len(parts) >= 7:
        symbol_long = parts[0].strip()
        symbol_short = parts[1].strip()
        trigger_drop_pct = float(parts[2].strip())
        usd_position_size = float(parts[3].strip())
        ENABLE_SCALE_IN = parts[4].strip().lower() == "true"
        SCALE_IN_LEGS = int(parts[5].strip())
        SCALE_IN_DROP_STEP = float(parts[6].strip())
        MAX_USD_POSITION = usd_position_size
        print(f"[{get_timestamp()}] ✅ Using BOT_CONFIG: {symbol_long}/{symbol_short}, {trigger_drop_pct}% trigger, ${usd_position_size}", flush=True)
    else:
        print(f"[{get_timestamp()}] ⚠️ BOT_CONFIG format invalid, using defaults", flush=True)
        symbol_long = os.getenv("SYMBOL_LONG", "MNTUSDT")
        symbol_short = os.getenv("SYMBOL_SHORT", "RAYDIUMUSDT")
        usd_position_size = float(os.getenv("USD_POSITION_SIZE", "1500"))
        MAX_USD_POSITION = float(os.getenv("MAX_USD_POSITION", "1500"))
        trigger_drop_pct = float(os.getenv("TRIGGER_DROP_PCT", "0.01"))
        ENABLE_SCALE_IN = os.getenv("ENABLE_SCALE_IN", "True").lower() == "true"
        SCALE_IN_LEGS = int(os.getenv("SCALE_IN_LEGS", "3"))
        SCALE_IN_DROP_STEP = float(os.getenv("SCALE_IN_DROP_STEP", "2"))
else:
    # Use individual environment variables or defaults
    symbol_long = os.getenv("SYMBOL_LONG", "MNTUSDT")
    symbol_short = os.getenv("SYMBOL_SHORT", "RAYDIUMUSDT")
    usd_position_size = float(os.getenv("USD_POSITION_SIZE", "1500"))
    MAX_USD_POSITION = float(os.getenv("MAX_USD_POSITION", "1500"))
    trigger_drop_pct = float(os.getenv("TRIGGER_DROP_PCT", "0.01"))
    ENABLE_SCALE_IN = os.getenv("ENABLE_SCALE_IN", "True").lower() == "true"
    SCALE_IN_LEGS = int(os.getenv("SCALE_IN_LEGS", "3"))
    SCALE_IN_DROP_STEP = float(os.getenv("SCALE_IN_DROP_STEP", "2"))

endpoint = "https://api.bybit.com"
instrument_cache = {}

# Startup message before checking API keys
print(f"[{get_timestamp()}] 🚀 Starting hedge bot...", flush=True)
print(f"[{get_timestamp()}] 📦 Python version: {sys.version}", flush=True)
print(f"[{get_timestamp()}] 📁 Working directory: {os.getcwd()}", flush=True)

# Check API keys after get_timestamp is defined
if not API_KEY or not API_SECRET:
    print(f"[{get_timestamp()}] ❌ ERROR: BYBIT_API_KEY and BYBIT_API_SECRET must be set as environment variables!", flush=True)
    print(f"[{get_timestamp()}] API_KEY is set: {API_KEY is not None}", flush=True)
    print(f"[{get_timestamp()}] API_SECRET is set: {API_SECRET is not None}", flush=True)
    sys.exit(1)

print(f"[{get_timestamp()}] ✅ API keys loaded", flush=True)
print("KEY TEST:", API_KEY[:6] if API_KEY else "KEY IS EMPTY/NONE", flush=True)
print("KEY LENGTH:", len(API_KEY) if API_KEY else 0, flush=True)
print("SECRET LENGTH:", len(API_SECRET) if API_SECRET else 0, flush=True)


# Removed adjust_qty - using simple rounding like old working bot
# This prevents API call hangs that were causing bot failures

def get_price(symbol):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; HedgeBot/1.0)",
            "Accept": "application/json"
        }
        res = requests.get(f"{endpoint}/v5/market/tickers?category=linear&symbol={symbol}", headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"[{get_timestamp()}] ❌ API returned status {res.status_code} for {symbol}")
            print(f"[{get_timestamp()}] Response preview: {res.text[:300]}")
            return None
        data = res.json()
        if "result" not in data or "list" not in data["result"] or len(data["result"]["list"]) == 0:
            print(f"[{get_timestamp()}] ❌ Unexpected API response format for {symbol}: {data}")
            return None
        price_str = data["result"]["list"][0].get("lastPrice")
        return float(price_str) if price_str else None
    except ValueError as e:
        print(f"[{get_timestamp()}] ❌ JSON decode error for {symbol}: {e}")
        print(f"[{get_timestamp()}] Response text: {res.text[:200] if 'res' in locals() else 'No response'}")
        return None
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Error fetching price for {symbol}: {e}")
        return None

def place_market_order(symbol, side, qty):
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    params = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": str(qty),
        "timeInForce": "GoodTillCancel",
        "orderLinkId": str(uuid.uuid4()),
    }

    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    sign_payload = f"{timestamp}{API_KEY}{recv_window}{query_string}"
    signature = hmac.new(API_SECRET.encode(), sign_payload.encode(), hashlib.sha256).hexdigest()

    headers = {
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(f"{endpoint}/v5/order/create", data=query_string, headers=headers)
    return r.json()

# === 🚀 MAIN BOT LOOP ===
print(f"[{get_timestamp()}] 🔧 Bybit hedge bot started (USDT-perp)...", flush=True)

# Retry initial price fetch with multiple attempts
max_retries = 5
retry_count = 0
price_long = None
price_short = None

while retry_count < max_retries and (not price_long or not price_short):
    print(f"[{get_timestamp()}] 🔄 Fetching initial prices (attempt {retry_count + 1}/{max_retries})...", flush=True)
    price_long = get_price(symbol_long)
    price_short = get_price(symbol_short)
    
    if not price_long or not price_short:
        retry_count += 1
        if retry_count < max_retries:
            print(f"[{get_timestamp()}] ⚠️ Failed to fetch initial prices, retrying in 10 seconds...", flush=True)
            time.sleep(10)
        else:
            print(f"[{get_timestamp()}] ❌ Failed to fetch initial prices after {max_retries} attempts.", flush=True)
            print(f"[{get_timestamp()}] 🔄 Will continue retrying in the main loop...", flush=True)
            # Don't exit - let the main loop handle retries
            price_long = 0  # Set dummy values to avoid division error
            price_short = 1

# Only set initial ratio if we got valid prices
if price_long and price_short and price_long > 0 and price_short > 0:
    initial_ratio = price_long / price_short
    trigger_ratio = initial_ratio * (1 - trigger_drop_pct / 100)
    print(f"[{get_timestamp()}] ✅ Initial prices loaded: {symbol_long}=${price_long}, {symbol_short}=${price_short}", flush=True)
    print(f"[{get_timestamp()}] ✅ Initial ratio: {initial_ratio:.4f}, Trigger ratio: {trigger_ratio:.4f}", flush=True)
else:
    # Set defaults - will be recalculated when prices are fetched
    initial_ratio = None
    trigger_ratio = None
    print(f"[{get_timestamp()}] ⚠️ Initial prices not available, will set ratio when prices are fetched", flush=True)

# Scale-in tracking
scale_in_leg_size = usd_position_size / SCALE_IN_LEGS if ENABLE_SCALE_IN else usd_position_size
scale_in_executed = 0
scale_in_trigger_ratios = []
if ENABLE_SCALE_IN:
    for i in range(SCALE_IN_LEGS):
        drop_pct = trigger_drop_pct + (i * SCALE_IN_DROP_STEP)
        if initial_ratio:
            scale_in_trigger_ratios.append(initial_ratio * (1 - drop_pct / 100))
    if initial_ratio and scale_in_trigger_ratios:
        print(f"[{get_timestamp()}] 📉 Scale-in enabled: {SCALE_IN_LEGS} legs of ${scale_in_leg_size:.0f} each", flush=True)
        print(f"[{get_timestamp()}] 📉 Leg 1 trigger: {scale_in_trigger_ratios[0]:.4f} ({trigger_drop_pct}% drop)", flush=True)
        print(f"[{get_timestamp()}] 📉 Leg {SCALE_IN_LEGS} trigger: {scale_in_trigger_ratios[-1]:.4f} ({trigger_drop_pct + (SCALE_IN_LEGS-1)*SCALE_IN_DROP_STEP}% drop)", flush=True)
else:
    if trigger_ratio:
        print(f"[{get_timestamp()}] 📉 Waiting for {symbol_long}/{symbol_short} to drop to {trigger_ratio:.4f} ({trigger_drop_pct}% below {initial_ratio:.4f})", flush=True)
    else:
        print(f"[{get_timestamp()}] 📉 Waiting for trigger ratio to be calculated...", flush=True)

while True:
    try:
        long_price = get_price(symbol_long)
        short_price = get_price(symbol_short)
        
        if not long_price or not short_price:
            print(f"[{get_timestamp()}] ⚠️ Failed to fetch prices, retrying in 30 seconds...", flush=True)
            time.sleep(30)
            continue
        
        # Set initial ratio on first successful price fetch if not set
        if initial_ratio is None:
            try:
                if short_price == 0:
                    print(f"[{get_timestamp()}] ⚠️ Invalid short price (0), skipping...", flush=True)
                    time.sleep(30)
                    continue
                initial_ratio = long_price / short_price
                trigger_ratio = initial_ratio * (1 - trigger_drop_pct / 100)
                print(f"[{get_timestamp()}] ✅ Initial ratio set: {initial_ratio:.4f}, Trigger: {trigger_ratio:.4f}", flush=True)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error calculating initial ratio: {e}", flush=True)
                time.sleep(30)
                continue

        # Calculate current ratio safely
        try:
            if short_price == 0:
                print(f"[{get_timestamp()}] ⚠️ Invalid short price (0), skipping...", flush=True)
                time.sleep(30)
                continue
            ratio = long_price / short_price
        except Exception as e:
            print(f"[{get_timestamp()}] ❌ Error calculating ratio: {e}", flush=True)
            time.sleep(30)
            continue
        
        # Show current target based on scale-in progress
        if ENABLE_SCALE_IN and scale_in_executed < SCALE_IN_LEGS and len(scale_in_trigger_ratios) > scale_in_executed:
            current_target = scale_in_trigger_ratios[scale_in_executed]
            progress = f"Leg {scale_in_executed + 1}/{SCALE_IN_LEGS}"
        elif trigger_ratio is not None:
            current_target = trigger_ratio
            progress = "Full"
        else:
            current_target = "N/A"
            progress = "Calculating..."
        
        print(
            f"[{get_timestamp()}] 📊 LONG = ${long_price} | SHORT = ${short_price} | "
            f"Ratio = {ratio:.4f} | Target ≤ {current_target} ({progress})",
            flush=True
        )

        # Skip trading logic if ratios aren't set yet
        if trigger_ratio is None:
            print(f"[{get_timestamp()}] ⏳ Waiting for trigger ratio to be calculated...", flush=True)
            time.sleep(30)
            continue

        # Scale-in logic
        if ENABLE_SCALE_IN:
            # Check if we should execute next scale-in leg
            if (scale_in_executed < SCALE_IN_LEGS and 
                len(scale_in_trigger_ratios) > scale_in_executed and 
                ratio <= scale_in_trigger_ratios[scale_in_executed]):
                leg_num = scale_in_executed + 1
                print(f"[{get_timestamp()}] 🚀 Scale-in Leg {leg_num}/{SCALE_IN_LEGS} triggered! Ratio: {ratio:.4f}")

                trade_size = min(scale_in_leg_size, MAX_USD_POSITION - (scale_in_executed * scale_in_leg_size))
                if trade_size <= 0:
                    print(f"[{get_timestamp()}] ⚠️ Max position reached. Skipping leg {leg_num}.")
                    scale_in_executed = SCALE_IN_LEGS
                    continue

                long_qty = round(trade_size / long_price, 2)
                short_qty = round(trade_size / short_price, 0)
                
                # Bybit minimum order size is typically 1 USDT equivalent
                # Check if quantities are too small
                min_usd_value = 1.0
                if (long_qty * long_price) < min_usd_value or (short_qty * short_price) < min_usd_value:
                    print(f"[{get_timestamp()}] ⚠️ Leg {leg_num} quantities too small (${long_qty * long_price:.2f} and ${short_qty * short_price:.2f}). Minimum is ${min_usd_value}. Skipping leg.", flush=True)
                    scale_in_executed += 1
                    if scale_in_executed >= SCALE_IN_LEGS:
                        print(f"[{get_timestamp()}] ⚠️ All legs skipped due to minimum size requirements.", flush=True)
                        break
                    continue

                print(f"[{get_timestamp()}] 📐 Leg {leg_num} - Long qty: {long_qty} {symbol_long} | Short qty: {short_qty} {symbol_short}", flush=True)

                r1 = place_market_order(symbol_long, "Buy", long_qty)
                r2 = place_market_order(symbol_short, "Sell", short_qty)

                print(f"[{get_timestamp()}] Leg {leg_num} orders sent:")
                print(f"[{get_timestamp()}] ➡️ Long:", r1)
                print(f"[{get_timestamp()}] ⬅️ Short:", r2)
                
                # CRITICAL: Check if both orders succeeded
                long_success = r1.get("retCode") == 0
                short_success = r2.get("retCode") == 0
                
                if not (long_success and short_success):
                    print(f"[{get_timestamp()}] ⚠️⚠️⚠️ CRITICAL: Leg {leg_num} partial execution!")
                    if long_success and not short_success:
                        print(f"[{get_timestamp()}] ⚠️⚠️⚠️ Long succeeded, Short failed: {r2.get('retMsg', 'Unknown')}")
                    elif not long_success and short_success:
                        print(f"[{get_timestamp()}] ⚠️⚠️⚠️ Short succeeded, Long failed: {r1.get('retMsg', 'Unknown')}")
                    else:
                        print(f"[{get_timestamp()}] ⚠️⚠️⚠️ Both orders failed!")
                    print(f"[{get_timestamp()}] ⚠️⚠️⚠️ Stopping scale-in to prevent further unhedged positions!")
                    break
                
                print(f"[{get_timestamp()}] ✅ Leg {leg_num} both orders executed successfully!")

                scale_in_executed += 1
                total_executed = scale_in_executed * scale_in_leg_size
                print(f"[{get_timestamp()}] 📊 Progress: ${total_executed:.0f}/${usd_position_size:.0f} executed ({scale_in_executed}/{SCALE_IN_LEGS} legs)")

                # If all legs executed, exit
                if scale_in_executed >= SCALE_IN_LEGS:
                    print(f"[{get_timestamp()}] ✅ All scale-in legs completed!")
                    break
                
                # Wait a bit before checking for next leg
                time.sleep(5)
                continue

        # Original single-execution logic (if scale-in disabled)
        elif trigger_ratio is not None and ratio <= trigger_ratio:
            print(f"[{get_timestamp()}] 🚀 Trigger hit. Executing hedge...")

            trade_size = min(usd_position_size, MAX_USD_POSITION)
            if trade_size < usd_position_size:
                print(f"[{get_timestamp()}] ⚠️ Requested size clipped to ${trade_size} max.")

            long_qty = round(trade_size / long_price, 2)
            short_qty = round(trade_size / short_price, 0)
            
            # Bybit minimum order size is typically 1 USDT equivalent
            min_usd_value = 1.0
            if (long_qty * long_price) < min_usd_value or (short_qty * short_price) < min_usd_value:
                print(f"[{get_timestamp()}] ⚠️ Quantities too small (${long_qty * long_price:.2f} and ${short_qty * short_price:.2f}). Minimum is ${min_usd_value}. Skipping trade.", flush=True)
                time.sleep(30)
                continue

            print(f"[{get_timestamp()}] 📐 Long qty: {long_qty} {symbol_long} | Short qty: {short_qty} {symbol_short}", flush=True)

            r1 = place_market_order(symbol_long, "Buy", long_qty)
            r2 = place_market_order(symbol_short, "Sell", short_qty)

            print(f"[{get_timestamp()}] ⚠️ Orders sent:")
            print(f"[{get_timestamp()}] ➡️ Long:", r1)
            print(f"[{get_timestamp()}] ⬅️ Short:", r2)
            
            # CRITICAL: Check if both orders succeeded
            long_success = r1.get("retCode") == 0
            short_success = r2.get("retCode") == 0
            
            if long_success and short_success:
                print(f"[{get_timestamp()}] ✅ Both orders executed successfully!")
                break
            elif long_success and not short_success:
                print(f"[{get_timestamp()}] ⚠️⚠️⚠️ CRITICAL: Long order succeeded but Short failed!")
                print(f"[{get_timestamp()}] ⚠️⚠️⚠️ You have an UNHEDGED LONG position! Manual intervention required!")
                print(f"[{get_timestamp()}] Short error: {r2.get('retMsg', 'Unknown')}")
                # Don't exit - keep running so user can see the warning
                break
            elif not long_success and short_success:
                print(f"[{get_timestamp()}] ⚠️⚠️⚠️ CRITICAL: Short order succeeded but Long failed!")
                print(f"[{get_timestamp()}] ⚠️⚠️⚠️ You have an UNHEDGED SHORT position! Manual intervention required!")
                print(f"[{get_timestamp()}] Long error: {r1.get('retMsg', 'Unknown')}")
                # Don't exit - keep running so user can see the warning
                break
            else:
                print(f"[{get_timestamp()}] ❌ Both orders failed!")
                print(f"[{get_timestamp()}] Long error: {r1.get('retMsg', 'Unknown')}")
                print(f"[{get_timestamp()}] Short error: {r2.get('retMsg', 'Unknown')}")
                print(f"[{get_timestamp()}] No positions opened. Continuing to monitor...")
                # Continue monitoring instead of breaking
                time.sleep(30)
                continue

        time.sleep(30)

    except KeyboardInterrupt:
        print(f"[{get_timestamp()}] ⏹️ Bot stopped by user.")
        break
    except Exception as e:
        import traceback
        print(f"[{get_timestamp()}] ❌ Error: {e}", flush=True)
        print(f"[{get_timestamp()}] Traceback: {traceback.format_exc()}", flush=True)
        time.sleep(30)
