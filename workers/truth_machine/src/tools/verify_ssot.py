"""
SSOT Verification Tool

Verifies that Web API and Telegram use the same data source
by comparing report_id fingerprints.

Usage:
    python -m src.tools.verify_ssot --platform polymarket
    python -m src.tools.verify_ssot --platform kalshi --verbose
"""

import asyncio
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def verify_ssot(platform: str, verbose: bool = False):
    """
    Verify SSOT consistency between Web API and Telegram.

    This simulates both the Web API flow and Telegram flow,
    and compares their report_id fingerprints.
    """
    from src.services.api import PolyrouterAPI
    from src.services.report_service import ReportService

    print(f"🔍 SSOT Verification for platform: {platform}")
    print("=" * 60)

    # Get Polyrouter API key
    api_key = None
    try:
        with open('.env') as f:
            for line in f:
                if line.startswith('POLYROUTER_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except FileNotFoundError:
        pass

    if not api_key:
        api_key = os.environ.get("POLYROUTER_API_KEY")

    if not api_key:
        print("❌ POLYROUTER_API_KEY not found")
        return False

    # Initialize services
    polyrouter = PolyrouterAPI(api_key)
    report_service = ReportService(polyrouter_api=polyrouter)

    try:
        # Generate report (this is what both Web and Telegram would use)
        print(f"\n1. Generating report via Polyrouter...")
        payload = await report_service.build_latest_report(
            platform_id=platform,
            limit=5,
            lang="zh",
            with_ai=False,  # Skip AI for faster testing
        )

        if not payload:
            print("❌ Failed to generate report")
            return False

        print(f"   ✅ Report generated")
        print(f"   report_id: {payload.report_id}")
        print(f"   generated_by: {payload.generated_by}")
        print(f"   updated_at: {payload.updated_at}")
        print(f"   items_count: {payload.items_count}")

        # Simulate Web API response
        print(f"\n2. Simulating Web API response...")
        web_response = payload.to_dict()
        web_report_id = web_response.get("report_id")
        print(f"   Web report_id: {web_report_id}")

        # Simulate Telegram message
        print(f"\n3. Simulating Telegram message...")
        telegram_message = report_service.format_for_telegram(payload)
        # Extract report_id from Telegram message
        tg_report_id = None
        for line in telegram_message.split('\n'):
            if 'report_id:' in line:
                tg_report_id = line.split('`')[1] if '`' in line else None
                break
        print(f"   Telegram report_id: {tg_report_id}")

        # Compare
        print(f"\n4. Comparing fingerprints...")
        if web_report_id == tg_report_id:
            print(f"   ✅ MATCH! Web and Telegram use the same data")
            print(f"   report_id: {web_report_id}")
        else:
            print(f"   ❌ MISMATCH!")
            print(f"   Web: {web_report_id}")
            print(f"   Telegram: {tg_report_id}")
            return False

        # Verify data source
        print(f"\n5. Verifying data source...")
        if payload.generated_by == "polyrouter":
            print(f"   ✅ Data source: Polyrouter (SSOT)")
        else:
            print(f"   ❌ Data source: {payload.generated_by} (NOT SSOT!)")
            return False

        if verbose:
            print(f"\n6. First 3 items:")
            for item in payload.items[:3]:
                print(f"   #{item['rank']}: {item['title'][:50]}...")

        print("\n" + "=" * 60)
        print("✅ SSOT VERIFICATION PASSED")
        print(f"   Platform: {platform}")
        print(f"   report_id: {payload.report_id}")
        print(f"   Data source: Polyrouter")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await polyrouter.close()


def main():
    parser = argparse.ArgumentParser(description="SSOT Verification Tool")
    parser.add_argument(
        "-p", "--platform",
        default="polymarket",
        help="Platform ID (polymarket, kalshi, etc.)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    args = parser.parse_args()

    success = asyncio.run(verify_ssot(args.platform, args.verbose))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
