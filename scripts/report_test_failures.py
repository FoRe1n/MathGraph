"""Expose JUnit failure details in Actions annotations without hiding failures."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from xml.etree import ElementTree as ET


def annotation(message: str) -> str:
    message = message.replace('\r\n', '\n').replace('\r', '\n')
    return '::error title=JUnit test failure::'+message.replace('%', '%25').replace('\n', '%0A')


def report(path: Path) -> int:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        print(annotation(f'JUnit results unavailable: {type(error).__name__}: {error}'), flush=True)
        return 1
    cases = list(root.iter('testcase'))
    counts = {'tests': len(cases), 'failures': 0, 'errors': 0, 'skipped': 0}
    diagnostics = []
    for case in cases:
        if case.find('skipped') is not None:
            counts['skipped'] += 1
        name = '.'.join(filter(None, (case.get('classname'), case.get('name'))))
        for kind in ('failure', 'error'):
            for result in case.findall(kind):
                counts['failures' if kind == 'failure' else 'errors'] += 1
                details = (result.text or '').replace('\r\n', '\n').replace('\r', '\n').strip()
                message = f'{name}: {result.get("message", kind)}'[:900]
                if details:
                    message += '\n'+details[-3000:]
                diagnostics.append(message)
                print(annotation(message), flush=True)
    summary = ', '.join(f'{key}={value}' for key, value in counts.items())
    print('JUnit results: '+summary, flush=True)
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with Path(summary_path).open('a', encoding='utf-8') as stream:
            stream.write('\nJUnit results: '+summary+'\n')
            for diagnostic in diagnostics:
                stream.write('\n```text\n'+diagnostic.replace('```', '` ` `')+'\n```\n')
    return 1 if diagnostics else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    raise SystemExit(report(parser.parse_args().results))
