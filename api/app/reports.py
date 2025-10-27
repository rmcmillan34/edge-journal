"""
PDF Report Generation Module

Generates multi-granularity PDF reports from trade data using WeasyPrint.
Supports trade, daily, weekly, monthly, yearly, YTD, and all-time reports.

Updated: 2025-01-25 - Fixed WeasyPrint PDF generation API call
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import calendar

from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Trade, User, DailyJournal, PlaybookResponse, Attachment, SavedView, Account


class ReportGenerator:
    """Generate PDF reports from trade data"""

    def __init__(self, db: Session, user_id: int):
        """
        Initialize report generator.

        Args:
            db: SQLAlchemy database session
            user_id: ID of the user generating the report
        """
        self.db = db
        self.user_id = user_id

        # Set up Jinja2 environment for templates
        # Use dynamic path that works in Docker (/app) and CI/local (repo root)
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "templates", "reports")

        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_trade_report(
        self,
        trade_id: int,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> tuple[bytes, str]:
        """
        Generate single trade report PDF.

        Args:
            trade_id: ID of the trade to report on
            theme: "light" or "dark" theme
            include_screenshots: Whether to include trade screenshots

        Returns:
            PDF bytes

        Raises:
            ValueError: If trade not found or doesn't belong to user
        """
        from .models import Instrument

        # Fetch the trade with account and symbol
        result = self.db.query(Trade, Instrument.symbol, Account.name).join(
            Account, Trade.account_id == Account.id
        ).outerjoin(
            Instrument, Trade.instrument_id == Instrument.id
        ).filter(
            Trade.id == trade_id,
            Account.user_id == self.user_id
        ).first()

        if not result:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Trade not found")

        trade, symbol, account_name = result

        # Attach symbol and account to trade
        class AccountStub:
            def __init__(self, name):
                self.name = name

        trade.symbol = symbol if symbol else "UNKNOWN"
        trade.account = AccountStub(account_name if account_name else "Unknown")

        # Calculate trade duration
        duration = None
        if trade.open_time_utc and trade.close_time_utc:
            delta = trade.close_time_utc - trade.open_time_utc
            hours = delta.total_seconds() / 3600
            if hours < 1:
                duration = f"{int(delta.total_seconds() / 60)} minutes"
            elif hours < 24:
                duration = f"{hours:.1f} hours"
            else:
                days = delta.days
                duration = f"{days} day{'s' if days != 1 else ''}"

        # Fetch playbook responses for this trade with template info
        from .models import PlaybookTemplate
        import json

        playbook_responses = self.db.query(PlaybookResponse).join(
            PlaybookTemplate, PlaybookResponse.template_id == PlaybookTemplate.id
        ).filter(
            PlaybookResponse.trade_id == trade_id
        ).all()

        # Parse playbook fields for display
        for response in playbook_responses:
            # Get the template to access field definitions
            template = self.db.query(PlaybookTemplate).filter(
                PlaybookTemplate.id == response.template_id
            ).first()

            response.template_name = template.name if template else "Unknown Template"

            # Parse values and comments
            values = {}
            comments = {}
            try:
                if response.values_json:
                    values = json.loads(response.values_json)
            except:
                pass

            try:
                if response.comments_json:
                    comments = json.loads(response.comments_json)
            except:
                pass

            # Build fields list for template
            response.fields = []
            if template and template.schema_json:
                try:
                    schema = json.loads(template.schema_json)
                    template_fields = schema.get('fields', [])
                    for field in template_fields:
                        field_key = field.get('key', '')
                        field_label = field.get('label', field_key)
                        field_value = values.get(field_key, '-')

                        # Format boolean values
                        if isinstance(field_value, bool):
                            field_value = 'Yes' if field_value else 'No'

                        # Format lists
                        if isinstance(field_value, list):
                            field_value = ', '.join(str(v) for v in field_value)

                        response.fields.append({
                            'label': field_label,
                            'value': str(field_value),
                            'grade': None  # Grade per field not currently stored
                        })
                except Exception as e:
                    print(f"[WARN] Failed to parse playbook template schema: {e}")
                    response.fields = []

            # Set overall grade
            response.overall_grade = response.computed_grade

        # Fetch daily journal for trade date
        journal = None
        journal_date = None
        if trade.open_time_utc:
            trade_date = trade.open_time_utc.date()
            journal = self.db.query(DailyJournal).filter(
                DailyJournal.user_id == self.user_id,
                DailyJournal.date == trade_date
            ).first()
            journal_date = trade_date.strftime('%Y-%m-%d')

        # Fetch attachments for this trade
        attachments = self.db.query(Attachment).filter(
            Attachment.trade_id == trade_id
        ).order_by(Attachment.sort_order).all()

        # Prepare attachments with embedded images
        prepared_attachments = []
        if include_screenshots:
            prepared_attachments = self._prepare_attachments_for_template(attachments)

        # Render template
        context = {
            'trade': trade,
            'duration': duration,
            'playbook_responses': playbook_responses,
            'journal': journal,
            'journal_date': journal_date,
            'attachments': prepared_attachments,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'theme': theme,
            'include_screenshots': include_screenshots,
        }

        template = self.jinja_env.get_template('trade.html')
        html_content = template.render(context)

        # Convert to PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return (pdf_bytes, "application/pdf")

    def generate_daily_report(
        self,
        report_date: date,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> tuple[bytes, str]:
        """
        Generate daily report PDF.

        Args:
            report_date: Date to report on
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark" theme
            include_screenshots: Whether to include screenshots

        Returns:
            Tuple of (bytes, content_type)
        """
        # Handle "separate" mode: generate individual PDFs per account
        if account_separation_mode == "separate":
            return self._generate_separate_account_pdfs(
                report_type="daily",
                year=report_date.year,
                report_date=report_date,
                account_ids=account_ids,
                view_id=view_id,
                theme=theme,
                include_screenshots=include_screenshots
            )

        # Fetch trades for the day
        trades = self._fetch_trades_for_period(report_date, report_date, account_ids, view_id)

        # Calculate metrics
        metrics = self.calculate_metrics(trades)

        # Generate equity chart
        equity_chart = self.generate_equity_chart_svg(trades) if trades else None

        # Group trades by account if in grouped mode
        account_groups = None
        if account_separation_mode == "grouped":
            account_groups = self._group_trades_by_account(trades)

        # Fetch daily journal entry
        journal = self.db.query(DailyJournal).filter(
            DailyJournal.user_id == self.user_id,
            DailyJournal.date == report_date
        ).first()

        # Render template
        context = {
            'report_date': report_date.strftime('%Y-%m-%d'),
            'trades': trades,
            'metrics': metrics,
            'equity_chart': equity_chart,
            'journal': journal,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'theme': theme,
            'include_screenshots': include_screenshots,
            'account_separation_mode': account_separation_mode,
            'account_groups': account_groups,
        }

        template = self.jinja_env.get_template('daily.html')
        html_content = template.render(context)

        # Convert to PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return (pdf_bytes, "application/pdf")

    def generate_weekly_report(
        self,
        year: int,
        week: int,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> tuple[bytes, str]:
        """
        Generate weekly report PDF.

        Args:
            year: Report year
            week: ISO week number (1-53)
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark" theme
            include_screenshots: Whether to include screenshots

        Returns:
            Tuple of (bytes, content_type)
        """
        # Handle "separate" mode: generate individual PDFs per account
        if account_separation_mode == "separate":
            return self._generate_separate_account_pdfs(
                report_type="weekly",
                year=year,
                week=week,
                account_ids=account_ids,
                view_id=view_id,
                theme=theme,
                include_screenshots=include_screenshots
            )

        # Calculate week start and end dates
        jan1 = date(year, 1, 1)
        week_start = jan1 + timedelta(weeks=week-1, days=-jan1.weekday())
        week_end = week_start + timedelta(days=6)

        # Fetch trades for the week
        trades = self._fetch_trades_for_period(week_start, week_end, account_ids, view_id)

        # Calculate metrics
        metrics = self.calculate_metrics(trades)

        # Generate equity chart
        equity_chart = self.generate_equity_chart_svg(trades) if trades else None

        # Group trades by account if in grouped mode
        account_groups = None
        if account_separation_mode == "grouped":
            account_groups = self._group_trades_by_account(trades)

        # Group trades by day
        daily_breakdown = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            day_trades = [t for t in trades if t.open_time_utc.date() == current_date]
            day_pnl = sum(t.net_pnl or 0 for t in day_trades)

            daily_breakdown.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'weekday': current_date.strftime('%A'),
                'trade_count': len(day_trades),
                'pnl': day_pnl,
                'trades': day_trades
            })

        # Render template
        context = {
            'year': year,
            'week_number': week,
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': week_end.strftime('%Y-%m-%d'),
            'trades': trades,
            'metrics': metrics,
            'equity_chart': equity_chart,
            'daily_breakdown': daily_breakdown,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'theme': theme,
            'include_screenshots': include_screenshots,
            'account_separation_mode': account_separation_mode,
            'account_groups': account_groups,
        }

        template = self.jinja_env.get_template('weekly.html')
        html_content = template.render(context)

        # Convert to PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return (pdf_bytes, "application/pdf")

    def generate_monthly_report(
        self,
        year: int,
        month: int,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> tuple[bytes, str]:
        """
        Generate monthly report with hierarchical breakdown.

        Args:
            year: Report year
            month: Report month (1-12)
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts:
                - "combined": Merge all accounts together
                - "grouped": Show combined overview + per-account sections
                - "separate": Generate separate PDF per account (handled at router level)
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark" theme
            include_screenshots: Whether to include trade screenshots

        Returns:
            PDF bytes

        Structure:
            - Cover page
            - Executive summary (month KPIs, equity curve, calendar)
            - Week-by-week breakdown
            - Day-by-day breakdown within each week
            - Trade-by-trade details
            - Screenshot appendix (if >2 screenshots per trade)

        Raises:
            ValueError: If invalid month/year or separation mode
        """
        # Validate inputs
        if not (1 <= month <= 12):
            raise ValueError(f"Invalid month: {month}. Must be 1-12.")
        if year < 2000 or year > 2100:
            raise ValueError(f"Invalid year: {year}. Must be between 2000-2100.")
        if account_separation_mode not in ["combined", "grouped", "separate"]:
            raise ValueError(f"Invalid separation mode: {account_separation_mode}")

        # Handle "separate" mode: generate individual PDFs per account
        if account_separation_mode == "separate":
            return self._generate_separate_account_pdfs(
                report_type="monthly",
                year=year,
                month=month,
                account_ids=account_ids,
                view_id=view_id,
                theme=theme,
                include_screenshots=include_screenshots
            )

        # Fetch trades for the month
        trades = self._fetch_trades_for_period(
            start_date=date(year, month, 1),
            end_date=self._get_month_end_date(year, month),
            account_ids=account_ids,
            view_id=view_id
        )

        # Calculate metrics
        metrics = self.calculate_metrics(trades)

        # Generate equity chart SVG
        equity_chart_svg = self.generate_equity_chart_svg(trades)

        # Generate calendar HTML
        calendar_html = self.generate_calendar_html(year, month, trades)

        # Group trades by account if in grouped mode
        account_groups = None
        if account_separation_mode == "grouped":
            account_groups = self._group_trades_by_account(trades)

        # Fetch and prepare attachments if screenshots are included
        trade_attachments = {}
        if include_screenshots and trades:
            trade_ids = [t.id for t in trades]
            attachments = self.db.query(Attachment).filter(
                Attachment.trade_id.in_(trade_ids)
            ).order_by(Attachment.trade_id, Attachment.sort_order).all()

            # Group attachments by trade_id
            from collections import defaultdict
            att_by_trade = defaultdict(list)
            for att in attachments:
                att_by_trade[att.trade_id].append(att)

            # Prepare attachments with embedded images
            for trade_id, atts in att_by_trade.items():
                trade_attachments[trade_id] = self._prepare_attachments_for_template(atts)

        # Prepare template context
        context = {
            'year': year,
            'month': month,
            'month_name': self._get_month_name(month),
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'metrics': metrics,
            'equity_chart': equity_chart_svg,
            'calendar_html': calendar_html,
            'trades': trades,
            'theme': theme,
            'include_screenshots': include_screenshots,
            'account_separation_mode': account_separation_mode,
            'account_groups': account_groups,
            'trade_attachments': trade_attachments,
        }

        # Render HTML from Jinja2 template
        template = self.jinja_env.get_template('monthly.html')
        html_content = template.render(context)

        # Convert HTML to PDF using WeasyPrint
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return (pdf_bytes, "application/pdf")

    def generate_yearly_report(
        self,
        year: int,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light"
    ) -> bytes:
        """
        Generate yearly report PDF.

        Args:
            year: Report year
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark" theme

        Returns:
            PDF bytes
        """
        # Fetch trades for the year
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        trades = self._fetch_trades_for_period(year_start, year_end, account_ids, view_id)

        # Calculate metrics
        metrics = self.calculate_metrics(trades)

        # Generate equity chart
        equity_chart = self.generate_equity_chart_svg(trades) if trades else None

        # Group trades by account if in grouped mode
        account_groups = None
        if account_separation_mode == "grouped":
            account_groups = self._group_trades_by_account(trades)

        # Group trades by month
        monthly_breakdown = []
        for month in range(1, 13):
            month_start = date(year, month, 1)
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)

            month_trades = [t for t in trades if month_start <= t.open_time_utc.date() <= month_end]
            month_metrics = self.calculate_metrics(month_trades)

            monthly_breakdown.append({
                'name': month_start.strftime('%B'),
                'trade_count': len(month_trades),
                'win_rate': month_metrics['win_rate'],
                'pnl': month_metrics['total_pnl']
            })

        # Calculate best/worst months
        monthly_pnls = [m['pnl'] for m in monthly_breakdown if m['trade_count'] > 0]
        metrics['best_month_pnl'] = max(monthly_pnls) if monthly_pnls else 0
        metrics['worst_month_pnl'] = min(monthly_pnls) if monthly_pnls else 0

        # Render template
        context = {
            'year': year,
            'trades': trades,
            'metrics': metrics,
            'equity_chart': equity_chart,
            'monthly_breakdown': monthly_breakdown,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'theme': theme,
            'account_separation_mode': account_separation_mode,
            'account_groups': account_groups,
        }

        template = self.jinja_env.get_template('yearly.html')
        html_content = template.render(context)

        # Convert to PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return (pdf_bytes, "application/pdf")

    def generate_ytd_report(
        self,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light"
    ) -> bytes:
        """
        Generate year-to-date report PDF.

        Args:
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark" theme

        Returns:
            PDF bytes
        """
        # YTD is just the current year up to today
        current_year = datetime.utcnow().year
        return self.generate_yearly_report(
            year=current_year,
            account_ids=account_ids,
            account_separation_mode=account_separation_mode,
            view_id=view_id,
            theme=theme
        )

    def generate_alltime_report(
        self,
        account_ids: Optional[List[int]] = None,
        account_separation_mode: str = "combined",
        view_id: Optional[int] = None,
        theme: str = "light"
    ) -> bytes:
        """
        Generate all-time report PDF.

        Args:
            account_ids: List of account IDs to include (None = all accounts)
            account_separation_mode: How to display multiple accounts
            view_id: Optional saved view ID to apply filters
            theme: "light" or "dark" theme

        Returns:
            PDF bytes
        """
        # Fetch ALL trades for user (no date filter, just use a very wide range)
        # Get first and last trade dates
        from sqlalchemy import func as sqlfunc

        query = self.db.query(
            sqlfunc.min(Trade.open_time_utc).label('first_trade'),
            sqlfunc.max(Trade.open_time_utc).label('last_trade')
        ).join(Account, Trade.account_id == Account.id).filter(
            Account.user_id == self.user_id
        )

        if account_ids:
            query = query.filter(Trade.account_id.in_(account_ids))

        result = query.first()

        if not result.first_trade:
            # No trades at all
            start_date = date.today()
            end_date = date.today()
        else:
            start_date = result.first_trade.date()
            end_date = result.last_trade.date()

        # Fetch all trades
        trades = self._fetch_trades_for_period(start_date, end_date, account_ids, view_id)

        # Calculate metrics
        metrics = self.calculate_metrics(trades)

        # Generate equity chart
        equity_chart = self.generate_equity_chart_svg(trades) if trades else None

        # Calculate days traded
        unique_days = set(t.open_time_utc.date() for t in trades)
        metrics['days_traded'] = len(unique_days)

        # Calculate winning/losing days
        daily_pnls = {}
        for trade in trades:
            day = trade.open_time_utc.date()
            daily_pnls[day] = daily_pnls.get(day, 0) + (trade.net_pnl or 0)

        metrics['winning_days'] = sum(1 for pnl in daily_pnls.values() if pnl > 0)
        metrics['losing_days'] = sum(1 for pnl in daily_pnls.values() if pnl < 0)

        # Top performing symbols
        from collections import defaultdict
        symbol_stats = defaultdict(lambda: {'trades': [], 'pnl': 0})
        for trade in trades:
            symbol_stats[trade.symbol]['trades'].append(trade)
            symbol_stats[trade.symbol]['pnl'] += trade.net_pnl or 0

        top_symbols = []
        for symbol, data in sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)[:10]:
            symbol_metrics = self.calculate_metrics(data['trades'])
            top_symbols.append({
                'symbol': symbol,
                'trade_count': len(data['trades']),
                'win_rate': symbol_metrics['win_rate'],
                'pnl': data['pnl']
            })

        # Yearly breakdown
        yearly_stats = defaultdict(list)
        for trade in trades:
            yearly_stats[trade.open_time_utc.year].append(trade)

        yearly_breakdown = []
        for year in sorted(yearly_stats.keys()):
            year_trades = yearly_stats[year]
            year_metrics = self.calculate_metrics(year_trades)
            yearly_breakdown.append({
                'year': year,
                'trade_count': len(year_trades),
                'win_rate': year_metrics['win_rate'],
                'pnl': year_metrics['total_pnl']
            })

        # Group trades by account if in grouped mode
        account_groups = None
        if account_separation_mode == "grouped":
            account_groups = self._group_trades_by_account(trades)

        # Render template
        context = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'trades': trades,
            'metrics': metrics,
            'equity_chart': equity_chart,
            'top_symbols': top_symbols,
            'yearly_breakdown': yearly_breakdown,
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            'theme': theme,
            'account_separation_mode': account_separation_mode,
            'account_groups': account_groups,
        }

        template = self.jinja_env.get_template('alltime.html')
        html_content = template.render(context)

        # Convert to PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return (pdf_bytes, "application/pdf")

    def _generate_separate_account_pdfs(
        self,
        report_type: str,
        year: int,
        month: int = None,
        week: int = None,
        report_date: date = None,
        account_ids: Optional[List[int]] = None,
        view_id: Optional[int] = None,
        theme: str = "light",
        include_screenshots: bool = True
    ) -> tuple[bytes, str]:
        """
        Generate separate PDF reports for each account and package as ZIP.

        Args:
            report_type: Type of report ("monthly", "weekly", "daily", etc.)
            year: Report year
            month: Report month (for monthly reports)
            week: Week number (for weekly reports)
            report_date: Date (for daily reports)
            account_ids: List of account IDs (None = all accounts)
            view_id: Optional saved view ID
            theme: "light" or "dark"
            include_screenshots: Whether to include screenshots

        Returns:
            Tuple of (zip_bytes, "application/zip")
        """
        import io
        import zipfile

        # Get all accounts for the user (filter by account_ids if provided)
        query = self.db.query(Account).filter(Account.user_id == self.user_id)
        if account_ids:
            query = query.filter(Account.id.in_(account_ids))
        accounts = query.all()

        if not accounts:
            raise ValueError("No accounts found for the specified filters")

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for account in accounts:
                # Generate report for this specific account
                if report_type == "monthly":
                    pdf_bytes, _ = self.generate_monthly_report(
                        year=year,
                        month=month,
                        account_ids=[account.id],
                        account_separation_mode="combined",  # Use combined mode for individual account
                        view_id=view_id,
                        theme=theme,
                        include_screenshots=include_screenshots
                    )
                    filename = f"{account.name}_{year}_{month:02d}_monthly.pdf"

                elif report_type == "weekly":
                    pdf_bytes, _ = self.generate_weekly_report(
                        year=year,
                        week=week,
                        account_ids=[account.id],
                        account_separation_mode="combined",
                        view_id=view_id,
                        theme=theme,
                        include_screenshots=include_screenshots
                    )
                    filename = f"{account.name}_{year}_W{week:02d}_weekly.pdf"

                elif report_type == "daily":
                    pdf_bytes, _ = self.generate_daily_report(
                        report_date=report_date,
                        account_ids=[account.id],
                        account_separation_mode="combined",
                        view_id=view_id,
                        theme=theme,
                        include_screenshots=include_screenshots
                    )
                    filename = f"{account.name}_{report_date.strftime('%Y-%m-%d')}_daily.pdf"

                else:
                    raise ValueError(f"Unsupported report type for separate mode: {report_type}")

                # Sanitize filename (remove invalid characters)
                filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

                # Add PDF to ZIP
                zip_file.writestr(filename, pdf_bytes)

        zip_buffer.seek(0)
        return (zip_buffer.getvalue(), "application/zip")

    # ========== Helper Methods ==========

    def _fetch_trades_for_period(
        self,
        start_date: date,
        end_date: date,
        account_ids: Optional[List[int]] = None,
        view_id: Optional[int] = None
    ) -> List[Trade]:
        """
        Fetch trades for a given period, honoring account and view filters.

        Args:
            start_date: Period start date (inclusive)
            end_date: Period end date (inclusive)
            account_ids: List of account IDs to filter by (None = all accounts)
            view_id: Optional saved view ID to apply additional filters

        Returns:
            List of Trade objects sorted by open_time_utc
        """
        # Join with Account to filter by user_id (Trade doesn't have user_id directly)
        # Also join with Instrument to get symbol
        from .models import Instrument, SavedView
        from .filters import FilterCompiler
        import json

        # Query trades with symbol from instrument and account name
        query = self.db.query(Trade, Instrument.symbol, Account.name).join(
            Account, Trade.account_id == Account.id
        ).outerjoin(
            Instrument, Trade.instrument_id == Instrument.id
        ).filter(
            Account.user_id == self.user_id,
            func.date(Trade.open_time_utc) >= start_date,
            func.date(Trade.open_time_utc) <= end_date
        )

        # Apply account filter if specified
        if account_ids:
            query = query.filter(Trade.account_id.in_(account_ids))

        # Apply saved view filters if specified
        if view_id:
            saved_view = self.db.query(SavedView).filter(
                SavedView.id == view_id,
                SavedView.user_id == self.user_id
            ).first()

            if saved_view and saved_view.filters_json:
                try:
                    filter_dsl = json.loads(saved_view.filters_json)
                    compiler = FilterCompiler(self.user_id)
                    query = compiler.compile(filter_dsl, query)
                except (json.JSONDecodeError, Exception) as e:
                    # If filter parsing fails, log and continue without filters
                    print(f"[WARN] Failed to apply saved view filters: {e}")

        # Fetch results and attach symbol and account to trade objects
        results = query.order_by(Trade.open_time_utc).all()
        trades = []

        # Create a simple Account stub class for templates
        class AccountStub:
            def __init__(self, name):
                self.name = name

        for trade, symbol, account_name in results:
            # Attach symbol attribute
            trade.symbol = symbol if symbol else "UNKNOWN"
            # Attach account stub for template access
            trade.account = AccountStub(account_name if account_name else "Unknown")
            trades.append(trade)

        return trades

    def calculate_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """
        Calculate performance metrics from trades.

        Args:
            trades: List of Trade objects

        Returns:
            Dictionary containing:
                - total_pnl: Sum of all net_pnl
                - total_trades: Count of trades
                - winning_trades: Count where net_pnl > 0
                - losing_trades: Count where net_pnl < 0
                - win_rate: winning_trades / total_trades (0-1)
                - avg_win: Average of positive pnl trades
                - avg_loss: Average of negative pnl trades (absolute value)
                - profit_factor: sum(wins) / abs(sum(losses))
                - largest_win: Max net_pnl
                - largest_loss: Min net_pnl
                - avg_pnl_per_trade: total_pnl / total_trades
        """
        if not trades:
            return {
                "total_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_pnl_per_trade": 0.0,
            }

        # Extract PnL values, handling None and Decimal types
        pnl_values = []
        for trade in trades:
            if trade.net_pnl is not None:
                pnl = float(trade.net_pnl) if isinstance(trade.net_pnl, Decimal) else trade.net_pnl
                pnl_values.append(pnl)

        # If no valid PnL values, return zeros
        if not pnl_values:
            return {
                "total_pnl": 0.0,
                "total_trades": len(trades),
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "avg_pnl_per_trade": 0.0,
            }

        # Separate wins and losses
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]

        total_pnl = sum(pnl_values)
        total_trades = len(pnl_values)
        winning_trades = len(wins)
        losing_trades = len(losses)

        # Calculate averages
        avg_win = sum(wins) / winning_trades if winning_trades > 0 else 0.0
        avg_loss = abs(sum(losses) / losing_trades) if losing_trades > 0 else 0.0

        # Calculate profit factor
        sum_wins = sum(wins) if wins else 0.0
        sum_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = sum_wins / sum_losses if sum_losses > 0 else 0.0

        return {
            "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(winning_trades / total_trades, 4) if total_trades > 0 else 0.0,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "largest_win": round(max(pnl_values), 2) if pnl_values else 0.0,
            "largest_loss": round(min(pnl_values), 2) if pnl_values else 0.0,
            "avg_pnl_per_trade": round(total_pnl / total_trades, 2) if total_trades > 0 else 0.0,
        }

    def generate_equity_chart_svg(self, trades: List[Trade]) -> str:
        """
        Generate equity curve as SVG using matplotlib.

        Args:
            trades: List of Trade objects sorted by open_time_utc

        Returns:
            SVG string with data URI for embedding in HTML
        """
        # Import matplotlib here to avoid import errors during testing
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import io
            import base64
        except ImportError:
            # Return empty string if matplotlib not available
            return ""

        if not trades:
            return ""

        # Build equity curve with dates
        dates = []
        equity = []
        cumulative_pnl = 0.0

        for trade in trades:
            if trade.net_pnl is not None and trade.open_time_utc:
                pnl = float(trade.net_pnl) if isinstance(trade.net_pnl, Decimal) else trade.net_pnl
                cumulative_pnl += pnl
                dates.append(trade.open_time_utc)
                equity.append(cumulative_pnl)

        if not dates:
            return ""

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(dates, equity, color='#2563eb', linewidth=2)
        ax.fill_between(dates, equity, 0, alpha=0.1, color='#2563eb')
        ax.set_xlabel('Date')
        ax.set_ylabel('Equity ($)')
        ax.set_title('Equity Curve')
        ax.grid(True, alpha=0.3)

        # Add zero line
        ax.axhline(y=0, color='#666', linestyle='--', linewidth=1, alpha=0.5)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        fig.autofmt_xdate()

        # Convert to SVG
        buf = io.BytesIO()
        fig.savefig(buf, format='svg', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        svg_data = buf.read()

        # Encode as base64 data URI
        svg_base64 = base64.b64encode(svg_data).decode('utf-8')
        return f"data:image/svg+xml;base64,{svg_base64}"

    def generate_calendar_html(self, year: int, month: int, trades: List[Trade]) -> str:
        """
        Generate HTML calendar heatmap for a month.

        Args:
            year: Year
            month: Month (1-12)
            trades: List of Trade objects for the month

        Returns:
            HTML string with calendar table
        """
        # Calculate daily P&L
        daily_pnl = {}
        daily_trade_count = {}
        for trade in trades:
            day = trade.open_time_utc.date()
            daily_pnl[day] = daily_pnl.get(day, 0) + (trade.net_pnl or 0)
            daily_trade_count[day] = daily_trade_count.get(day, 0) + 1

        # Get month info
        month_start = date(year, month, 1)
        num_days = calendar.monthrange(year, month)[1]
        first_weekday = month_start.weekday()  # 0 = Monday

        # Build calendar HTML
        html = ['<table class="calendar-table">']
        html.append('<thead><tr>')
        html.append('<th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th>')
        html.append('</tr></thead>')
        html.append('<tbody>')

        # Start first week
        html.append('<tr>')

        # Add empty cells before first day
        for _ in range(first_weekday):
            html.append('<td class="empty"></td>')

        # Add days
        current_weekday = first_weekday
        for day_num in range(1, num_days + 1):
            current_date = date(year, month, day_num)
            pnl = daily_pnl.get(current_date, 0)
            trade_count = daily_trade_count.get(current_date, 0)

            # Determine cell class based on P&L
            cell_class = 'calendar-day'
            if trade_count > 0:
                if pnl > 0:
                    cell_class += ' positive'
                elif pnl < 0:
                    cell_class += ' negative'
                else:
                    cell_class += ' neutral'

            html.append(f'<td class="{cell_class}">')
            html.append(f'<div class="day-number">{day_num}</div>')
            if trade_count > 0:
                html.append(f'<div class="day-pnl">${pnl:.0f}</div>')
                html.append(f'<div class="day-trades">{trade_count} trade{"s" if trade_count != 1 else ""}</div>')
            html.append('</td>')

            # Start new row on Sunday
            current_weekday += 1
            if current_weekday % 7 == 0 and day_num < num_days:
                html.append('</tr><tr>')

        # Fill remaining cells in last week
        remaining = (7 - (current_weekday % 7)) % 7
        for _ in range(remaining):
            html.append('<td class="empty"></td>')

        html.append('</tr>')
        html.append('</tbody>')
        html.append('</table>')

        return ''.join(html)

    def _get_month_end_date(self, year: int, month: int) -> date:
        """
        Get the last day of a given month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Last date of the month
        """
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)

    def _get_month_name(self, month: int) -> str:
        """
        Get month name from month number.

        Args:
            month: Month number (1-12)

        Returns:
            Full month name (e.g., "January")
        """
        return calendar.month_name[month]

    def _group_trades_by_account(self, trades: List[Trade]) -> List[dict]:
        """
        Group trades by account and calculate per-account metrics.

        Args:
            trades: List of Trade objects with attached account attribute

        Returns:
            List of dictionaries with:
                - account_name: str
                - trades: List[Trade]
                - metrics: dict (same format as calculate_metrics output)
        """
        from collections import defaultdict

        # Group trades by account name
        account_trades = defaultdict(list)
        for trade in trades:
            account_name = trade.account.name if hasattr(trade, 'account') and trade.account else "Unknown"
            account_trades[account_name].append(trade)

        # Build account groups with metrics
        account_groups = []
        for account_name in sorted(account_trades.keys()):
            account_trade_list = account_trades[account_name]
            account_metrics = self.calculate_metrics(account_trade_list)

            account_groups.append({
                'account_name': account_name,
                'trades': account_trade_list,
                'metrics': account_metrics,
            })

        return account_groups

    def _encode_image_to_data_uri(self, file_path: str, mime_type: str = None) -> str:
        """
        Encode image file to base64 data URI for embedding in HTML/PDF.

        Args:
            file_path: Path to image file
            mime_type: MIME type of the image (optional, will be detected)

        Returns:
            Data URI string (e.g., "data:image/png;base64,...")
        """
        import os
        import base64
        import mimetypes

        # Check if file exists, handle permission errors gracefully (e.g., in CI)
        try:
            if not os.path.exists(file_path):
                return ""
        except (PermissionError, OSError):
            return ""

        # Detect MIME type if not provided
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = 'image/png'  # Default fallback

        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()

            encoded = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            print(f"[WARN] Failed to encode image {file_path}: {e}")
            return ""

    def _prepare_attachments_for_template(self, attachments: List[Attachment]) -> List[dict]:
        """
        Prepare attachments for template rendering with embedded images.

        Args:
            attachments: List of Attachment objects

        Returns:
            List of dicts with attachment metadata and embedded image data
        """
        prepared = []
        for att in attachments:
            att_dict = {
                'id': att.id,
                'filename': att.filename,
                'mime_type': att.mime_type,
                'caption': att.caption or '',
                'timeframe': att.timeframe or '',
                'state': att.state or '',
                'view': att.view or '',
                'is_image': att.mime_type and att.mime_type.startswith('image/') if att.mime_type else False,
                'data_uri': ''
            }

            # Embed image as data URI if it's an image
            if att_dict['is_image'] and att.storage_path:
                att_dict['data_uri'] = self._encode_image_to_data_uri(att.storage_path, att.mime_type)

            prepared.append(att_dict)

        return prepared

    def _format_currency(self, value: float) -> str:
        """Format value as currency."""
        return f"${value:,.2f}"

    def _format_percent(self, value: float) -> str:
        """Format value as percentage (expects 0-1 range)."""
        return f"{value * 100:.1f}%"

    def _format_date(self, dt: datetime) -> str:
        """Format datetime as YYYY-MM-DD HH:MM."""
        return dt.strftime("%Y-%m-%d %H:%M")
