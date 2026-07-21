import os

with open('seed.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.strip() == '# 4. Add QC Records':
        new_lines.append(line)
        new_lines.append('''    qc_data = [
        (3, "Vikram Nair", -11, "Pass", [], "All welds clean, dimensions correct", "Fabrication"),
        (2, "Vikram Nair", -7, "Fail", ["Surface rust on left panel", "Weld gap > 2mm"], "Requires rework before paint", "Fabrication"),
        (1, "Vikram Nair", -6, "Pass", [], "Post-rework inspection passed", "Painting"),
        (4, "Vikram Nair", -5, "Pass", [], "Paint coat uniform, no blistering", "Painting"),
        (7, "Priya Sharma", -10, "Pass", [], "Dimensions within tolerance", "Fabrication"),
        (9, "Vikram Nair", -9, "Pass", [], "Telecom cabinet passed IP55 seal test", "Final Assembly"),
        (10, "Priya Sharma", -4, "Pass", [], "MCC panel wiring verified", "Final Assembly"),
        (14, "Vikram Nair", -3, "Fail", ["Paint adhesion failure", "Primer coat thin"], "Needs repaint", "Painting"),
        (15, "Priya Sharma", -2, "Pass", [], "EV battery housing sealed correctly", "Fabrication"),
        (17, "Vikram Nair", -1, "Pass", [], "Switchgear clearances verified", "Final Assembly"),
        (20, "Priya Sharma", -6, "Pass", [], "Custom display enclosure dimensions OK", "Fabrication"),
        (21, "Vikram Nair", -5, "Fail", ["Gasket missing on door", "Hinge alignment off"], "Major rework required", "Final Assembly"),
        (5, "Priya Sharma", -4, "Pass", [], "Smart grid panel functional test passed", "Final Assembly"),
        (8, "Vikram Nair", -3, "Pass", [], "Auto component box load tested", "Final Assembly"),
        (12, "Priya Sharma", -2, "Pass", [], "5G cabinet antenna port aligned", "Final Assembly"),
    ]
    for idx, (v_idx, inspector, off, result, defects, notes, stage) in enumerate(qc_data, 1):
        qc = QCRecord(
            id=idx,
            vehicle_id=v_idx,
            inspector_name=inspector,
            inspected_at=now + timedelta(days=off),
            result=result,
            defects_found=defects,
            notes=notes,
            stage=stage
        )
        db.add(qc)
    db.commit()
''')
        skip = True
    elif skip and line.strip() == '# 5. Add Dispatch Records':
        skip = False
        new_lines.append(line)
    elif not skip:
        new_lines.append(line)

with open('seed.py', 'w') as f:
    f.writelines(new_lines)
