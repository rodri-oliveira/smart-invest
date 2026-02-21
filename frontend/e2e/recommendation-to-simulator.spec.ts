import { expect, test, type Page } from "@playwright/test";

const API_URL = "http://localhost:8000";

async function mockAuthenticatedSession(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("token", "fake-token");
  });

  await page.route(`${API_URL}/auth/me`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        email: "demo@smartinvest.com",
        name: "Demo User",
      }),
    });
  });

  await page.route(`${API_URL}/recommendation/data-status`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "fresh",
        prices_date: "2026-02-14",
        scores_date: "2026-02-14",
        today: "2026-02-14",
        prices_count: 2,
        scores_count: 2,
        active_universe: 2,
        prices_coverage: 1,
        scores_coverage: 1,
        days_since_prices: 0,
      }),
    });
  });
}

test("consulta de ativo e adiciona ao simulador", async ({ page }) => {
  await mockAuthenticatedSession(page);

  page.on("dialog", async (dialog) => {
    if (dialog.type() === "prompt") {
      await dialog.accept("1");
      return;
    }
    await dialog.accept();
  });

  await page.route(`${API_URL}/recommendation/asset-insight`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mode: "asset_query",
        ticker: "SANB11",
        name: "Santander BR Unit",
        sector: "Financeiro",
        latest_price: 36.32,
        latest_date: "2026-02-14",
        change_1d_pct: -1.71,
        change_7d_pct: 5.06,
        change_30d_pct: 10.26,
        score_final: null,
        risk_label: "MODERADO",
        guidance: "Sem score recente. Observe mais alguns dias.",
        didactic_summary: "SANB11 em R$ 36,32 com oscilacao controlada.",
      }),
    });
  });

  await page.route("**/simulation/order", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "success" }),
    });
  });

  await page.route("**/simulation/positions*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          ticker: "SANB11",
          quantity: 1,
          avg_price: 36.32,
          total_cost: 36.32,
          current_price: 36.32,
          profit_loss: 0,
          profit_loss_pct: 0,
        },
      ]),
    });
  });

  await page.route("**/simulation/alerts*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/simulation/daily-plan*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        generated_at: "2026-02-14T10:00:00",
        is_real: false,
        profile: "leigo",
        summary: "Plano do dia para 1 ativo.",
        next_step: "Acompanhe sem aumentar risco.",
        guidance: [
          {
            ticker: "SANB11",
            action: "Acompanhar",
            reason: "Sem score recente.",
            risk_level: "MEDIO",
          },
        ],
      }),
    });
  });

  await page.goto("/");

  await expect(page.getByText("Qual e o seu objetivo?")).toBeVisible();

  const input = page.locator("textarea");
  await input.fill("sobre o Santander?");
  await page.keyboard.press("Enter");

  await expect(page.getByText("Consulta de Ativo: SANB11")).toBeVisible();
  await page.getByRole("button", { name: "Adicionar ao Simulador" }).click();

  await expect(page.getByRole("heading", { name: /simulador/i })).toBeVisible();
  await expect(page.getByText("SANB11", { exact: true })).toBeVisible();
});

test("simulador vazio exibe mensagens didaticas", async ({ page }) => {
  await mockAuthenticatedSession(page);

  await page.route("**/simulation/positions*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
  await page.route("**/simulation/alerts*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
  await page.route("**/simulation/daily-plan*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        generated_at: "2026-02-14T10:00:00",
        is_real: false,
        profile: "leigo",
        summary: "Voce ainda nao tem ativos nesta carteira.",
        next_step: "Escolha um ativo, compre pouco e acompanhe por alguns dias.",
        guidance: [],
      }),
    });
  });

  await page.goto("/");
  await page.getByText("Simulador de Compra").click();

  await expect(page.getByText("Como operar de forma simples")).toBeVisible();
  await expect(page.getByText("Voce ainda nao tem ativos nesta carteira.")).toBeVisible();
  await expect(page.getByText("Nenhuma simulacao ativa no momento.")).toBeVisible();
});

test("alerta operacional permite acao Ajustar", async ({ page }) => {
  await mockAuthenticatedSession(page);

  page.on("dialog", async (dialog) => {
    if (dialog.type() === "prompt") {
      await dialog.accept("1");
      return;
    }
    await dialog.accept();
  });

  await page.route("**/simulation/positions*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          ticker: "WEGE3",
          quantity: 2,
          avg_price: 80.98,
          total_cost: 161.96,
          current_price: 78.0,
          profit_loss: -5.96,
          profit_loss_pct: -3.68,
        },
      ]),
    });
  });
  await page.route("**/simulation/alerts*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          ticker: "WEGE3",
          type: "REBALANCE",
          severity: "MEDIUM",
          message: "Score atual indica saida da estrategia.",
          is_real: false,
        },
      ]),
    });
  });
  await page.route("**/simulation/daily-plan*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        generated_at: "2026-02-14T10:00:00",
        is_real: false,
        profile: "leigo",
        summary: "Plano do dia para 1 ativo.",
        next_step: "Reveja risco e ajuste se necessario.",
        guidance: [
          {
            ticker: "WEGE3",
            action: "Reduzir risco",
            reason: "Sinal enfraquecido.",
            risk_level: "ALTO",
          },
        ],
      }),
    });
  });

  let sellOrderCaptured = false;
  await page.route("**/simulation/order", async (route) => {
    const body = route.request().postDataJSON() as { order_type?: string };
    if (body?.order_type === "SELL") {
      sellOrderCaptured = true;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "success" }),
    });
  });

  await page.goto("/");
  await page.getByText("Simulador de Compra").click();
  await expect(page.getByRole("button", { name: "Ajustar" })).toBeVisible();

  await page.getByRole("button", { name: "Ajustar" }).click();
  await expect
    .poll(() => sellOrderCaptured, {
      timeout: 5000,
    })
    .toBeTruthy();
});
