"""Geometric solar centre, NOAA/Meeus equations; degrees east/north positive.
No refraction, weather, illuminance or surrounding-obstruction model.
Reference: https://gml.noaa.gov/grad/solcalc/calcdetails.html
"""
from datetime import datetime, timezone
import hashlib
import json
import math

ALGORITHM = 'noaa-meeus-geometric-v1'


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid '+name)
    return value


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be ISO 8601 with an explicit UTC offset')
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None or not 1901 <= result.astimezone(timezone.utc).year <= 2099:
        raise ValueError('Use a timezone-aware timestamp in UTC years 1901–2099')
    return result


def validate_site(site):
    if not isinstance(site, dict) or site.get('schemaVersion') != '1.0.0':
        raise ValueError('Invalid local site schema')
    number(site.get('latitudeDeg'), -90, 90, 'latitude')
    number(site.get('longitudeDeg'), -180, 180, 'longitude')
    number(site.get('planNorthAzimuthDeg'), 0, 360, 'plan north azimuth')
    for key in ('locationStatus', 'northStatus'):
        if site.get(key) not in ('estimated', 'verified'):
            raise ValueError('Missing site provenance: '+key)
    if not isinstance(site.get('note'), str) or not site['note'].strip():
        raise ValueError('Site requires a provenance note')
    return site


def position(local_time, latitude, longitude, plan_north=0):
    dt = timestamp(local_time).astimezone(timezone.utc)
    number(latitude, -90, 90, 'latitude'); number(longitude, -180, 180, 'longitude')
    number(plan_north, 0, 360, 'plan north')
    t = (dt.timestamp()/86400 + 2440587.5 - 2451545)/36525
    rad = math.radians
    sin = lambda a: math.sin(rad(a))
    cos = lambda a: math.cos(rad(a))
    l0 = (280.46646 + t*(36000.76983 + .0003032*t)) % 360
    m = 357.52911 + t*(35999.05029 - .0001537*t)
    e = .016708634 - t*(.000042037 + .0000001267*t)
    centre = sin(m)*(1.914602-t*(.004817+.000014*t)) + sin(2*m)*(.019993-.000101*t) + .000289*sin(3*m)
    omega = 125.04 - 1934.136*t
    apparent = l0 + centre - .00569 - .00478*sin(omega)
    obliquity = 23 + (26+(21.448-t*(46.815+t*(.00059-.001813*t)))/60)/60 + .00256*cos(omega)
    dec = math.asin(sin(obliquity)*sin(apparent))
    y = math.tan(rad(obliquity)/2)**2
    equation = 4*math.degrees(y*sin(2*l0)-2*e*sin(m)+4*e*y*sin(m)*cos(2*l0)-.5*y*y*sin(4*l0)-1.25*e*e*sin(2*m))
    minutes = dt.hour*60 + dt.minute + dt.second/60 + dt.microsecond/60000000
    hour = rad(((minutes+equation+4*longitude) % 1440)/4-180)
    lat = rad(latitude)
    elevation = math.degrees(math.asin(max(-1,min(1,math.sin(lat)*math.sin(dec)+math.cos(lat)*math.cos(dec)*math.cos(hour)))))
    azimuth = (math.degrees(math.atan2(math.sin(hour),math.cos(hour)*math.sin(lat)-math.tan(dec)*math.cos(lat)))+180) % 360
    return dict(trueAzimuthDeg=azimuth, azimuthDeg=(azimuth-plan_north)%360, elevationDeg=elevation)


def site_sha256(site):
    """Semantic hash of a local site input (W05): the SAME canonical
    (sorted-key) JSON encoding make_case() has always hashed into a solar
    case's siteSHA256 -- kept as its own function so a caller checking
    "does this site.local.json still match these cases" hashes the PARSED
    site dict, not the on-disk file's raw bytes (which can differ in
    indentation/whitespace/trailing newline without the site's actual
    content having changed). Never conflate the two."""
    validate_site(site)
    return hashlib.sha256(json.dumps(site,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def cases_match_site(cases, site):
    """True if every case in `cases` (an iterable of solar cases, e.g.
    document['cases']) was computed from exactly this site input. Used
    whenever a site.local.json and a sun-cases.json are both present, to
    catch a sun-cases.json left over from before the site changed --
    recomputing is always an explicit, separate action (see
    study_controls.recompute_sun_cases()), never automatic here."""
    expected = site_sha256(site)
    return all(case.get('siteSHA256') == expected for case in cases)


SEASON_REFERENCE_DATES = ((3, 21), (6, 21), (9, 21), (12, 21))
SEASON_REFERENCE_HOURS = (9, 12, 15)


def season_reference_timestamps(year, utc_offset='+09:00'):
    """12 representative local timestamps (4 calendar dates near the
    equinoxes/solstices x 3 times of day) for `year`, in `utc_offset`. These
    are fixed CALENDAR dates (month/day), not the astronomically exact
    equinox/solstice instant for that year -- callers must not describe them
    as such (W05 spec section 2)."""
    if not isinstance(year, int) or isinstance(year, bool) or not 1901 <= year <= 2099:
        raise ValueError('Invalid year')
    return [f'{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00{utc_offset}'
            for month, day in SEASON_REFERENCE_DATES for hour in SEASON_REFERENCE_HOURS]


def make_case(site, local_time):
    validate_site(site)
    angles = position(local_time, site['latitudeDeg'], site['longitudeDeg'], site['planNorthAzimuthDeg'])
    usable = 1 <= angles['elevationDeg'] <= 89
    return dict(algorithm=ALGORITHM, localTimestamp=timestamp(local_time).isoformat(),
        siteSHA256=site_sha256(site),
        locationStatus=site['locationStatus'], northStatus=site['northStatus'],
        planNorthAzimuthDeg=site['planNorthAzimuthDeg'], **angles, usable=usable,
        reason=None if usable else 'Solar elevation outside the supported daylight interval [1, 89] degrees')


def validate_case(case):
    if not isinstance(case, dict) or case.get('algorithm') != ALGORITHM:
        raise ValueError('Unsupported solar case')
    timestamp(case.get('localTimestamp'))
    for key, low, high in [('trueAzimuthDeg',0,360),('azimuthDeg',0,360),('elevationDeg',-90,90),('planNorthAzimuthDeg',0,360)]:
        number(case.get(key),low,high,key)
    for key in ('locationStatus','northStatus'):
        if case.get(key) not in ('estimated','verified'): raise ValueError('Invalid solar provenance')
    digest = case.get('siteSHA256')
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid site hash')
    if abs((case['trueAzimuthDeg']-case['planNorthAzimuthDeg']-case['azimuthDeg']+180)%360-180)>1e-6:
        raise ValueError('Inconsistent north correction')
    if case.get('usable') is not (1<=case['elevationDeg']<=89):
        raise ValueError('Inconsistent daylight eligibility')
    return case


def matches(case, state):
    return abs((case['azimuthDeg']-state['azimuthDeg']+180)%360-180)<.001 and abs(case['elevationDeg']-state['elevationDeg'])<.001


def apply_case(state, case):
    validate_case(case)
    if not case['usable']: raise ValueError(case['reason'])
    return dict(state,azimuthDeg=case['azimuthDeg'],elevationDeg=case['elevationDeg'],solar=dict(case))


def validate_cases(document):
    if not isinstance(document,dict) or document.get('schemaVersion')!='1.0.0' or not isinstance(document.get('cases'),list) or not document['cases']:
        raise ValueError('Invalid solar case list')
    for case in document['cases']: validate_case(case)
    return document
