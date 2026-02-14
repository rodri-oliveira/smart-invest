import requests
r = requests.post('http://127.0.0.1:8000/portfolio/build?n_positions=10&strategy=score_weighted&name=SmartPortfolio', json={})
print(f'Status: {r.status_code}')
if r.status_code == 200:
    d = r.json()
    print(f'Total: {d["total_weight"]*100:.1f}%')
    for h in d['holdings']:
        print(f"  {h['ticker']}: {h['weight']*100:.1f}%")
else:
    print(f'Erro: {r.text}')
