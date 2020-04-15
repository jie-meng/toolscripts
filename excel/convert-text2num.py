from openpyxl import load_workbook

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return None

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return None

def process_sheet(sheet):
    for row in sheet.iter_rows():
        for cell in row:
            if type(cell.value) == str:
                if is_int(cell.value) != None:
                    print('cell {0} converted to int {1}'.format(cell, cell.value))
                    cell.value = int(cell.value)
                elif is_number(cell.value) != None:
                    print('cell {0} converted float {1}'.format(cell, cell.value))
                    cell.value = float(cell.value)

def write_workbook(source, dest):
    wb = load_workbook(source)

    for sheet in wb.worksheets:
        process_sheet(sheet)

    wb.save(dest)

if __name__== "__main__":
    print('please input source xlsx path:')
    source = input()

    print('please input dest xlsx path:')
    dest = input()
    write_workbook(source, dest)

    print('\ndone!')
