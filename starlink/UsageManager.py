# starlink/UsageManager.py
from typing import TYPE_CHECKING, List, Dict
import json
from datetime import datetime, date

if TYPE_CHECKING:
    from starlink.StarlinkClient import StarlinkClient

class UsageManager:
    def __init__(self, client: 'StarlinkClient'):
        self.client = client

    def get_live_usage_data(self, account_number: str, service_lines: List[str] = None, cycles_to_fetch: int = 1, target_billing_cycle: str = None) -> Dict:
        """
        Fetches live usage data from the Starlink API for the specified number of past billing cycles.
        Processes the raw data into a structured format.
        
        Args:
            account_number: Starlink account number
            service_lines: List of service line IDs to filter
            cycles_to_fetch: Number of billing cycles to fetch (default: 1 for current)
            target_billing_cycle: Specific billing cycle date in YYYY-MM-DD format (optional)
        """
        endpoint = f"/enterprise/v1/accounts/{account_number}/billing-cycles/query"
        payload = {"previousBillingCycles": cycles_to_fetch - 1, "pageLimit": 50, "pageIndex": 0}
        if service_lines:
            payload["serviceLinesFilter"] = service_lines

        api_response = self.client.post(endpoint, data=payload)
        service_lines_data = api_response.get("content", {}).get("results", [])

        if not service_lines_data:
            return {}

        processed_data = {}
        for service_line in service_lines_data:
            sl_id = service_line.get("serviceLineNumber")
            processed_data[sl_id] = {
                "total_cap_gb": 0,
                "total_consumed_gb": 0,
                "daily_usage": [],
                "billing_cycle_start_date": None,
                "billing_cycle_end_date": None
            }
            
            billing_cycles = service_line.get("billingCycles", [])
            
            # If target_billing_cycle is specified, filter to that specific cycle
            if target_billing_cycle:
                target_date = datetime.strptime(target_billing_cycle, '%Y-%m-%d').date()
                billing_cycles = [
                    cycle for cycle in billing_cycles 
                    if self._is_cycle_in_range(cycle, target_date)
                ]
            
            # Process all cycles when fetching multiple cycles, or just the first if fetching 1 cycle
            if not target_billing_cycle and cycles_to_fetch == 1 and billing_cycles:
                billing_cycles = [billing_cycles[0]]  # Only process the current/most recent cycle
            
            for cycle in billing_cycles:
                cycle_start = cycle.get('startDate', '').split('T')[0]
                cycle_end = cycle.get('endDate', '').split('T')[0]
                
                # Set billing cycle dates from the first processed cycle
                if not processed_data[sl_id]["billing_cycle_start_date"]:
                    processed_data[sl_id]["billing_cycle_start_date"] = cycle_start
                    processed_data[sl_id]["billing_cycle_end_date"] = cycle_end
                
                # For multiple cycles, we want to accumulate data, not overwrite
                # Only reset totals if this is the first cycle or if we're targeting a specific cycle
                if not processed_data[sl_id]["daily_usage"] or target_billing_cycle:
                    processed_data[sl_id]["total_cap_gb"] = 0
                    processed_data[sl_id]["total_consumed_gb"] = 0
                
                # Aggregate totals for this specific cycle
                cycle_cap = 0
                cycle_consumed = 0
                for pool in cycle.get("dataPoolUsage", []):
                    for block in pool.get("dataBlocks", []):
                        cycle_cap += block.get("totalAmountGB", 0)
                        cycle_consumed += block.get("consumedAmountGB", 0)
                
                # Add to totals (don't overwrite for multiple cycles)
                processed_data[sl_id]["total_cap_gb"] += cycle_cap
                processed_data[sl_id]["total_consumed_gb"] += cycle_consumed
                
                # Collect daily data for this cycle only, with deduplication
                daily_data_dict = {}  # Use dict to deduplicate by date
                
                # First, collect existing daily data to avoid duplicates
                for existing_daily in processed_data[sl_id]["daily_usage"]:
                    daily_data_dict[existing_daily["date"]] = {
                        "priority_gb": existing_daily.get("priority_gb", 0),
                        "standard_gb": existing_daily.get("standard_gb", 0),
                        "total_gb": existing_daily.get("total_gb", existing_daily.get("usage_gb", 0))
                    }
                
                # Then add new daily data from this cycle
                for daily in cycle.get("dailyDataUsage", []):
                    date_only_str = daily.get('date', '').split('T')[0]
                    if not date_only_str: 
                        continue
                    
                    # Fix for data top-ups: priorityGB and optInPriorityGB can contain the same data
                    # Only use optInPriorityGB if priorityGB is 0, otherwise priorityGB already includes opt-in
                    priority_gb = daily.get('priorityGB', 0)
                    optin_gb = daily.get('optInPriorityGB', 0)
                    standard_gb = daily.get('standardGB', 0)
                    nonbillable_gb = daily.get('nonBillableGB', 0)
                    
                    # If both priority and optIn have values and they're equal, it's duplicated
                    # Use the maximum of the two to avoid doubling
                    actual_priority = max(priority_gb, optin_gb)
                    
                    daily_total = actual_priority + standard_gb + nonbillable_gb
                    daily_data_dict[date_only_str] = {
                        "priority_gb": round(actual_priority, 2),
                        "standard_gb": round(standard_gb, 2),
                        "total_gb": round(daily_total, 2)
                    }
                
                # Convert back to list format
                processed_data[sl_id]["daily_usage"] = [
                    {"date": date, **usage_data} 
                    for date, usage_data in daily_data_dict.items()
                ]
        
        return processed_data

    def _is_cycle_in_range(self, cycle: Dict, target_date: date) -> bool:
        """Check if a billing cycle contains the target date."""
        try:
            start_date = datetime.strptime(cycle.get('startDate', '').split('T')[0], '%Y-%m-%d').date()
            end_date = datetime.strptime(cycle.get('endDate', '').split('T')[0], '%Y-%m-%d').date()
            return start_date <= target_date <= end_date
        except (ValueError, AttributeError):
            return False

    def archive_usage_data(self, db_conn, live_data: Dict) -> Dict[str, int]:
        """Archives daily usage data into the historical table with duplicate prevention."""
        stats = {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "missing_service_lines": 0,
        }
        with db_conn.cursor() as cur:
            for sl_id, data in live_data.items():
                # Get the database service_line_id
                cur.execute("SELECT service_line_id FROM service_lines WHERE starlink_service_line_id = %s;", (sl_id,))
                result = cur.fetchone()
                if not result:
                    print(f"⚠️ Warning: Service line {sl_id} not found in database, skipping...")
                    stats["missing_service_lines"] += 1
                    continue
                    
                service_line_db_id = result[0]
                
                for daily_data in data["daily_usage"]:
                    # Check if data already exists for this date
                    cur.execute(
                        "SELECT consumed_gb FROM daily_usage_history WHERE service_line_id = %s AND usage_date = %s;",
                        (service_line_db_id, daily_data["date"])
                    )
                    existing_data = cur.fetchone()
                    
                    if existing_data:
                        existing_gb = existing_data[0]
                        new_gb = daily_data["usage_gb"]
                        
                        # Only update if the new data is different (and log the change)
                        # Convert both to float for comparison
                        existing_gb_float = float(existing_gb)
                        new_gb_float = float(new_gb)
                        if abs(existing_gb_float - new_gb_float) > 0.01:  # Allow for small floating point differences
                            print(f"🔄 Updating usage for {sl_id} on {daily_data['date']}: {existing_gb} → {new_gb} GB")
                            cur.execute(
                                """
                                UPDATE daily_usage_history 
                                SET consumed_gb = %s 
                                WHERE service_line_id = %s AND usage_date = %s;
                                """,
                                (new_gb, service_line_db_id, daily_data["date"])
                            )
                            stats["updated"] += 1
                        else:
                            print(f"✅ Data already exists and matches for {sl_id} on {daily_data['date']}: {existing_gb} GB")
                            stats["unchanged"] += 1
                    else:
                        # Insert new data
                        print(f"📝 Inserting new usage data for {sl_id} on {daily_data['date']}: {daily_data['usage_gb']} GB")
                        cur.execute(
                            """
                            INSERT INTO daily_usage_history (service_line_id, usage_date, consumed_gb)
                            VALUES (%s, %s, %s);
                            """,
                            (service_line_db_id, daily_data["date"], daily_data["usage_gb"])
                        )
                        stats["inserted"] += 1
        
        db_conn.commit()
        print("✅ Daily usage data archived successfully with duplicate prevention.")
        print(f"   Summary → inserted: {stats['inserted']}, updated: {stats['updated']}, unchanged: {stats['unchanged']}, missing SLs: {stats['missing_service_lines']}")
        return stats