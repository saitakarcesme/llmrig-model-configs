"""Check that independent computer-use grading accepts and rejects real CSVs."""
import json
from pathlib import Path
from eval_fixtures import Fixture

root=Path('/home/isa/Experiments/qwen38-flash-next-b70-fit')
fixture=Fixture('computer_use',root/'fixture-selfcheck')
fixture.setup_browser()
try:
    assert not fixture.verify()
    for selector in ('#unpaid','#overdue','#sort','#export'):
        fixture.page.locator(selector).click()
    fixture.page.wait_for_timeout(300)
    assert fixture.verify(),fixture.output.read_text()
    confirmation=fixture.page.locator('#count').inner_text()
    assert confirmation=='Exported 3 invoices to overdue-invoices.csv'
    positive=fixture.output.read_text()
    fixture.page.locator('#overdue').click()
    fixture.page.locator('#export').click()
    fixture.page.wait_for_timeout(300)
    assert not fixture.verify()
    fixture.coordinate_system='normalized'
    click=fixture.execute('computer_click',{'x':98,'y':198})
    assert click=={'clicked':{'x':98,'y':198,'units':'normalized'}}
    assert fixture.page.locator('#unpaid').inner_text()=='Unpaid only: OFF'
    screen=fixture.execute('computer_screenshot',{})
    assert screen['action_coordinate_units']=='normalized' and screen['action_coordinate_range']==[0,1000]
    try:
        fixture.execute('computer_click',{'x':[98,198],'y':198})
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid coordinate arrays were accepted')
    receipt={'status':'passed','positive_csv':positive,'confirmation':confirmation,
             'normalized_click':click,'coordinate_feedback_verified':True,
             'negative_csv':fixture.output.read_text(),
             'note':'Deterministic fixture self-check; these actions are not model evaluation results.'}
    (root/'receipts/fixture-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
finally:
    fixture.close()
