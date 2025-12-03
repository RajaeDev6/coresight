"""
Query engine with stats functions
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .query_parser import QueryParser
from index.indexer import Indexer


class QueryEngine:
    """Search engine with SPL-like query syntax and stats"""
    
    def __init__(self, indexer: Indexer):
        """
        Initialize query engine
        
        Args:
            indexer: Indexer instance for querying logs
        """
        self.indexer = indexer
        self.parser = QueryParser()

    def search(self, query: str) -> List[Dict]:
        """
        Execute a search query
        
        Args:
            query: SPL-like query string
            
        Returns:
            List of log dictionaries or stats results
        """
        try:
            where_clause, stats_cmd = self.parser.parse(query)
            results = self.indexer.query(where_clause)
            
            if stats_cmd:
                return self._run_stats(results, stats_cmd)
            
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def _run_stats(self, results: List[Dict], stats_cmd: str) -> List[Dict]:
        """Execute stats command on results"""
        stats_cmd = stats_cmd.strip().lower()

        # count_by(field)
        match = re.match(r"count_by\((\w+)\)", stats_cmd)
        if match:
            field = match.group(1)
            return self._count_by(results, field)

        # top(n, field)
        match = re.match(r"top\((\d+),\s*(\w+)\)", stats_cmd)
        if match:
            n = int(match.group(1))
            field = match.group(2)
            return self._top(results, n, field)

        # time_bucket(interval)
        match = re.match(r"time_bucket\((\w+)\)", stats_cmd)
        if match:
            interval = match.group(1)
            return self._time_bucket(results, interval)

        # table(field1, field2, ...)
        match = re.match(r"table\(([^)]+)\)", stats_cmd)
        if match:
            fields = [f.strip() for f in match.group(1).split(",")]
            return self._table(results, fields)

        # stats count
        if stats_cmd == "stats count" or stats_cmd == "count":
            return [{"count": len(results)}]

        return [{"error": f"Unknown stats command: {stats_cmd}"}]

    def _count_by(self, results: List[Dict], field: str) -> List[Dict]:
        """Count results by field"""
        counts = {}
        for r in results:
            key = r.get(field) or "null"
            counts[key] = counts.get(key, 0) + 1

        return [{"value": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    def _top(self, results: List[Dict], n: int, field: str) -> List[Dict]:
        """Get top N values by field"""
        counts = {}
        for r in results:
            key = r.get(field) or "null"
            counts[key] = counts.get(key, 0) + 1

        top_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]
        return [{"value": k, "count": v} for k, v in top_items]

    def _time_bucket(self, results: List[Dict], interval: str) -> List[Dict]:
        """Bucket results by time interval"""
        buckets = {}
        
        for r in results:
            ts_str = r.get("timestamp")
            if not ts_str:
                continue

            try:
                # Parse timestamp
                if "T" in ts_str:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                
                # Bucket by interval
                if interval == "1m" or interval == "minute":
                    bucket_key = dt.strftime("%Y-%m-%d %H:%M:00")
                elif interval == "5m":
                    # Round to 5-minute buckets
                    minutes = (dt.minute // 5) * 5
                    bucket_key = dt.replace(minute=minutes, second=0).strftime("%Y-%m-%d %H:%M:00")
                elif interval == "1h" or interval == "hour":
                    bucket_key = dt.strftime("%Y-%m-%d %H:00:00")
                elif interval == "1d" or interval == "day":
                    bucket_key = dt.strftime("%Y-%m-%d")
                else:
                    bucket_key = dt.strftime("%Y-%m-%d %H:00:00")  # Default to hour
                
                buckets[bucket_key] = buckets.get(bucket_key, 0) + 1
            except Exception:
                continue

        return [{"time": k, "count": v} for k, v in sorted(buckets.items())]

    def _table(self, results: List[Dict], fields: List[str]) -> List[Dict]:
        """Format results as table with specified fields"""
        table_results = []
        for r in results:
            row = {}
            for field in fields:
                row[field] = r.get(field, "")
            table_results.append(row)
        return table_results

