"""Portable comparison state. Pure Python; shared by the CLI and UE editor."""
import math


def validate_state(state, study):
    if state.get('schemaVersion') != '1.0.0':
        raise ValueError('Unsupported comparison state schema')
    if state.get('roomId') != study['roomId']:
        raise ValueError('Comparison state belongs to another room')
    if state.get('variant') not in study['settings']['variants']:
        raise ValueError('Unknown finish variant')
    for key, low, high in [('azimuthDeg',0,360),('elevationDeg',1,89),
                           ('sunLux',1,150000),('exposureEV100',-5,20)]:
        value=state.get(key)
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError(f'Invalid {key}: expected a finite number in [{low}, {high}]')
    camera=state.get('camera')
    if camera is not None:
        for key in ('locationCm','rotationDeg'):
            values=camera.get(key)
            if not isinstance(values,list) or len(values)!=3 or any(
                isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values):
                raise ValueError('Invalid camera '+key)
        lens=camera.get('lensMm')
        if isinstance(lens,bool) or not isinstance(lens,(float,int)) or not 12<=lens<=120:
            raise ValueError('Invalid camera lens')
    return state


def default_state(study, job):
    return validate_state(dict(schemaVersion='1.0.0',roomId=study['roomId'],
        variant=study['variant'],azimuthDeg=study['lighting']['azimuthDeg'],
        elevationDeg=study['lighting']['elevationDeg'],sunLux=job['sunLux'],
        exposureEV100=job['exposureEV100'],camera=None),study)
