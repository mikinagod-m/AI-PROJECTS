from openpyxl import Workbook


def write_stkavail(path, rows):
    """rows: list of (part, phys, free=0)"""
    wb = Workbook()
    ws = wb.active
    ws.title = "stkavail.new2"
    ws.append(["LINE", "Mach", "Op Code", "Part Number", "Product Description", "Phys Stock", "Free Stock"])
    for part, phys, free in rows:
        ws.append(["PCH1", "", "", part, part, phys, free])
    wb.save(path)


def write_fcast(path, weeks, rows, sheet="fcastbydate"):
    """rows: list of (part, list of qty aligned to weeks)"""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(["Line", "Part Number", "Product Description", *weeks])
    for part, qtys in rows:
        ws.append(["PCH1", part, part, *qtys])
    wb.save(path)


def write_wo(path, weeks, rows, before_values=None, date_qty_cells=None):
    """date_qty_cells: list of (row_idx_1based_data, week_index, datetime) to plant serial bugs"""
    wb = Workbook()
    ws = wb.active
    ws.title = "wo.replen"
    ws.append(["Line", "Part Number", "Product Description", "Before", *weeks])
    for i, (part, qtys) in enumerate(rows):
        before = (before_values or [None] * len(rows))[i]
        ws.append(["PCH1", part, part, before, *qtys])
    if date_qty_cells:
        for data_row, week_i, dt in date_qty_cells:
            # data starts at Excel row 2; week columns start at E (5)
            ws.cell(data_row, 5 + week_i, dt)
    wb.save(path)


def write_three_sheet_book(path, weeks, stk_rows, fcast_rows, wo_rows):
    """One workbook with stkavail.new2, fcastbydate, and wo.replen."""
    wb = Workbook()
    ws = wb.active
    ws.title = "stkavail.new2"
    ws.append(["LINE", "Mach", "Op Code", "Part Number", "Product Description", "Phys Stock", "Free Stock"])
    for part, phys, free in stk_rows:
        ws.append(["PCH1", "", "", part, part, phys, free])
    wf = wb.create_sheet("fcastbydate")
    wf.append(["Line", "Part Number", "Product Description", *weeks])
    for part, qtys in fcast_rows:
        wf.append(["PCH1", part, part, *qtys])
    ww = wb.create_sheet("wo.replen")
    ww.append(["Line", "Part Number", "Product Description", "Before", *weeks])
    for part, qtys in wo_rows:
        ww.append(["PCH1", part, part, None, *qtys])
    wb.save(path)
