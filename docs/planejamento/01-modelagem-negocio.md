# Smart Invest - Modelagem de Negócio

## 1. Visão do Negócio

### 1.1 Declaração de Propósito

O Smart Invest é um sistema de inteligência estratégica para investimentos que combina:
- **Motor quantitativo determinístico** (cérebro matemático)
- **Camada conversacional com IA** (interface inteligente)
- **Capacidade de gerar ordens práticas estruturadas**

### 1.2 Proposta de Valor

**Para quem**: Investidores individuais no Brasil que querem tomar decisões de investimento baseadas em dados, sem depender de achismos ou "dicas".

**Problema resolvido**:
- Falta de análise quantitativa acessível
- Sobrecarga de informações do mercado
- Dificuldade de interpretar dados macro e técnico
- Ausência de sistema disciplinado de decisão

**Solução**:
- Análise automatizada de ativos brasileiros
- Classificação de regime de mercado (Risk ON/Risk OFF)
- Ranking quantitativo de ações por múltiplos fatores
- Recomendações estruturadas com justificativa técnica
- Interface em linguagem natural

### 1.3 Diferenciais Competitivos

1. **Foco no Brasil**: Dados B3, macro BR, dividendos brasileiros
2. **Quantitativo rigoroso**: Baseado em pesquisa acadêmica (AQR, Antonacci, Faber)
3. **Regime-aware**: Adapta alocação conforme ambiente macro
4. **Multi-fator**: Momentum + Valor + Qualidade (não só um indicador)
5. **Backtestado**: Toda estratégia validada historicamente
6. **Linguagem natural**: Pergunte como falaria com um gestor

---

## 2. Modelo de Receita (Fases)

### Fase 1: Uso Pessoal (Atual)
- **Objetivo**: Validar o sistema investindo capital próprio
- **Receita**: Alpha gerado nas próprias operações
- **Custo**: Desenvolvimento + infraestrutura (R$ 0-100/mês)
- **Investimento inicial**: Tempo de desenvolvimento

### Fase 2: SaaS Freemium (Futuro)
- **Gratuito**: Análise básica, 5 ações/mês, dados delay
- **Pro (R$ 49/mês)**: Análise completa, ranking ilimitado, alertas
- **Premium (R$ 149/mês)**: Carteira personalizada, backtest próprio, API
- **Institucional (sob consulta)**: Licenciamento white-label

### Fase 3: Gestão de Recursos (Futuro distante)
- Viabilidade técnica e regulatória
- Necessita certificações CVM
- Modelo: Taxa de performance sobre alpha

---

## 3. Análise de Mercado

### 3.1 Tamanho do Mercado (TAM/SAM/SOM)

**TAM (Total Addressable Market)**:
- 4+ milhões de investidores na B3
- R$ 5+ trilhões sob custódia

**SAM (Serviceable Addressable Market)**:
- 500 mil investidores com renda > R$ 10k/mês
- Interesse em análise técnica/quantitativa
- Usuários de planilhas e dados

**SOM (Serviceable Obtainable Market)**:
- Fase 1: 1 usuário (você) - validação
- Fase 2: 1.000-10.000 usuários pagos
- Fase 3: 50.000+ usuários

### 3.2 Concorrência

**Direta (Ferramentas de Análise)**:
- Status Invest: Fundamentalista, não quantitativo
- Investing.com: Genérico, não focado BR
- Fundamentus: Dados, sem análise sistemática
- Ticker Trader: Técnico, não quantitativo
- Gorila: Assinatura cara (R$ 300+/mês)

**Indireta (Robôs/Assessores)**:
- Toro Investimentos: Robôs simples
- Warren/BTG: Carteiras pré-fabricadas
- Inteligência artificial de corretoras: Regras fixas

### 3.3 Vantagem Competitiva vs Concorrência

| Aspecto | Smart Invest | Status Invest | Gorila | Corretoras |
|---------|--------------|---------------|---------|------------|
| Quantitativo | ✅ Multi-fator | ❌ Fundamental | ✅ Técnico | ❌ Regras simples |
| Regime-aware | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Backtest | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Linguagem natural | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| Custo | ✅ Grátis/Caro | Grátis | R$ 300+/mês | Embutido |

---

## 4. Estratégia de Go-to-Market

### Fase 1: Validção (0-6 meses)
- Desenvolver MVP
- Investir capital próprio usando o sistema
- Documentar resultados (alpha vs Ibovespa)
- Ajustar modelo baseado em performance real

### Fase 2: Beta Fechado (6-12 meses)
- Convite para 10-20 investidores experientes
- Feedback intensivo
- Ajuste de produto
- Casos de sucesso documentados

### Fase 3: Lançamento Público (12+ meses)
- Landing page + waitlist
- Conteúdo educativo (blog/youtube)
- Parcerias com influenciadores financeiros
- Freemium para aquisição

### Fase 4: Escala (24+ meses)
- Programa de indicação
- Conteúdo SEO/YouTube
- API para desenvolvedores
- Possível captação (se métricas forem boas)

---

## 5. Métricas de Negócio (KPIs)

### Métricas de Performance do Sistema
- **Alpha vs Ibovespa**: > 3% ao ano (CAGR)
- **Sharpe Ratio**: > 0.8
- **Max Drawdown**: < 25%
- **Win Rate mensal**: > 55%

### Métricas de Produto (Fase SaaS)
- **MAU (Monthly Active Users)**: Crescimento 20% mês/mês
- **Churn Rate**: < 5% mensal
- **LTV/CAC**: > 3x
- **NPS**: > 50

### Métricas Técnicas
- **Uptime**: > 99%
- **Latência**: < 2s para análise
- **Cobertura**: 100% do Ibovespa
- **Freshness de dados**: < 24h

---

## 6. Riscos de Negócio e Mitigação

### Riscos de Mercado
| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Modelo para de funcionar | Média | Alto | Diversificação por fatores, stops |
| Crise sistêmica | Baixa | Alto | Regime OFF automático, proteção de capital |
| Dados incorretos | Baixa | Alto | Múltiplas fontes, validação cruzada |

### Riscos Operacionais
| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| API de dados falha | Média | Alto | Fallbacks (brapi → yfinance → cache) |
| Bug no cálculo | Média | Alto | Testes unitários, backtest histórico |
| Vazamento de dados | Baixa | Alto | Não coletar dados pessoais sensíveis |

### Riscos Regulatórios
| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Regulamentação CVM | Média | Alto | Consultoria jurídica, disclaimers claros |
| Responsabilidade por recomendações | Média | Alto | Isenção de responsabilidade, educação |

---

## 7. Canvas de Negócio

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│   PARCEIROS     │    ATIVIDADES   │    RECURSOS     │    PROP. VALOR  │
│    CHAVE        │     CHAVE       │     CHAVE       │                 │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ • brapi.dev     │ • Coleta dados  │ • Motor quant.  │ Análise quant.  │
│ • BCB API       │ • Cálculo fatores│ • Base histórica│ adaptativa      │
│ • AWS/Railway   │ • Classificação │ • Algoritmos    │ com IA          │
│ • Influenciadores│ regime          │ • LLM API       │ conversacional  │
│                 │ • Ranking       │                 │                 │
│                 │ • Backtest      │                 │                 │
├─────────────────┴─────────────────┴─────────────────┴─────────────────┤
│                                                                     │
│                    RELACIONAMENTO COM CLIENTES                        │
│              • Chat/IA conversacional                               │
│              • Relatórios personalizados                              │
│              • Alertas e notificações                                 │
│              • Comunidade (Discord/Telegram futuro)                 │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                         SEGMENTOS DE CLIENTES                        │
│              • Investidores ativos (DIY)                             │
│              • Investidores quantitativos                            │
│              • Trader de swing/position                              │
│              • Futuro: assessores independentes                      │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                         ESTRUTURA DE CUSTOS                        │
│              • Infraestrutura (R$ 0-100 inicial)                     │
│              • APIs de dados (grátis inicial)                        │
│              • LLM API (R$ 5-20/mês)                               │
│              • Desenvolvimento (tempo próprio)                     │
├─────────────────────────────────────────────────────────────────────┤
│                         FONTES DE RECEITA                          │
│              Fase 1: Alpha próprio (retorno investimento)            │
│              Fase 2: Assinaturas (R$ 49-149/mês)                   │
│              Fase 3: Licenciamento/API                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Plano de Receita Detalhado (Projeção)

### Fase 1: Desenvolvimento (Meses 1-6)
- Receita: Alpha do capital próprio investido
- Custo: R$ 0 (desenvolvimento próprio)
- Infra: R$ 0-50/mês (SQLite local, GitHub Actions)

### Fase 2: Beta Fechado (Meses 7-12)
- Usuários: 20 (grátis)
- Custo: R$ 100-200/mês (servidor + API)
- Foco: Validação, não monetização

### Fase 3: Lançamento (Ano 2)
- Usuários: 1.000 (10% pagos = 100)
- Receita: 100 × R$ 49 = R$ 4.900/mês
- Custo: R$ 500-1.000/mês
- Lucro: R$ 3.900-4.400/mês

### Fase 4: Escala (Ano 3)
- Usuários: 10.000 (15% pagos = 1.500)
- Receita: 1.500 × R$ 70 (média) = R$ 105.000/mês
- Custo: R$ 15.000-20.000/mês
- Lucro: R$ 85.000-90.000/mês

---

## 9. Requisitos para Sucesso

### Técnicos
- [ ] Motor quantitativo validado por backtest (10+ anos)
- [ ] Alpha consistente vs Ibovespa (>3% ao ano)
- [ ] Drawdown controlado (<25%)
- [ ] Sistema 99%+ uptime
- [ ] Dados atualizados diariamente

### De Produto
- [ ] Interface conversacional funcional
- [ ] Relatórios claros e acionáveis
- [ ] Tempo de resposta < 2s
- [ ] Cobertura 100% Ibovespa

### De Negócio
- [ ] Capital próprio investido com sucesso
- [ ] Cases de usuários beta
- [ ] Canal de aquisição (conteúdo/SEO)
- [ ] Modelo de preço validado
- [ ] Infraestrutura escalável

---

**Documento versão**: 1.0  
**Criado em**: Fevereiro 2026  
**Próxima revisão**: Após validação do MVP
