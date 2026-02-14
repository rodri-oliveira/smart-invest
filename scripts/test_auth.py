#!/usr/bin/env python3
"""Testar sistema de autenticação."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aim.data_layer.database import Database
from aim.auth import get_auth_manager


def test_auth_system():
    """Testa fluxo completo de autenticação."""
    print("=" * 60)
    print("TESTE DO SISTEMA DE AUTENTICAÇÃO")
    print("=" * 60)
    
    db = Database()
    auth = get_auth_manager(db)
    
    # Teste 1: Criar usuário
    print("\n1. Criando usuário de teste...")
    result = auth.create_user(
        email="teste@smartinvest.com",
        password="senha123",
        name="Usuário Teste"
    )
    
    if result["success"]:
        print(f"   ✓ Usuário criado: {result['email']}")
    else:
        print(f"   ℹ {result['error']} (pode já existir)")
    
    # Teste 2: Login com credenciais corretas
    print("\n2. Testando login...")
    login = auth.authenticate(
        email="teste@smartinvest.com",
        password="senha123"
    )
    
    if login["success"]:
        print(f"   ✓ Login bem-sucedido!")
        print(f"   Token: {login['token'][:50]}...")
        print(f"   Usuário: {login['user']['name']} ({login['user']['email']})")
        
        # Teste 3: Verificar token
        print("\n3. Verificando token...")
        user_data = auth.verify_token(login["token"])
        
        if user_data:
            print(f"   ✓ Token válido!")
            print(f"   ID: {user_data['user_id']}")
            print(f"   Email: {user_data['email']}")
        else:
            print(f"   ✗ Token inválido!")
        
        # Teste 4: Alterar senha
        print("\n4. Testando alteração de senha...")
        change = auth.change_password(
            user_id=login["user"]["id"],
            old_password="senha123",
            new_password="nova456"
        )
        
        if change["success"]:
            print(f"   ✓ Senha alterada!")
        else:
            print(f"   ✗ Erro: {change['error']}")
        
        # Teste 5: Login com nova senha
        print("\n5. Testando login com nova senha...")
        login2 = auth.authenticate(
            email="teste@smartinvest.com",
            password="nova456"
        )
        
        if login2["success"]:
            print(f"   ✓ Login com nova senha funcionou!")
        else:
            print(f"   ✗ Erro: {login2['error']}")
        
        # Teste 6: Tentativa com senha errada
        print("\n6. Testando login com senha errada...")
        login_fail = auth.authenticate(
            email="teste@smartinvest.com",
            password="senhaerrada"
        )
        
        if not login_fail["success"]:
            print(f"   ✓ Login bloqueado corretamente")
            print(f"   Motivo: {login_fail['error']}")
        else:
            print(f"   ✗ Deveria ter falhado!")
    
    else:
        print(f"   ✗ Login falhou: {login['error']}")
    
    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS!")
    print("=" * 60)


if __name__ == "__main__":
    test_auth_system()
