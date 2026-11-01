import { spawn } from "node:child_process";
import { mkdtemp, rm, writeFile, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const EDGE = process.env.PLACEMENTOS_EDGE_PATH || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = Number(process.env.PLACEMENTOS_CDP_PORT || 9333);
const OUTPUT = process.argv[2] || "docs/evidence/p10-accessibility.json";
const profile = await mkdtemp(path.join(tmpdir(), "placementos-a11y-"));
const edge = spawn(EDGE, [
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--no-default-browser-check",
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  "http://localhost:3000",
], { stdio: "ignore" });

class Cdp {
  constructor(url) {
    this.nextId = 1;
    this.pending = new Map();
    this.ws = new WebSocket(url);
  }
  async connect() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    });
  }
  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { this.ws.close(); }
}

async function waitForTargets() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const targets = await response.json();
      const page = targets.find((target) => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Edge DevTools target did not become ready");
}

async function evaluate(cdp, expression) {
  const response = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
  return response.result.value;
}

async function key(cdp, value, code, windowsVirtualKeyCode) {
  const common = { key: value, code, windowsVirtualKeyCode, nativeVirtualKeyCode: windowsVirtualKeyCode };
  await cdp.send("Input.dispatchKeyEvent", {
    type: "keyDown",
    ...common,
    ...(value === "Enter" ? { text: "\r", unmodifiedText: "\r" } : {}),
  });
  await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", ...common });
}

async function waitFor(cdp, expression, message) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (await evaluate(cdp, expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(message);
}

async function navigate(cdp, url) {
  await cdp.send("Page.navigate", { url });
  await waitFor(cdp, "document.readyState === 'complete'", `Navigation did not complete: ${url}`);
}

async function focusAndEnter(cdp, finder) {
  const focused = await evaluate(cdp, `(() => { const element = ${finder}; if (!element) return false; element.focus(); return document.activeElement === element; })()`);
  if (!focused) return false;
  await key(cdp, "Enter", "Enter", 13);
  return true;
}

const report = {
  measured_at: new Date().toISOString(),
  method: "Headless Microsoft Edge keyboard and rendered-DOM audit through the Chrome DevTools Protocol",
  viewport: {},
  checks: {},
  notes: [],
};

let cdp;
try {
  const target = await waitForTargets();
  cdp = new Cdp(target.webSocketDebuggerUrl);
  await cdp.connect();
  await cdp.send("Page.enable");
  await cdp.send("Page.bringToFront");
  await cdp.send("Runtime.enable");
  await cdp.send("Accessibility.enable");
  await waitFor(cdp, "document.readyState === 'complete'", "Initial page did not load");
  await waitFor(cdp, "document.body.textContent.includes('Select Dev Persona')", "Persona trigger did not render");

  await evaluate(cdp, "document.body.focus() || true");
  await key(cdp, "Tab", "Tab", 9);
  report.checks.skip_link_first = await evaluate(cdp, "document.activeElement?.textContent?.trim() === 'Skip to main content'");
  await key(cdp, "Enter", "Enter", 13);
  report.checks.skip_link_targets_main = await evaluate(cdp, "document.activeElement?.id === 'main-content'");

  report.checks.persona_trigger_keyboard = await focusAndEnter(
    cdp,
    "[...document.querySelectorAll('button')].find((item) => item.textContent.includes('Select Dev Persona'))",
  );
  await waitFor(cdp, "document.querySelectorAll('[role=menuitem]').length >= 4", "Persona menu did not open");
  report.checks.persona_menu_semantics = await evaluate(cdp, "document.querySelector('[role=menu]') !== null && document.querySelectorAll('[role=menuitem]').length >= 4");
  report.checks.coordinator_login_keyboard = await focusAndEnter(cdp, "document.querySelector('[role=menuitem]')");
  await waitFor(cdp, "document.body.textContent.includes('Priya Sharma')", "Coordinator persona did not become active");

  await navigate(cdp, "http://localhost:3000/coordinator/operations");
  await waitFor(cdp, "document.body.textContent.includes('Operations and pilot readiness')", "Operations screen did not render");
  report.checks.operations_heading = await evaluate(cdp, "document.querySelector('h1')?.textContent.trim() === 'Operations and pilot readiness'");
  report.checks.synthetic_only_warning = await evaluate(cdp, "document.body.textContent.includes('Synthetic demo only') && document.body.textContent.includes('Do not load real student data')");
  report.checks.refresh_keyboard = await focusAndEnter(cdp, "[...document.querySelectorAll('button')].find((item) => item.textContent.trim() === 'Refresh status')");
  await waitFor(cdp, "!document.body.textContent.includes('Loading operational readiness')", "Refresh did not finish");

  await navigate(cdp, "http://localhost:3000/coordinator/approvals");
  await waitFor(cdp, "document.querySelector('h1') !== null", "Approval screen did not render");
  report.checks.approval_evidence_heading = await evaluate(cdp, "document.querySelector('h1')?.textContent.includes('approval center') === true");
  report.checks.form_controls_named = await evaluate(cdp, `(() => [...document.querySelectorAll('button,input,select,textarea')].filter((element) => !element.disabled).every((element) => {
    const label = element.labels?.[0]?.textContent?.trim();
    const name = element.getAttribute('aria-label') || element.getAttribute('aria-labelledby') || label || element.textContent?.trim() || element.getAttribute('title');
    return Boolean(name);
  }))()`);

  await waitFor(cdp, "document.querySelector('button[aria-label=\"Switch Persona\"]') !== null", "Authenticated persona switcher did not render");
  report.checks.student_switch_keyboard = await focusAndEnter(cdp, "document.querySelector('button[aria-label=\"Switch Persona\"]')");
  await waitFor(cdp, "document.querySelectorAll('[role=menuitem]').length >= 4", "Persona menu did not reopen");
  report.checks.student_login_keyboard = await focusAndEnter(
    cdp,
    "[...document.querySelectorAll('[role=menuitem]')].find((item) => item.textContent.includes('Aarav Sharma'))",
  );
  await waitFor(cdp, "document.body.textContent.includes('Aarav Sharma')", "Student persona did not become active");
  await navigate(cdp, "http://localhost:3000/student/drives");
  await waitFor(cdp, "document.querySelector('h1') !== null", "Student drives screen did not render");
  report.checks.student_status_separation = await evaluate(cdp, "document.body.textContent.includes('Eligibility, document readiness, and registration are separate statuses')");
  report.checks.deadline_semantics = await evaluate(cdp, "document.body.textContent.includes('deadlines are enforced by the server')");
  report.checks.file_controls_named = await evaluate(cdp, `(() => [...document.querySelectorAll('input[type=file]')].every((element) => Boolean(element.labels?.[0]?.textContent?.trim() || element.getAttribute('aria-label'))))()`);

  await cdp.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await new Promise((resolve) => setTimeout(resolve, 200));
  report.viewport = { width: 390, height: 844 };
  report.checks.mobile_no_page_overflow = await evaluate(cdp, "document.documentElement.scrollWidth <= window.innerWidth");
  report.checks.touch_targets_present = await evaluate(cdp, "document.querySelectorAll('button, a, input').length > 0");

  const ax = await cdp.send("Accessibility.getFullAXTree");
  const namedInteractive = ax.nodes.filter((node) => ["button", "link", "textbox", "combobox"].includes(node.role?.value) && node.name?.value).length;
  report.accessibility_tree = { nodes: ax.nodes.length, named_interactive_nodes: namedInteractive };
  report.checks.named_interactive_tree = namedInteractive > 0;
  report.notes.push("This is an engineering audit, not a WCAG certification.");
  report.notes.push("The synchronized 100-request API burst is a documented capacity limit; it is unrelated to keyboard conformance.");
  report.passed = Object.values(report.checks).every(Boolean);

  await mkdir(path.dirname(OUTPUT), { recursive: true });
  await writeFile(OUTPUT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  if (!report.passed) process.exitCode = 1;
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  if (cdp) cdp.close();
  edge.kill();
  await new Promise((resolve) => setTimeout(resolve, 500));
  if (profile.startsWith(tmpdir())) {
    try {
      await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch (error) {
      console.warn(`Temporary Edge profile cleanup deferred: ${error.message}`);
    }
  }
}
