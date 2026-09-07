"""Validate editable finish scales before an expensive engine import."""
import math


def validate_finishes(document):
    if document.get('schemaVersion')!='1.0.0': raise ValueError('Unsupported finish schema')
    roles=document.get('roles',{})
    if set(roles)!={'floor','wall','ceiling','wood','fabric','cabinet'}:
        raise ValueError('Missing or unknown finish roles')
    def number(value,low,high):
        return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and low<=value<=high
    for role,detail in roles.items():
        if not number(detail.get('roughness'),0,1): raise ValueError('Invalid roughness: '+role)
        if role=='floor':
            if detail.get('paletteRole')!='wood' or detail.get('status') not in ('estimated','verified') or not detail.get('note'):
                raise ValueError('Floor requires palette role and provenance')
            plank=detail.get('planks',{})
            for key,low,high in [('widthCm',3,60),('lengthCm',20,500),('seamCm',0,.5),('rotationDeg',0,360)]:
                if not number(plank.get(key),low,high): raise ValueError('Invalid plank '+key)
        else:
            scale=detail.get('noiseScalePerCm')
            if not isinstance(scale,list) or len(scale)!=3 or not all(number(v,.0001,100) for v in scale):
                raise ValueError('Invalid texture scale: '+role)
            if not number(detail.get('colorMin'),0,2) or not number(detail.get('colorMax'),0,2) or detail['colorMin']>detail['colorMax']:
                raise ValueError('Invalid finish modulation: '+role)
    for variant,overrides in document.get('variantOverrides',{}).items():
        if variant!='reference' or not isinstance(overrides,dict): raise ValueError('Unknown finish variant override')
        for role,detail in overrides.items():
            if role not in ('floor','ceiling'): raise ValueError('Unsupported surface override')
            if detail.get('paletteRole')!=role or detail.get('status')!='estimated' or not detail.get('note'):
                raise ValueError('Surface override requires palette and provenance')
            if not number(detail.get('roughness'),0,1): raise ValueError('Invalid surface roughness')
            pattern=detail.get('pattern',{})
            if pattern.get('kind') not in ('tile','boards'): raise ValueError('Invalid surface pattern')
            for key,low,high in [('widthCm',3,200),('lengthCm',10,600),('seamCm',.01,1),('rotationDeg',0,360)]:
                if not number(pattern.get(key),low,high): raise ValueError('Invalid surface '+key)
    return document


def details_for_variant(document, variant):
    validate_finishes(document)
    return {**document['roles'],**document.get('variantOverrides',{}).get(variant,{})}
