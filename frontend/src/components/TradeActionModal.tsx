"use client";

import { useRef } from "react";

interface TradeActionModalProps {
  open: boolean;
  title: string;
  description: string;
  consequenceHint?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  defaultTicker?: string;
  defaultQuantity?: string;
  showTickerInput?: boolean;
  isSubmitting?: boolean;
  onCancel: () => void;
  onConfirm: (values: { ticker: string; quantity: string }) => void;
}

export default function TradeActionModal({
  open,
  title,
  description,
  consequenceHint,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  defaultTicker = "",
  defaultQuantity = "100",
  showTickerInput = false,
  isSubmitting = false,
  onCancel,
  onConfirm,
}: TradeActionModalProps) {
  const tickerRef = useRef<HTMLInputElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-surface-light bg-surface p-5 shadow-2xl">
        <h3 className="text-base font-semibold text-(--text-primary)">{title}</h3>
        <p className="text-sm text-(--text-secondary) mt-1">{description}</p>
        {consequenceHint && (
          <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2">
            <p className="text-xs text-amber-300">
              <strong>Consequencia da acao:</strong> {consequenceHint}
            </p>
          </div>
        )}

        <div className="mt-4 space-y-3">
          {showTickerInput && (
            <div>
              <label className="block text-xs text-(--text-muted) mb-1">Ticker</label>
              <input
                key={`ticker-${defaultTicker}`}
                ref={tickerRef}
                defaultValue={defaultTicker}
                placeholder="Ex: WEGE3"
                className="w-full px-3 py-2 rounded-lg bg-surface-light border border-surface-light text-sm"
              />
            </div>
          )}
          <div>
            <label className="block text-xs text-(--text-muted) mb-1">Quantidade</label>
            <input
              key={`qty-${defaultQuantity}`}
              ref={quantityRef}
              defaultValue={defaultQuantity}
              placeholder="Ex: 100"
              inputMode="numeric"
              className="w-full px-3 py-2 rounded-lg bg-surface-light border border-surface-light text-sm"
            />
          </div>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-2 rounded-lg bg-surface-light hover:bg-white/10 text-sm"
            disabled={isSubmitting}
          >
            {cancelLabel}
          </button>
          <button
            onClick={() =>
              onConfirm({
                ticker: tickerRef.current?.value || defaultTicker,
                quantity: quantityRef.current?.value || defaultQuantity,
              })
            }
            className="px-3 py-2 rounded-lg bg-primary hover:bg-primary-light text-white text-sm disabled:opacity-50"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Processando..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
