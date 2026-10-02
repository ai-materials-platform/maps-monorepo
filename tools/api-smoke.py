import json
import urllib.request

BASE = 'http://127.0.0.1:5000'


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.load(r)
    except Exception as e:
        return -1, str(e)


BASE_INPUT = {
    'Fe': 70.0, 'C': 0.05, 'Si': 0.4, 'Mn': 1.5, 'P': 0.01, 'S': 0.005,
    'Ni': 8.0, 'Cr': 18.0, 'Mo': 2.0, 'Cu': 0.1, 'V': 0.05, 'N': 0.02,
    'Nb': 0.01, 'Ti': 0.01, 'B': 0.001, 'Al': 0.03,
    'Solution_treatment_temperature': 1323.0,
    'Solution_treatment_time(s)': 3600.0,
    'Grains mm-2': 12000.0,
    'Temperature (K)': 293.0,
}

s, r = call('GET', '/status')
print('STATUS:', s, {k: r.get(k) for k in ('model_trained', 'pretrained_available', 'pretrained_model_type')})

s, r = call('POST', '/predict/pretrained', dict(BASE_INPUT))
print('PRETRAINED:', s, r.get('status'), r.get('predictions', {}).get('elongation_pct'), '|', (r.get('correction_note') or '')[:40])

high_c = dict(BASE_INPUT, C=1.5, Ni=0.2)
s, r = call('POST', '/predict/pretrained', high_c)
print('HIGHC:', s, r.get('predictions', {}).get('elongation_pct'), '|', (r.get('correction_note') or '')[:60])

s, r = call('POST', '/curve', {'input': high_c, 'use_pretrained': True,
                               'yield_mode': 'discontinuous', 'luders_strain': 0.02,
                               'fracture_mode': 'auto'})
c = r.get('curve', {}) if isinstance(r, dict) else {}
print('CURVE:', s, 'n=', len(c.get('strain', [])), 'pts=', sorted(c.get('points', {}).keys()),
      'mode=', c.get('meta', {}).get('yield_mode'), c.get('meta', {}).get('fracture_mode'))
