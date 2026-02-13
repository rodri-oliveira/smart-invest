#!/usr/bin/env python3
"""Testar API localmente."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import time
import subprocess
import signal
import os

print("Iniciando servidor API...")

# Iniciar servidor em background
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=str(Path(__file__).parent.parent)
)

# Aguardar inicialização
time.sleep(3)

try:
    print("\nTestando endpoints:")
    print("=" * 50)
    
    # Test 1: Health
    try:
        r = requests.get("http://127.0.0.1:8000/health/simple", timeout=5)
        print(f"✓ Health: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"✗ Health: {e}")
    
    # Test 2: Root
    try:
        r = requests.get("http://127.0.0.1:8000/", timeout=5)
        print(f"✓ Root: {r.status_code} - {r.json()['name']}")
    except Exception as e:
        print(f"✗ Root: {e}")
    
    # Test 3: Assets
    try:
        r = requests.get("http://127.0.0.1:8000/assets/", timeout=5)
        data = r.json()
        print(f"✓ Assets: {len(data)} ativos")
    except Exception as e:
        print(f"✗ Assets: {e}")
    
    # Test 4: Regime
    try:
        r = requests.get("http://127.0.0.1:8000/signals/regime/current", timeout=5)
        data = r.json()
        print(f"✓ Regime: {data['regime']} (score: {data['score_total']:.2f})")
    except Exception as e:
        print(f"✗ Regime: {e}")
    
    # Test 5: Ranking
    try:
        r = requests.get("http://127.0.0.1:8000/signals/ranking?top_n=5", timeout=5)
        data = r.json()
        print(f"✓ Ranking: {len(data)} ativos")
        for item in data[:3]:
            print(f"   {item['rank_universe']}. {item['ticker']} (score: {item['score_final']:+.2f})")
    except Exception as e:
        print(f"✗ Ranking: {e}")
    
    print("=" * 50)
    print("✓ Testes concluídos!")
    
finally:
    # Parar servidor
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except:
        proc.kill()
    print("\nServidor parado.")
