#!/usr/bin/env python3
"""
Email Report Generator
Generate and send usage reports to clients
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import Database
from starlink.StarlinkClient import StarlinkClient


class EmailReportGenerator:
    """Generate and send email reports"""
    
    def __init__(self, db: Database, client: StarlinkClient, dry_run: bool = False):
        self.db = db
        self.client = client
        self.dry_run = dry_run
        
        # Load SMTP settings
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_from = os.getenv('SMTP_FROM', self.smtp_user)
    
    def generate_report(self, mapping_id: int, start_date: str = None, end_date: str = None):
        """
        Generate and send report for a client mapping
        
        Args:
            mapping_id: Client mapping ID
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        """
        # Get mapping details
        mapping = self.db.get_client_mapping(mapping_id)
        if not mapping:
            raise ValueError(f"Mapping ID {mapping_id} not found")
        
        if not mapping['active']:
            raise ValueError(f"Mapping ID {mapping_id} is inactive")
        
        print(f"📊 Generating report for {mapping['client_name']}...")
        print(f"   Service Line: {mapping['service_line_id']} ({mapping['nickname']})")
        print(f"   Account: {mapping['account_number']}")
        
        # Fetch usage data
        try:
            usage_data = self.client.usage.get_live_usage_data(
                mapping['account_number'],
                service_lines=[mapping['service_line_id']],
                cycles_to_fetch=1
            )
        except Exception as e:
            error_msg = f"Failed to fetch usage data: {e}"
            print(f"❌ {error_msg}")
            self._log_report(mapping, 'failed', error_message=error_msg)
            raise
        
        # Get service line data
        sl_data = usage_data.get(mapping['service_line_id'], {})
        if not sl_data:
            error_msg = f"No usage data found for service line {mapping['service_line_id']}"
            print(f"❌ {error_msg}")
            self._log_report(mapping, 'failed', error_message=error_msg)
            raise ValueError(error_msg)
        
        # Filter by date range if provided
        daily_usage = sl_data.get('daily_usage', [])
        if start_date and end_date:
            daily_usage = [
                day for day in daily_usage
                if start_date <= day.get('date', '') <= end_date
            ]
            report_type = 'custom_range'
        else:
            report_type = 'current_cycle'
            # Get billing cycle dates from data
            if daily_usage:
                start_date = daily_usage[0].get('date')
                end_date = daily_usage[-1].get('date')
        
        # Calculate totals
        total_usage_gb = sum(day.get('total_gb', day.get('usage_gb', 0)) for day in daily_usage)
        days_included = len(daily_usage)
        
        print(f"   Date Range: {start_date} to {end_date}")
        print(f"   Total Usage: {total_usage_gb:.2f} GB over {days_included} days")
        
        # Generate HTML email
        html_content = self._format_html_email(
            mapping['client_name'],
            mapping['service_line_id'],
            mapping['nickname'],
            daily_usage,
            start_date,
            end_date,
            total_usage_gb
        )
        
        # Send email
        subject = f"Starlink Usage Report - {mapping['client_name']} ({start_date} to {end_date})"
        
        if self.dry_run:
            print("\n🔍 DRY RUN MODE - Email not sent")
            print(f"   To: {mapping['primary_email']}")
            if mapping['cc_emails']:
                print(f"   CC: {mapping['cc_emails']}")
            print(f"   Subject: {subject}")
            print(f"\n--- Email Content Preview ---")
            print(html_content[:500] + "..." if len(html_content) > 500 else html_content)
            status = 'pending'
        else:
            try:
                self._send_email(
                    to=mapping['primary_email'],
                    cc=mapping['cc_emails'].split(',') if mapping['cc_emails'] else [],
                    subject=subject,
                    html_content=html_content
                )
                print(f"✅ Email sent successfully to {mapping['primary_email']}")
                status = 'sent'
            except Exception as e:
                error_msg = f"Failed to send email: {e}"
                print(f"❌ {error_msg}")
                self._log_report(mapping, 'failed', error_message=error_msg,
                               start_date=start_date, end_date=end_date,
                               total_usage_gb=total_usage_gb, days_included=days_included,
                               report_type=report_type, email_subject=subject)
                raise
        
        # Log report
        self._log_report(
            mapping, status,
            start_date=start_date,
            end_date=end_date,
            billing_cycle_start=start_date,
            billing_cycle_end=end_date,
            total_usage_gb=total_usage_gb,
            days_included=days_included,
            report_type=report_type,
            email_subject=subject
        )
        
        # Update last_sent_at
        if status == 'sent':
            self.db.update_client_mapping(mapping_id, last_sent_at=datetime.now().isoformat())
    
    def _format_html_email(self, client_name: str, service_line_id: str, 
                          nickname: str, daily_usage: list, start_date: str, 
                          end_date: str, total_usage_gb: float) -> str:
        """Format HTML email content"""
        
        # Build daily usage table
        usage_rows = ""
        for day in daily_usage:
            date_str = day.get('date', 'N/A')
            priority_gb = day.get('priority_gb', 0)
            standard_gb = day.get('standard_gb', 0)
            total_gb = day.get('total_gb', 0)
            
            usage_rows += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{date_str}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{priority_gb:.2f} GB</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{standard_gb:.2f} GB</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;"><strong>{total_gb:.2f} GB</strong></td>
                </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #060352 0%, #0a0870 100%);
                    color: white;
                    padding: 30px 20px;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-top: none;
                }}
                .summary {{
                    background-color: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-left: 4px solid #eb6e34;
                    border-radius: 4px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background-color: white;
                    margin: 20px 0;
                }}
                th {{
                    background-color: #060352;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0 0 10px 0; font-size: 28px;">Zuba Broadband</h1>
                <h2 style="margin: 0; font-size: 20px; font-weight: normal;">Starlink Usage Report</h2>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <div class="content">
                <h2>Client Information</h2>
                <p><strong>Client Name:</strong> {client_name}</p>
                <p><strong>Service Line:</strong> {service_line_id}</p>
                <p><strong>Terminal Nickname:</strong> {nickname or 'N/A'}</p>
                
                <div class="summary">
                    <h3>Usage Summary</h3>
                    <p><strong>Reporting Period:</strong> {start_date} to {end_date}</p>
                    <p><strong>Total Days:</strong> {len(daily_usage)}</p>
                    <p><strong>Total Data Usage:</strong> <span style="font-size: 28px; color: #eb6e34; font-weight: bold;">{total_usage_gb:.2f} GB</span></p>
                </div>
                
                <h3>Daily Usage Breakdown</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th style="text-align: right;">Priority Data</th>
                            <th style="text-align: right;">Standard Data</th>
                            <th style="text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {usage_rows}
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #f0f0f0; font-weight: bold;">
                            <td style="padding: 10px;">TOTAL</td>
                            <td style="padding: 10px; text-align: right;">{sum(d.get('priority_gb', 0) for d in daily_usage):.2f} GB</td>
                            <td style="padding: 10px; text-align: right;">{sum(d.get('standard_gb', 0) for d in daily_usage):.2f} GB</td>
                            <td style="padding: 10px; text-align: right;"><strong>{total_usage_gb:.2f} GB</strong></td>
                        </tr>
                    </tfoot>
                </table>
                
                <div class="footer">
                    <p><strong>Zuba Broadband</strong> - Your Trusted Starlink Service Provider</p>
                    <p>This is an automated report. For questions or support, please contact us.</p>
                    <p style="margin-top: 10px; color: #999;">&copy; 2025 Zuba Broadband. Powered by Starlink Enterprise.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, to: str, cc: list, subject: str, html_content: str):
        """Send email via SMTP"""
        if not self.smtp_user or not self.smtp_password:
            raise ValueError("SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env")
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.smtp_from
        msg['To'] = to
        if cc:
            msg['Cc'] = ', '.join(cc)
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        recipients = [to] + cc
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg, from_addr=self.smtp_from, to_addrs=recipients)
    
    def _log_report(self, mapping: dict, status: str, **kwargs):
        """Log report to database"""
        self.db.add_report_log(
            mapping_id=mapping['id'],
            service_line_id=mapping['service_line_id'],
            recipient_email=mapping['primary_email'],
            report_type=kwargs.get('report_type', 'current_cycle'),
            status=status,
            cc_emails=mapping.get('cc_emails'),
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
            billing_cycle_start=kwargs.get('billing_cycle_start'),
            billing_cycle_end=kwargs.get('billing_cycle_end'),
            total_usage_gb=kwargs.get('total_usage_gb'),
            days_included=kwargs.get('days_included'),
            error_message=kwargs.get('error_message'),
            email_subject=kwargs.get('email_subject')
        )


def main():
    parser = argparse.ArgumentParser(
        description="Generate and send usage reports to clients",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send current billing cycle report
  python send_report.py --mapping-id 1

  # Send report for specific date range
  python send_report.py --mapping-id 1 --start-date 2025-10-13 --end-date 2025-11-09

  # Dry run (don't actually send email)
  python send_report.py --mapping-id 1 --dry-run

  # Send to all active mappings
  python send_report.py --all
        """
    )
    
    parser.add_argument(
        '--mapping-id',
        type=int,
        help='Client mapping ID to send report for'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Send reports to all active mappings'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for custom range (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for custom range (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview email without sending'
    )
    
    parser.add_argument(
        '--db',
        default='../data/starlink.db',
        help='Path to database file'
    )
    
    args = parser.parse_args()
    
    if not args.mapping_id and not args.all:
        parser.error("Either --mapping-id or --all is required")
    
    # Load environment variables
    load_dotenv()
    
    client_id = os.getenv('STARLINK_CLIENT_ID')
    client_secret = os.getenv('STARLINK_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ Error: STARLINK_CLIENT_ID and STARLINK_CLIENT_SECRET must be set in .env")
        sys.exit(1)
    
    # Initialize
    db = Database(args.db)
    client = StarlinkClient(client_id, client_secret)
    generator = EmailReportGenerator(db, client, dry_run=args.dry_run)
    
    try:
        if args.all:
            # Send to all active mappings
            mappings = db.get_client_mappings(active_only=True)
            print(f"📧 Sending reports to {len(mappings)} active mappings...\n")
            
            success = 0
            failed = 0
            
            for mapping in mappings:
                try:
                    generator.generate_report(
                        mapping['id'],
                        start_date=args.start_date,
                        end_date=args.end_date
                    )
                    success += 1
                except Exception as e:
                    print(f"❌ Failed for mapping {mapping['id']}: {e}")
                    failed += 1
                print()  # Blank line between reports
            
            print(f"\n📊 Summary: {success} sent, {failed} failed")
        else:
            # Send single report
            generator.generate_report(
                args.mapping_id,
                start_date=args.start_date,
                end_date=args.end_date
            )
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
