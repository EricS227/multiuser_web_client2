#!/usr/bin/env python3
"""
Test Brazilian timezone configuration
"""

from backend.models import brazilian_now
from datetime import datetime, timezone
import pytz

def test_timezone():
    print("TIMEZONE TEST")
    print("=" * 30)
    
    # Current times
    utc_time = datetime.now(timezone.utc)
    brazil_time = brazilian_now()
    
    print(f"UTC Time:    {utc_time}")
    print(f"Brazil Time: {brazil_time}")
    
    # Check difference (should be -3 hours from UTC, or -2 during daylight saving)
    time_diff = brazil_time.utcoffset().total_seconds() / 3600
    print(f"UTC Offset:  {time_diff} hours")
    
    # Check if it's working
    if time_diff in [-3, -2]:  # Brazil is UTC-3, or UTC-2 during daylight saving
        print("✓ Brazilian timezone is configured correctly!")
    else:
        print("❌ Timezone configuration issue")
    
    # Format for display
    print(f"\nFormatted Brazil time: {brazil_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"ISO format: {brazil_time.isoformat()}")

if __name__ == "__main__":
    test_timezone()