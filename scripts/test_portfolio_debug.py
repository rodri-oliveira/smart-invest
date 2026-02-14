import requests

# Testar portfolio build com prompt
try:
    r = requests.post(
        'http://127.0.0.1:8000/portfolio/build?n_positions=10&strategy=score_weighted&name=SmartPortfolio',
        json={'prompt': 'Especular aceitando alto risco'},
        timeout=30
    )
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        d = r.json()
        print(f"Regime: {d.get('user_regime')}")
        print(f"Peso Total: {d.get('total_weight', 0) * 100:.1f}%")
    else:
        print(f'Erro: {r.text[:500]}')
except Exception as e:
    print(f'Erro: {e}')
