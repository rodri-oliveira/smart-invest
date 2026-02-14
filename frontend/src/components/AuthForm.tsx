"use client";

import { useState } from "react";
import { Lock, Mail, User, Eye, EyeOff, ArrowRight } from "lucide-react";

interface AuthFormProps {
  onLogin: (email: string, password: string) => void;
  onRegister: (email: string, password: string, name: string) => void;
  isLoading?: boolean;
  error?: string | null;
}

export default function AuthForm({ onLogin, onRegister, isLoading, error }: AuthFormProps) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (isRegistering) {
      if (formData.password !== formData.confirmPassword) {
        return;
      }
      onRegister(formData.email, formData.password, formData.name);
    } else {
      onLogin(formData.email, formData.password);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="glass-card rounded-2xl p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold gradient-text mb-2">
            {isRegistering ? "Criar Conta" : "Bem-vindo"}
          </h1>
          <p className="text-[var(--text-secondary)]">
            {isRegistering 
              ? "Crie sua conta para começar a investir" 
              : "Entre para acessar suas recomendações"}
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-[var(--error)]/10 border border-[var(--error)]/30">
            <p className="text-sm text-[var(--error)]">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {isRegistering && (
            <div className="relative">
              <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Nome completo"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="
                  w-full bg-[var(--surface)] rounded-xl
                  py-4 pl-12 pr-4
                  text-[var(--text-primary)]
                  placeholder:text-[var(--text-muted)]
                  border border-[var(--surface-light)]
                  focus:border-[var(--primary)] focus:outline-none
                  transition-colors
                "
                required
              />
            </div>
          )}

          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)]" />
            <input
              type="email"
              placeholder="Email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="
                w-full bg-[var(--surface)] rounded-xl
                py-4 pl-12 pr-4
                text-[var(--text-primary)]
                placeholder:text-[var(--text-muted)]
                border border-[var(--surface-light)]
                focus:border-[var(--primary)] focus:outline-none
                transition-colors
              "
              required
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)]" />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Senha"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="
                w-full bg-[var(--surface)] rounded-xl
                py-4 pl-12 pr-12
                text-[var(--text-primary)]
                placeholder:text-[var(--text-muted)]
                border border-[var(--surface-light)]
                focus:border-[var(--primary)] focus:outline-none
                transition-colors
              "
              required
              minLength={6}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--primary)]"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          {isRegistering && (
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)]" />
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Confirmar senha"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className="
                  w-full bg-[var(--surface)] rounded-xl
                  py-4 pl-12 pr-4
                  text-[var(--text-primary)]
                  placeholder:text-[var(--text-muted)]
                  border border-[var(--surface-light)]
                  focus:border-[var(--primary)] focus:outline-none
                  transition-colors
                "
                required
              />
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="
              w-full py-4 rounded-xl
              bg-[var(--gradient-primary)]
              text-white font-semibold
              flex items-center justify-center gap-2
              hover:opacity-90 hover:scale-[1.02]
              active:scale-[0.98]
              transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              glow-primary
            "
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                {isRegistering ? "Criar Conta" : "Entrar"}
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        {/* Toggle */}
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => setIsRegistering(!isRegistering)}
            className="text-sm text-[var(--text-muted)] hover:text-[var(--primary-light)] transition-colors"
          >
            {isRegistering 
              ? "Já tem uma conta? Entre" 
              : "Não tem conta? Cadastre-se"}
          </button>
        </div>
      </div>
    </div>
  );
}
