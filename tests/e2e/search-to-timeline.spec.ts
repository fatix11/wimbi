import { test, expect } from "@playwright/test";

test("CC officer can search a farmer and view their journey timeline", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign in as Chikondi Mvula" }).click();
  await expect(page).toHaveURL(/\/search$/);

  await page.getByPlaceholder(/Grace Banda/).fill("Grace");
  await page.getByRole("link", { name: /Grace Banda/ }).click();

  await expect(page).toHaveURL(/\/farmers\/GL-MW-00001$/);
  await expect(page.getByText("Grace Banda")).toBeVisible();
  await expect(page.getByText("Enrolled in Credit program")).toBeVisible();
});

test("a Malawi-scoped user cannot open a farmer from another country", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign in as Chikondi Mvula" }).click();
  await expect(page).toHaveURL(/\/search$/);

  await page.goto("/farmers/GL-KE-00001");
  await expect(page.getByText(/this page could not be found/i)).toBeVisible();
});
