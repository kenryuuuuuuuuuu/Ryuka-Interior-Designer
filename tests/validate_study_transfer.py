"""Compare an exported UE state against a separately regenerated UE project."""
import argparse
import json
import struct
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state',required=True,type=Path)
parser.add_argument('--project',required=True,type=Path)
args=parser.parse_args()
source=json.loads(args.state.read_text(encoding='utf-8'))
actual=json.loads((args.project/'study-state.json').read_text(encoding='utf-8'))
report=json.loads((args.project/'import-verification.json').read_text(encoding='utf-8'))
# W07-G1/G2: --state is always the MERGED, full-scope state
# (refresh-visual-study.py's own merged-study-state.json) -- unlike the
# pre-G1 single-room shape, schemaVersion is not expected to "upgrade" here
# (the merge itself already produced the current schema, 2.1.0 since W07-G2);
# an actual mismatch is a real regeneration bug, not a legitimate
# legacy-schema pass-through.
assert actual['schemaVersion']=='2.1.0'==source['schemaVersion'],'schemaVersion'
for key in ('scopeId','activeRoomId','roomStates'):
    assert actual[key]==source[key],key
# W07-G2: doorStates/walkthrough are whole-house fields too (like
# azimuthDeg/roomStates above) -- a saved door-open state or a recorded
# walkthrough position must transfer through a full regeneration exactly,
# never reset to closed/null along the way.
assert actual.get('doorStates')==source.get('doorStates'),'doorStates lost during regeneration'
assert actual.get('walkthrough')==source.get('walkthrough'),'walkthrough position lost during regeneration'
for key in ('azimuthDeg','elevationDeg','sunLux','exposureEV100'):
    assert abs(actual[key]-source[key])<1e-6,key
for key in ('locationCm','rotationDeg'):
    assert all(abs(a-b)<1e-6 for a,b in zip(actual['camera'][key],source['camera'][key])),key
# CineCamera stores focal length as float32; native runtime JSON may contain float64.
expected_lens=struct.unpack('<f',struct.pack('<f',source['camera']['lensMm']))[0]
assert actual['camera']['lensMm']==expected_lens, 'Camera lens changed beyond float32 storage precision'
assert report['unrealImportVerified'] and report['maxBoundsErrorCm']<.1
assert report['comparisonState']==actual
assert actual.get('solar')==source.get('solar'), 'Solar provenance lost during regeneration'
assert actual.get('siteContextSHA256')==source.get('siteContextSHA256'), 'Site context lost during regeneration'
result=dict(statePreserved=True,geometryVerified=True,cameraRotationPreserved=True,
            siteDaylightCalibrated=False)
(args.project/'state-transfer-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
