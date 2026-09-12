"""Build walkthrough clock presets with the existing solar_position model.

The input dates and site are parameters so a future date picker can use the
same calculation. Synthetic preview site values are never labelled as actual.
"""
from datetime import date, datetime, timedelta
import math

from solar_position import position, site_sha256, validate_site


def build_presets(site, season_dates, hours, utc_offset, *, synthetic):
    validate_site(site)
    if not season_dates or not hours or any(hour not in (9, 12, 15, 18, 21, 24) for hour in hours):
        raise ValueError('Invalid walkthrough preset hours')
    if len(set(hours)) != len(hours) or len({entry['id'] for entry in season_dates}) != len(season_dates):
        raise ValueError('Duplicate walkthrough preset')
    rows = []
    for season in season_dates:
        day = date.fromisoformat(season['date'])
        if not season['id'] or not season['label']:
            raise ValueError('Missing season identifier or label')
        for hour in hours:
            moment = datetime.fromisoformat(f'{day.isoformat()}T00:00:00{utc_offset}') + timedelta(hours=hour)
            angles = position(moment.isoformat(), site['latitudeDeg'], site['longitudeDeg'], site['planNorthAzimuthDeg'])
            elevation = angles['elevationDeg']
            # The native state contract requires [1,89]. Below the horizon,
            # night mode hides the sun and sky; 1 degree is only a valid
            # stored placeholder and is not displayed as the solar position.
            night = elevation < 1
            rows.append(dict(seasonId=season['id'], seasonLabel=season['label'], hour=hour,
                localTimestamp=moment.isoformat(), azimuthDeg=angles['azimuthDeg'],
                trueElevationDeg=elevation, elevationDeg=max(1, min(89, elevation)),
                sunLux=max(1000, min(50000, 50000 * math.sin(math.radians(max(1, elevation))) / math.sin(math.radians(60)))),
                mode='night' if night else 'day'))
    return dict(schemaVersion='1.0.0', synthetic=synthetic, siteSHA256=site_sha256(site),
        siteNote=site['note'], seasons=[dict(id=s['id'], label=s['label'], date=s['date']) for s in season_dates],
        hours=hours, presets=rows)
