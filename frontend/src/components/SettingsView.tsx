"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, RefreshCw, Shield, ShieldCheck } from "lucide-react";
import { authService, AuditEvent, TenantProfile } from "@/services/auth";

interface SettingsViewProps {
  tenantProfile: TenantProfile | null;
}

const DEFAULT_LIMIT = 30;

export default function SettingsView({ tenantProfile }: SettingsViewProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [severity, setSeverity] = useState<"" | "INFO" | "WARN" | "ERROR">("");
  const [days, setDays] = useState(7);
  const [eventType, setEventType] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAudit = async (nextOffset = offset) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await authService.getRecentAuditEvents({
        limit: DEFAULT_LIMIT,
        offset: nextOffset,
        severity: severity || undefined,
        days,
        event_type: eventType.trim() || undefined,
      });
      setEvents(data.items);
      setTotal(data.total);
      setHasMore(data.has_more);
      setOffset(data.offset);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Falha ao carregar auditoria.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentPage = Math.floor(offset / DEFAULT_LIMIT) + 1;
  const totalPages = Math.max(1, Math.ceil(total / DEFAULT_LIMIT));
  const firstRow = total === 0 ? 0 : offset + 1;
  const lastRow = Math.min(offset + events.length, total);

  const exportCsv = () => {
    const headers = ["id", "created_at", "severity", "event_type", "message", "ip_address", "user_id"];
    const escapeCsv = (value: unknown) => {
      const stringValue = String(value ?? "");
      if (/[",\n]/.test(stringValue)) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    };
    const rows = events.map((event) =>
      [
        event.id,
        event.created_at,
        event.severity,
        event.event_type,
        event.message,
        event.ip_address || "",
        event.user_id ?? "",
      ].map(escapeCsv).join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 10);
    link.href = url;
    link.download = `audit-events-${stamp}-page-${currentPage}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const counts = useMemo(
    () => ({
      info: events.filter((e) => e.severity === "INFO").length,
      warn: events.filter((e) => e.severity === "WARN").length,
      error: events.filter((e) => e.severity === "ERROR").length,
    }),
    [events],
  );

  return (
    <div className="space-y-6">
      <div className="glass-card rounded-2xl p-6 border border-surface-light">
        <h2 className="text-lg font-bold text-(--text-primary) mb-4 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-primary-light" />
          Plano e Segurança
        </h2>
        {tenantProfile ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <InfoCard label="Plano" value={tenantProfile.plan_name} />
            <InfoCard
              label="Limite de Ativos Simulados"
              value={String(tenantProfile.limits.max_simulated_positions)}
            />
            <InfoCard
              label="Recursos"
              value={[
                tenantProfile.features.allow_real_portfolio ? "Carteira Real" : null,
                tenantProfile.features.allow_history ? "Historico" : null,
                tenantProfile.features.allow_daily_plan ? "Plano Diario" : null,
              ]
                .filter(Boolean)
                .join(", ")}
            />
          </div>
        ) : (
          <p className="text-sm text-(--text-muted)">Perfil do tenant indisponível.</p>
        )}
      </div>

      <div className="glass-card rounded-2xl p-6 border border-surface-light">
        <div className="flex flex-wrap items-center gap-3 justify-between mb-4">
          <h3 className="text-lg font-semibold text-(--text-primary) flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-light" />
            Auditoria Recente
          </h3>
          <button
            onClick={() => fetchAudit(offset)}
            className="px-3 py-2 text-xs rounded-lg bg-surface-light hover:bg-white/10 transition-colors inline-flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as "" | "INFO" | "WARN" | "ERROR")}
            className="px-3 py-2 bg-surface-light rounded-lg text-sm"
          >
            <option value="">Todas severidades</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
          </select>
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value, 10))}
            className="px-3 py-2 bg-surface-light rounded-lg text-sm"
          >
            <option value={1}>Último dia</option>
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
          </select>
          <input
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            placeholder="event_type (opcional)"
            className="px-3 py-2 bg-surface-light rounded-lg text-sm"
          />
          <button
            onClick={() => fetchAudit(0)}
            className="px-3 py-2 text-sm rounded-lg bg-(--primary-muted) text-primary-light hover:bg-primary hover:text-white transition-colors"
          >
            Aplicar filtros
          </button>
        </div>

        <div className="flex flex-wrap gap-3 mb-4 text-xs items-center justify-between">
          <div className="flex gap-3">
            <Badge tone="info" label={`INFO: ${counts.info}`} />
            <Badge tone="warn" label={`WARN: ${counts.warn}`} />
            <Badge tone="error" label={`ERROR: ${counts.error}`} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-(--text-muted)">
              Mostrando {firstRow}-{lastRow} de {total}
            </span>
            <button
              onClick={exportCsv}
              disabled={events.length === 0}
              className="px-3 py-1.5 text-xs rounded-lg bg-surface-light hover:bg-white/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Exportar CSV
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-sm text-error inline-flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-(--text-muted) border-b border-surface-light">
                <th className="text-left py-2 pr-3">Data</th>
                <th className="text-left py-2 pr-3">Severidade</th>
                <th className="text-left py-2 pr-3">Evento</th>
                <th className="text-left py-2 pr-3">Mensagem</th>
                <th className="text-left py-2">IP (mascarado)</th>
              </tr>
            </thead>
            <tbody>
              {!isLoading && events.length === 0 && (
                <tr>
                  <td className="py-4 text-(--text-muted)" colSpan={5}>
                    Nenhum evento encontrado para os filtros atuais.
                  </td>
                </tr>
              )}
              {events.map((event) => (
                <tr key={event.id} className="border-b border-surface-light/40">
                  <td className="py-2 pr-3 text-(--text-secondary)">
                    {new Date(event.created_at).toLocaleString("pt-BR")}
                  </td>
                  <td className="py-2 pr-3">
                    <Badge
                      tone={
                        event.severity === "ERROR"
                          ? "error"
                          : event.severity === "WARN"
                            ? "warn"
                            : "info"
                      }
                      label={event.severity}
                    />
                  </td>
                  <td className="py-2 pr-3 text-(--text-primary)">{event.event_type}</td>
                  <td className="py-2 pr-3 text-(--text-secondary)">{event.message}</td>
                  <td className="py-2 text-(--text-muted)">{event.ip_address || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-end gap-2 text-sm">
          <button
            onClick={() => fetchAudit(Math.max(0, offset - DEFAULT_LIMIT))}
            disabled={offset === 0 || isLoading}
            className="px-3 py-1.5 rounded-lg bg-surface-light hover:bg-white/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Anterior
          </button>
          <span className="text-(--text-muted)">
            Pagina {currentPage} de {totalPages}
          </span>
          <button
            onClick={() => fetchAudit(offset + DEFAULT_LIMIT)}
            disabled={!hasMore || isLoading}
            className="px-3 py-1.5 rounded-lg bg-surface-light hover:bg-white/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Proxima
          </button>
        </div>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-light p-3 border border-surface-light">
      <div className="text-(--text-muted) text-xs mb-1">{label}</div>
      <div className="text-(--text-primary) font-semibold">{value || "-"}</div>
    </div>
  );
}

function Badge({ tone, label }: { tone: "info" | "warn" | "error"; label: string }) {
  const cls =
    tone === "error"
      ? "bg-error/15 text-error"
      : tone === "warn"
        ? "bg-warning/15 text-(--warning)"
        : "bg-info/15 text-info";
  return <span className={`inline-flex px-2 py-1 rounded-md text-xs font-semibold ${cls}`}>{label}</span>;
}
