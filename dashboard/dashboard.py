"""
Dashboard builder for creating analytics dashboards
"""

from typing import List, Dict
from .charts import Charts
from search.query_engine import QueryEngine


class Dashboard:
    """Dashboard builder for log analytics"""
    
    def __init__(self, query_engine: QueryEngine):
        """
        Initialize dashboard
        
        Args:
            query_engine: QueryEngine instance for running queries
        """
        self.query_engine = query_engine
        self.charts = Charts()

    def build_http_status_dashboard(self) -> Dict[str, List[str]]:
        """Build HTTP status code dashboard from access logs"""
        results = self.query_engine.search('log_type=access | count_by(status)')
        
        content = [
            "═══════════════════════════════════════════════════════",
            "  HTTP Status Code Distribution",
            "═══════════════════════════════════════════════════════",
            "",
            "Description: Shows the count of each HTTP status code",
            "             from web access logs (200, 404, 500, etc.)",
            ""
        ]
        
        if results and "error" not in results[0]:
            status_data = [(str(r.get("value", "")), r.get("count", 0)) for r in results]
            chart_lines = self.charts.bar_chart(status_data, width=35, show_total=True)
            content.extend(chart_lines)
        else:
            content.append("(no access log data available)")
        
        return {
            "title": "HTTP Status Codes",
            "content": content
        }

    def build_events_over_time(self) -> Dict[str, List[str]]:
        """Build events over time line chart"""
        # Get all logs and bucket by hour
        results = self.query_engine.search('* | time_bucket(1h)')
        
        content = [
            "═══════════════════════════════════════════════════════",
            "  Events Over Time (Hourly Distribution)",
            "═══════════════════════════════════════════════════════",
            "",
            "Description: Shows the number of log events per hour.",
            "             X-axis = Time (hours), Y-axis = Event count",
            "             Useful for identifying traffic patterns and",
            "             peak activity periods.",
            ""
        ]
        
        if results and "error" not in results[0] and len(results) >= 2:
            # Sort by time to ensure chronological order
            time_data = sorted([(r.get("time", ""), r.get("count", 0)) for r in results], 
                             key=lambda x: x[0])
            chart_lines = self.charts.line_chart(time_data, height=10, width=60, show_stats=True)
            content.extend(chart_lines)
            content.append("")
            content.append("Note: Chart shows log events grouped by hour intervals")
        else:
            content.append("(insufficient data - need at least 2 time buckets)")
            content.append("Ingest more logs to see time-based patterns")
        
        return {
            "title": "Events Over Time",
            "content": content
        }

    def build_top_ips(self) -> Dict[str, List[str]]:
        """Build top IP addresses dashboard"""
        results = self.query_engine.search('* | top(10, ip)')
        
        content = [
            "═══════════════════════════════════════════════════════",
            "  Top 10 IP Addresses by Request Count",
            "═══════════════════════════════════════════════════════",
            "",
            "Description: Shows the most active IP addresses in your logs.",
            "             Useful for identifying top clients, potential",
            "             attackers, or traffic sources.",
            ""
        ]
        
        if results and "error" not in results[0]:
            ip_data = [(str(r.get("value", "")), r.get("count", 0)) for r in results if r.get("value")]
            if ip_data:
                chart_lines = self.charts.bar_chart(ip_data, width=35, show_total=True)
                content.extend(chart_lines)
            else:
                content.append("(no IP addresses found in logs)")
        else:
            content.append("(no data available)")
        
        return {
            "title": "Top IP Addresses",
            "content": content
        }

    def build_failed_logins(self) -> Dict[str, List[str]]:
        """Build failed login attempts by user"""
        results = self.query_engine.search('action=login_failure | count_by(user)')
        
        content = [
            "═══════════════════════════════════════════════════════",
            "  Failed Login Attempts by User",
            "═══════════════════════════════════════════════════════",
            "",
            "Description: Shows which users have the most failed login",
            "             attempts. High counts may indicate brute-force",
            "             attacks or account compromise attempts.",
            ""
        ]
        
        if results and "error" not in results[0]:
            user_data = [(str(r.get("value", "")), r.get("count", 0)) for r in results]
            if user_data:
                chart_lines = self.charts.bar_chart(user_data, width=35, show_total=True)
                content.extend(chart_lines)
            else:
                content.append("(no failed login data found)")
        else:
            content.append("(no failed login attempts in logs)")
        
        return {
            "title": "Failed Login Attempts",
            "content": content
        }

    def build_logs_per_service(self) -> Dict[str, List[str]]:
        """Build logs per service dashboard (syslog)"""
        results = self.query_engine.search('log_type=syslog | count_by(service)')
        
        content = [
            "═══════════════════════════════════════════════════════",
            "  Syslog Events by Service",
            "═══════════════════════════════════════════════════════",
            "",
            "Description: Shows which system services are generating",
            "             the most log events. Helps identify active",
            "             services and potential issues.",
            ""
        ]
        
        if results and "error" not in results[0]:
            service_data = [(str(r.get("value", "")), r.get("count", 0)) for r in results]
            if service_data:
                chart_lines = self.charts.bar_chart(service_data, width=35, max_items=10, show_total=True)
                content.extend(chart_lines)
            else:
                content.append("(no service data found)")
        else:
            content.append("(no syslog data available)")
        
        return {
            "title": "Logs per Service",
            "content": content
        }

    def build_all_dashboards(self) -> Dict[str, Dict[str, List[str]]]:
        """Build all dashboards"""
        return {
            "HTTP Status Codes": self.build_http_status_dashboard(),
            "Events Over Time": self.build_events_over_time(),
            "Top IPs": self.build_top_ips(),
            "Failed Logins": self.build_failed_logins(),
            "Logs per Service": self.build_logs_per_service()
        }

