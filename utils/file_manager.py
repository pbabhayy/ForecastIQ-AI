"""
Utils: File Manager
===================
File I/O for ingestion and artifact export.

RESPONSIBILITY:
    - Read uploaded CSV/XLSX into dataframes (delegating engines).
    - Manage paths and writing of generated artifacts under exports/
      (reports, charts, forecasts).

Consumes: config.settings, config.constants, utils.logger
Pure I/O — no analytics or charts.
"""
