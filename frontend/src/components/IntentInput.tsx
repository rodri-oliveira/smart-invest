"use client";

import { useState } from "react";
import { Sparkles, Send, Loader2, Target, BarChart3, ShieldCheck } from "lucide-react";

interface IntentInputProps {
  onSubmit: (prompt: string) => void;
  isLoading?: boolean;
}

const EXAMPLES = [
  "Quero alto retorno em 30 dias",
  "Proteger meu capital de forma conservadora",
  "Renda passiva com dividendos",
  "Especular aceitando alto risco",
  "Como esta a acao da Petrobras hoje?",
  "Me mostra a situacao do Santander",
  "Como esta WEGE3?",
  "Quero montar carteira para iniciantes",
  "Tenho perfil moderado e foco em longo prazo",
  "Prefiro baixo risco e caixa de seguranca",
  "Me explique os riscos da estrategia em linguagem simples",
  "Quais ativos estao mais fortes no momento?",
];

const ONBOARDING_KEY = "smartinvest_onboarding_v1_done";

function pickExamples(items: string[], count: number): string[] {
  const clone = [...items];
  for (let i = clone.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [clone[i], clone[j]] = [clone[j], clone[i]];
  }
  return clone.slice(0, count);
}

export default function IntentInput({ onSubmit, isLoading = false }: IntentInputProps) {
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [examples, setExamples] = useState<string[]>(() => pickExamples(EXAMPLES, 6));
  const [showOnboarding, setShowOnboarding] = useState<boolean>(() => {
    try {
      return localStorage.getItem(ONBOARDING_KEY) !== "1";
    } catch {
      return true;
    }
  });

  const dismissOnboarding = () => {
    setShowOnboarding(false);
    try {
      localStorage.setItem(ONBOARDING_KEY, "1");
    } catch {
      // no-op
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const normalized = prompt.trim();
    if (normalized && !isLoading) {
      onSubmit(normalized);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold gradient-text mb-4">Qual e o seu objetivo?</h1>
        <p className="text-(--text-secondary) text-lg">
          Descreva sua intencao em linguagem natural. O motor quantitativo adapta a estrategia automaticamente.
        </p>
      </div>

      {showOnboarding && (
        <div className="mb-6 p-4 rounded-xl bg-surface border border-primary-light/20">
          <h3 className="text-sm font-semibold text-primary-light">Primeiro uso em 3 passos</h3>
          <p className="text-xs text-(--text-secondary) mt-2">
            1) Escreva seu objetivo em linguagem simples. 2) Leia os blocos O que aconteceu e O que fazer agora.
            3) Clique em <strong>+</strong> para testar no simulador antes de decidir.
          </p>
          <button
            type="button"
            onClick={dismissOnboarding}
            className="mt-3 px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary-light transition-colors text-xs"
          >
            Entendi
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="relative">
        <div
          className={`
            relative glass-card rounded-2xl p-2
            transition-all duration-300 ease-out
            ${isFocused ? "glow-primary scale-[1.02]" : "hover:scale-[1.01]"}
          `}
        >
          <div className="absolute left-4 top-1/2 -translate-y-1/2">
            <Sparkles
              className={`w-6 h-6 transition-colors duration-300 ${
                isFocused ? "text-primary-light" : "text-(--text-muted)"
              }`}
            />
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const normalized = prompt.trim();
                if (normalized && !isLoading) {
                  onSubmit(normalized);
                }
              }
            }}
            placeholder="Ex: Quero alto retorno em 30 dias com risco moderado..."
            className="
              w-full bg-transparent border-none outline-none
              text-(--text-primary) text-lg
              placeholder:text-(--text-muted)
              min-h-[80px] max-h-[200px]
              py-4 px-14 resize-none
            "
            disabled={isLoading}
          />

          <button
            type="submit"
            disabled={!prompt.trim() || isLoading}
            className={`
              absolute right-3 top-1/2 -translate-y-1/2
              w-12 h-12 rounded-xl
              flex items-center justify-center
              transition-all duration-300
              ${
                prompt.trim() && !isLoading
                  ? "bg-(--gradient-primary) hover:scale-110 glow-primary"
                  : "bg-surface-light cursor-not-allowed"
              }
            `}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-(--text-primary) animate-spin" />
            ) : (
              <Send className={`w-5 h-5 ${prompt.trim() ? "text-white" : "text-(--text-muted)"}`} />
            )}
          </button>
        </div>

        <div className="flex justify-between mt-3 px-2">
          <span className="text-xs text-(--text-muted)">{prompt.length > 0 && `${prompt.length} caracteres`}</span>
          <span className="text-xs text-(--text-muted)">Enter envia. Shift + Enter quebra linha.</span>
        </div>
      </form>

      <div className="mt-8">
        <div className="flex items-center justify-center gap-3 mb-3">
          <p className="text-sm text-(--text-muted)">Exemplos de prompts:</p>
          <button
            type="button"
            onClick={() => setExamples(pickExamples(EXAMPLES, 6))}
            className="text-xs text-primary-light hover:text-primary transition-colors"
          >
            trocar exemplos
          </button>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          {examples.map((example) => (
            <button
              key={example}
              onClick={() => setPrompt(example)}
              disabled={isLoading}
              className="
                px-4 py-2 rounded-full text-sm
                bg-surface border border-(--primary-muted)
                text-(--text-secondary)
                hover:bg-(--primary-muted) hover:text-primary-light
                hover:border-primary
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-12">
        {[
          {
            title: "Adaptativo",
            desc: "Motor ajusta aos seus objetivos",
            icon: <Target className="w-6 h-6 text-primary-light" />,
          },
          {
            title: "Quantitativo",
            desc: "Analise baseada em dados reais",
            icon: <BarChart3 className="w-6 h-6 text-primary-light" />,
          },
          {
            title: "Risk-First",
            desc: "Risco calculado antes de retorno",
            icon: <ShieldCheck className="w-6 h-6 text-primary-light" />,
          },
        ].map((item) => (
          <div
            key={item.title}
            className="
              glass-card rounded-xl p-4 text-center
              hover:bg-surface-light
              transition-all duration-300
            "
          >
            <div className="text-2xl mb-2 flex justify-center">{item.icon}</div>
            <h3 className="text-sm font-semibold text-primary-light mb-1">{item.title}</h3>
            <p className="text-xs text-(--text-muted)">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
