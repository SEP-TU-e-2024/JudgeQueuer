# conftest.py
from collections import defaultdict


def pytest_collection_modifyitems(config, items):
    # Group tests by their class
    class_items = defaultdict(list)
    for item in items:
        cls = getattr(item, 'cls', None)
        if cls:
            class_items[cls].append(item)
        else:
            class_items['No Class'].append(item)
    
    # Reorder items to be grouped by class
    new_order = []
    for cls, cls_items in class_items.items():
        new_order.extend(cls_items)
    
    items[:] = new_order

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # Print the tests grouped by class
    tr = terminalreporter
    if hasattr(tr, 'stats'):
        for outcome in ['passed', 'failed', 'skipped', 'error']:
            if outcome in tr.stats:
                class_tests = defaultdict(list)
                for test in tr.stats[outcome]:
                    cls = getattr(test, 'cls', None)
                    if cls:
                        class_tests[cls].append(test)
                    else:
                        class_tests['No Class'].append(test)

                tr.write_sep("=", f"Grouped by test class - {outcome.capitalize()} tests")
                for cls, tests in class_tests.items():
                    tr.write(f"\n{cls.__name__ if cls != 'No Class' else cls}:\n")
                    for test in tests:
                        tr.write(f"  {test.nodeid}\n")

