"""Prepare or import the existing static design review; never manufacture a viewed result."""
import argparse
from studio import Project, read, write, sha, stamp
from production_contract import check_design_record, check_validator_evidence


def prepare(p, scene, png, validator_report=None):
    report = {'scene': scene['id'], 'content_key': p.visual_content_key(scene),
              'status': 'pending', 'viewed': False, 'reviewer': '', 'observed': '',
              'files': {png: sha(p.file(png))}}
    if validator_report:
        result = read(p.file(validator_report))
        html = str(p.file(result['html']).relative_to(p.path)).replace('\\', '/')
        report.update(validator_report=validator_report, source_html=html)
        report['files'].update({html: sha(p.file(html)), validator_report: sha(p.file(validator_report))})
        check_validator_evidence(p, report)
    return report


def import_review(p, scene, path):
    report = read(p.file(path))
    check_design_record(p, scene, report, accepted_status=('pass', 'rejected'))
    dest = '.history/design-review-' + scene['id'] + '-' + stamp() + '.json'
    write(p.file(dest), report)
    scene['design_review'] = dest
    write(p.file('project.json'), p.data)
    p.save('design_review_recorded', scene=scene['id'], report=dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project'); parser.add_argument('--scene', required=True)
    parser.add_argument('--validator-report', help='Coverage-aware original validator JSON, relative to project; use with --png')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--png', help='Prepare a pending review for the actually rendered PNG')
    group.add_argument('--import-report', help='Project-relative completed review; actual viewing required')
    args = parser.parse_args()
    if args.validator_report and not args.png:
        parser.error('--validator-report is only used when preparing with --png')
    p = Project(args.project); scene = p.scenes(args.scene)[0]
    if args.png:
        dest = 'review/design-review-' + scene['id'] + '-' + stamp() + '.json'
        write(p.file(dest), prepare(p, scene, args.png, args.validator_report)); print(dest)
    else: print(import_review(p, scene, args.import_report))


if __name__ == '__main__': main()
