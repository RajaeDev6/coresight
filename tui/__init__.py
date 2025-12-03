"""
Custom TUI Library for CoreSight
Provides terminal UI components for building interactive dashboards
"""

from .colors import C
from .input_box import InputBox
from .table_view import TableView
from .dashboard_view import DashboardView

__all__ = ['C', 'InputBox', 'TableView', 'DashboardView']

