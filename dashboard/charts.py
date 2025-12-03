"""
Chart rendering utilities for terminal visualization
"""

from typing import List, Tuple, Dict


class Charts:
    """Terminal chart rendering utilities"""
    
    @staticmethod
    def bar_chart(data: List[Tuple[str, int]], width: int = 40, max_items: int = 10, show_total: bool = False) -> List[str]:
        """
        Generate ASCII bar chart with improved formatting
        
        Args:
            data: List of (label, value) tuples
            width: Maximum bar width
            max_items: Maximum number of items to display
            show_total: Whether to show total count at the end
            
        Returns:
            List of strings representing the chart
        """
        if not data:
            return ["(no data)"]

        # Sort by value descending and limit
        sorted_data = sorted(data, key=lambda x: x[1], reverse=True)[:max_items]
        max_value = max(count for _, count in sorted_data) if sorted_data else 1
        total = sum(count for _, count in data)

        lines = []
        for label, count in sorted_data:
            bar_width = int((count / max_value) * width) if max_value > 0 else 0
            bar = "█" * bar_width + "░" * (width - bar_width)
            percentage = (count / total * 100) if total > 0 else 0
            lines.append(f"{label:<18} │{bar}│ {count:>4} ({percentage:>5.1f}%)")

        if show_total and total > 0:
            lines.append("")
            lines.append(f"{'Total:':<18} {total:>4} events")

        return lines

    @staticmethod
    def line_chart(data: List[Tuple[str, int]], height: int = 10, width: int = 50, show_stats: bool = True) -> List[str]:
        """
        Generate improved ASCII line chart with axis labels and stats
        
        Args:
            data: List of (time_label, value) tuples (sorted by time)
            height: Chart height in lines
            width: Chart width in characters
            show_stats: Whether to show min/max/total stats
            
        Returns:
            List of strings representing the chart
        """
        if not data or len(data) < 2:
            return ["(insufficient data for line chart - need at least 2 data points)"]

        values = [count for _, count in data]
        max_value = max(values) if values else 1
        min_value = min(values) if values else 0
        value_range = max_value - min_value if max_value > min_value else 1
        total = sum(values)

        lines = []
        
        # Add stats header
        if show_stats:
            lines.append(f"Total Events: {total} | Max: {max_value} | Min: {min_value} | Avg: {total//len(values) if values else 0}")
            lines.append("")

        # Create grid with Y-axis labels
        chart_width = width - 8  # Reserve space for Y-axis labels
        grid = [[" " for _ in range(chart_width)] for _ in range(height)]

        # Plot points
        for i, (_, value) in enumerate(data):
            x = int((i / (len(data) - 1)) * (chart_width - 1)) if len(data) > 1 else 0
            normalized = (value - min_value) / value_range if value_range > 0 else 0
            y = int((1 - normalized) * (height - 1))
            y = max(0, min(height - 1, y))
            
            if 0 <= x < chart_width and 0 <= y < height:
                grid[y][x] = "●"

        # Draw lines between points
        for i in range(len(data) - 1):
            x1 = int((i / (len(data) - 1)) * (chart_width - 1)) if len(data) > 1 else 0
            x2 = int(((i + 1) / (len(data) - 1)) * (chart_width - 1)) if len(data) > 1 else 0
            
            v1 = values[i]
            v2 = values[i + 1]
            y1 = int((1 - (v1 - min_value) / value_range) * (height - 1)) if value_range > 0 else height - 1
            y2 = int((1 - (v2 - min_value) / value_range) * (height - 1)) if value_range > 0 else height - 1
            y1 = max(0, min(height - 1, y1))
            y2 = max(0, min(height - 1, y2))

            # Draw line
            steps = max(abs(x2 - x1), abs(y2 - y1))
            if steps > 0:
                for step in range(steps + 1):
                    t = step / steps
                    x = int(x1 + t * (x2 - x1))
                    y = int(y1 + t * (y2 - y1))
                    if 0 <= x < chart_width and 0 <= y < height:
                        if grid[y][x] == " ":
                            grid[y][x] = "─" if abs(y2 - y1) < abs(x2 - x1) else "│"

        # Convert grid to strings with Y-axis labels
        y_step = max_value / height if height > 0 else 1
        for i, row in enumerate(grid):
            y_label = int(max_value - (i * y_step))
            y_label_str = f"{y_label:>4} │"
            lines.append(y_label_str + "".join(row))

        # Add X-axis
        lines.append("     └" + "─" * chart_width)
        
        # Add time labels on X-axis (format them nicely)
        if len(data) <= 8:
            # Show all labels - build a list of formatted labels first
            formatted_labels = []
            for label, _ in data:
                # Format time label (show just hour:minute if it's a timestamp)
                if ":" in label and len(label) > 10:
                    # Extract time part - try to get hour:minute
                    if "T" in label:
                        # ISO format: 2025-01-12T10:00:00
                        time_part = label.split("T")[1][:5] if "T" in label else label[-8:][:5]
                    elif " " in label:
                        parts = label.split()
                        if len(parts) >= 2 and ":" in parts[1]:
                            time_part = parts[1][:5]  # Get HH:MM
                        else:
                            time_part = label[-8:][:5] if len(label) >= 8 else label[:5]
                    else:
                        time_part = label[-8:][:5] if len(label) >= 8 else label[:5]
                else:
                    time_part = label[:6]
                formatted_labels.append(time_part[:5])
            
            # Create label line with spacing
            label_line = "      "
            if len(data) > 0:
                step = max(1, (chart_width - 6) // len(data))
                for i, time_label in enumerate(formatted_labels):
                    pos = 6 + (i * step)
                    if pos + 5 < len(label_line) + chart_width:
                        # Extend label_line if needed
                        while len(label_line) < pos + 5:
                            label_line += " "
                        label_line = label_line[:pos] + time_label + label_line[pos+len(time_label):]
            lines.append(label_line[:6+chart_width])
        else:
            # Show first, middle, last
            first_label = data[0][0] if data else ""
            last_label = data[-1][0] if data else ""
            # Format labels
            if ":" in first_label and len(first_label) > 10:
                if "T" in first_label:
                    first_label = first_label.split("T")[1][:5] if "T" in first_label else first_label[:5]
                elif " " in first_label:
                    first_label = first_label.split()[1][:5] if " " in first_label else first_label[:5]
                else:
                    first_label = first_label[:5]
            else:
                first_label = first_label[:5]
            
            if ":" in last_label and len(last_label) > 10:
                if "T" in last_label:
                    last_label = last_label.split("T")[1][:5] if "T" in last_label else last_label[:5]
                elif " " in last_label:
                    last_label = last_label.split()[1][:5] if " " in last_label else last_label[:5]
                else:
                    last_label = last_label[:5]
            else:
                last_label = last_label[:5]
            
            lines.append(f"      {first_label:<4}" + " " * (chart_width - 12) + f"{last_label:>4}")

        return lines

    @staticmethod
    def pie_chart(data: List[Tuple[str, int]], max_items: int = 8) -> List[str]:
        """
        Generate ASCII pie chart (as bar chart alternative)
        
        Args:
            data: List of (label, value) tuples
            max_items: Maximum number of items to display
            
        Returns:
            List of strings representing the chart
        """
        # For terminal, we'll use a bar chart representation
        return Charts.bar_chart(data, width=30, max_items=max_items)

    @staticmethod
    def table(data: List[Dict], columns: List[str], max_rows: int = 20) -> List[str]:
        """
        Generate formatted table
        
        Args:
            data: List of dictionaries
            columns: List of column names to display
            max_rows: Maximum number of rows to display
            
        Returns:
            List of strings representing the table
        """
        if not data:
            return ["(no data)"]

        # Calculate column widths
        col_widths = {}
        for col in columns:
            col_widths[col] = max(
                len(str(col)),
                max(len(str(row.get(col, ""))) for row in data[:max_rows])
            )

        lines = []
        
        # Header
        header = " | ".join(str(col).ljust(col_widths[col]) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for row in data[:max_rows]:
            row_str = " | ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in columns)
            lines.append(row_str)

        if len(data) > max_rows:
            lines.append(f"... ({len(data) - max_rows} more rows)")

        return lines

