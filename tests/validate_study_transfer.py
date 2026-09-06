"""Compare an exported UE state against a separately regenerated UE project."""
import argparse
import json
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',required=True,type=Path)
parser.add_argument('--project',required=True,type=Path)
args=parser.parse_args()
source=json.loads(args.state.read_text(encoding='utf-8'))
actual=json.loads((args.project/'study-state.json').read_text(encoding='utf-8'))
report=json.loads((args.project/'import-verification.json').read_text(encoding='utf-8'))
for key in ('roomId','variant','schemaVersion'):
    assert actual[key]==source[key],key
for key in ('azimuthDeg','elevationDeg','sunLux','exposureEV100'):
    assert abs(actual[key]-source[key])<1e-6,key
for key in ('locationCm','rotationDeg'):
    assert all(abs(a-b)<1e-6 for a,b in zip(actual['camera'][key],source['camera'][key])),key
assert actual['camera']['lensMm']==source['camera']['lensMm']
assert report['unrealImportVerified'] and report['maxBoundsErrorCm']<.1
assert report['comparisonState']==actual
assert actual.get('solar')==source.get('solar'), 'Solar provenance lost during regeneration'
assert actual.get('siteContextSHA256')==source.get('siteContextSHA256'), 'Site context lost during regeneration'
result=dict(statePreserved=True,geometryVerified=True,cameraRotationPreserved=True,
            siteDaylightCalibrated=False)
(args.project/'state-transfer-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
