"use client";

import { useState } from "react";
import { Sparkles, Send, Loader2 } from "lucide-react";

interface IntentInputProps {
  onSubmit: (prompt: string) => void;
  isLoading?: boolean;
}

export default function IntentInput({ onSubmit, isLoading = false }: IntentInputProps) {
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isLoading) {
      onSubmit(prompt.trim());
    }
  };

  const examples = [
    "Quero alto retorno em 30 dias",
    "Proteger meu capital conservadoramente",
    "Renda passiva com dividendos",
    "Especular aceitando alto risco",
  ];

  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold gradient-text mb-4">
          Qual é o seu objetivo?
        </h1>
        <p className="text-[var(--text-secondary)] text-lg">
          Descreva sua intenção em linguagem natural. Nosso motor quantitativo 
          adaptará a estratégia automaticamente.
        </p>
      </div>

      {/* Input Container */}
      <form onSubmit={handleSubmit} className="relative">
        <div
          className={`
            relative glass-card rounded-2xl p-2
            transition-all duration-300 ease-out
            ${isFocused ? "glow-primary scale-[1.02]" : "hover:scale-[1.01]"}
          `}
        >
          {/* Sparkle Icon */}
          <div className="absolute left-4 top-1/2 -translate-y-1/2">
            <Sparkles 
              className={`w-6 h-6 transition-colors duration-300 ${
                isFocused ? "text-[var(--primary-light)]" : "text-[var(--text-muted)]"
              }`} 
            />
          </div>

          {/* Text Input */}
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Ex: Quero alto retorno em 30 dias aceitando risco moderado..."
            className="
              w-full bg-transparent border-none outline-none
              text-[var(--text-primary)] text-lg
              placeholder:text-[var(--text-muted)]
              min-h-[80px] max-h-[200px]
              py-4 px-14 resize-none
            "
            disabled={isLoading}
          />

          {/* Submit Button */}
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
                  ? "bg-[var(--gradient-primary)] hover:scale-110 glow-primary"
                  : "bg-[var(--surface-light)] cursor-not-allowed"
              }
            `}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-[var(--text-primary)] animate-spin" />
            ) : (
              <Send className={`w-5 h-5 ${prompt.trim() ? "text-white" : "text-[var(--text-muted)]"}`} />
            )}
          </button>
        </div>

        {/* Character Counter */}
        <div className="flex justify-between mt-3 px-2">
          <span className="text-xs text-[var(--text-muted)]">
            {prompt.length > 0 && `${prompt.length} caracteres`}
          </span>
          <span className="text-xs text-[var(--text-muted)]">
            Pressione Enter para enviar
          </span>
        </div>
      </form>

      {/* Example Prompts */}
      <div className="mt-8">
        <p className="text-sm text-[var(--text-muted)] mb-3 text-center">
          Exemplos de prompts:
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {examples.map((example, index) => (
            <button
              key={index}
              onClick={() => setPrompt(example)}
              disabled={isLoading}
              className="
                px-4 py-2 rounded-full text-sm
                bg-[var(--surface)] border border-[var(--primary-muted)]
                text-[var(--text-secondary)]
                hover:bg-[var(--primary-muted)] hover:text-[var(--primary-light)]
                hover:border-[var(--primary)]
                transition-all duration-200
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-3 gap-4 mt-12">
        {[
          { 
            title: "Adaptativo", 
            desc: "Motor ajusta aos seus objetivos",
            icon: "🎯"
          },
          { 
            title: "Quantitativo", 
            desc: "Análise baseada em dados reais",
            icon: "📊"
          },
          { 
            title: "Risk-First", 
            desc: "Risco calculado antes de retorno",
            icon: "🛡️"
          },
        ].map((item, index) => (
          <div
            key={index}
            className="
              glass-card rounded-xl p-4 text-center
              hover:bg-[var(--surface-light)]
              transition-all duration-300
            "
          >
            <div className="text-2xl mb-2">{item.icon}</div>
            <h3 className="text-sm font-semibold text-[var(--primary-light)] mb-1">
              {item.title}
            </h3>
            <p className="text-xs text-[var(--text-muted)]">
              {item.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
