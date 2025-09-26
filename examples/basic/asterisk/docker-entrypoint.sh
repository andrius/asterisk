#!/bin/sh
set -e

echo "Processing Asterisk configuration templates..."

# Handle automatic IP detection
if [ "$EXTERNAL_IP" = "auto" ]; then
    echo "🔍 EXTERNAL_IP=auto detected, attempting to discover external IP..."

    # Try to detect external IP using multiple methods
    DETECTED_IP=""

    # Method 1: ipify.org
    DETECTED_IP=$(curl -s --max-time 5 https://api.ipify.org/ 2>/dev/null || echo "")

    # Method 2: httpbin.org (backup)
    if [ -z "$DETECTED_IP" ]; then
        DETECTED_IP=$(curl -s --max-time 5 https://httpbin.org/ip 2>/dev/null | grep -o '"origin":"[^"]*' | cut -d'"' -f4 | cut -d',' -f1 2>/dev/null || echo "")
    fi

    # Method 3: checkip.amazonaws.com (backup)
    if [ -z "$DETECTED_IP" ]; then
        DETECTED_IP=$(curl -s --max-time 5 https://checkip.amazonaws.com/ 2>/dev/null | tr -d '\n' || echo "")
    fi

    if [ -n "$DETECTED_IP" ]; then
        echo "✅ Detected external IP: $DETECTED_IP"
        export EXTERNAL_IP="$DETECTED_IP"
    else
        echo "❌ Could not detect external IP automatically"
        echo "⚠️  Using fallback IP: 127.0.0.1 (RTP may not work properly)"
        echo "💡 Set EXTERNAL_IP manually in .env file for proper NAT traversal"
        export EXTERNAL_IP="127.0.0.1"
    fi
else
    echo "✅ Using configured EXTERNAL_IP: $EXTERNAL_IP"
fi

# Process template files with envsubst
for template in /etc/asterisk/*.template; do
  if [ -f "$template" ]; then
    config_file="/etc/asterisk/$(basename "$template" .template)"
    echo "Processing: $(basename "$template") -> $(basename "$config_file")"
    envsubst < "$template" > "$config_file"
  fi
done

echo "Configuration processing complete!"
echo "Starting Asterisk: $*"
exec "$@"