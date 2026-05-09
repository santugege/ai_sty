import { test } from "playwright/test";

const pageUrl = process.env.PAGE_URL || "http://127.0.0.1:3000";
const apiPath = "/api/images/generate";

test("reproduce product image generation from page", async ({ page }) => {
  const consoleMessages = [];
  const apiEvents = [];

  page.on("console", (message) => {
    consoleMessages.push({
      type: message.type(),
      text: message.text(),
    });
  });

  page.on("request", (request) => {
    if (request.url().includes(apiPath)) {
      apiEvents.push({
        event: "request",
        method: request.method(),
        url: request.url(),
        postData: request.postData() || "",
      });
    }
  });

  page.on("response", async (response) => {
    if (response.url().includes(apiPath)) {
      let body = "";
      try {
        body = await response.text();
      } catch (error) {
        body = `<<failed to read body: ${error.message}>>`;
      }
      apiEvents.push({
        event: "response",
        status: response.status(),
        url: response.url(),
        body: body.slice(0, 800),
      });
    }
  });

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "生成商品图" }).click();

  let status = "pending";
  let resultImageCount = 0;
  let errorText = "";

  for (let attempt = 0; attempt < 90; attempt += 1) {
    await page.waitForTimeout(1000);

    resultImageCount = await page.getByAltText("电商商品图生成结果").count();
    if (resultImageCount > 0) {
      status = "image-rendered";
      break;
    }

    const errorLocator = page.locator(".text-error").locator("..").locator("p");
    const errorCount = await errorLocator.count();
    if (errorCount > 0) {
      errorText = (await errorLocator.first().innerText()).trim();
      if (errorText) {
        status = "error-rendered";
        break;
      }
    }

    const idleButtonCount = await page
      .getByRole("button", { name: "生成商品图" })
      .count();
    if (idleButtonCount > 0 && apiEvents.some((event) => event.event === "response")) {
      status = "submitted-no-result";
      break;
    }
  }

  await page.screenshot({
    path: "output/playwright/product-generation-result.png",
    fullPage: true,
  });

  console.log(JSON.stringify({
    status,
    pageUrl,
    resultImageCount,
    errorText,
    apiEvents,
    consoleMessages,
  }, null, 2));
});
