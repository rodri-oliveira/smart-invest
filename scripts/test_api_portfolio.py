"""Testar API de portfolio diretamente."""

import requests
import json

# Testar endpoint
url = "http://127.0.0.1:8000/portfolio/build?n_positions=10&strategy=score_weighted&name=SmartPortfolio"
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, headers=headers, json={}, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nCarteira ID: {data.get('portfolio_id')}")
        print(f"Nome: {data.get('name')}")
        print(f"Estratégia: {data.get('strategy')}")
        print(f"Posições: {data.get('n_positions')}")
        print(f"Peso Total: {data.get('total_weight', 0) * 100:.1f}%")
        
        print(f"\nHoldings:")
        for h in data.get('holdings', []):
            print(f"  {h['ticker']}: {h['weight']*100:.1f}%")
    else:
        print(f"Erro: {response.text}")
        
except Exception as e:
    print(f"Erro de conexão: {e}")
    print("Backend pode estar offline")
