import { cp, mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";

const rootDir = process.cwd();
const distDir = path.join(rootDir, "dist");

const includeEntries = [
  "index.html",
  "404.html",
  "services.html",
  "robots.txt",
  "sitemap.xml",
  "assets",
  "blog",
  "projects",
  "tender-automation/frontend",
  "functions",
];

async function copyEntry(relativePath) {
  const src = path.join(rootDir, relativePath);
  const dest = path.join(distDir, relativePath);

  const info = await stat(src);
  await mkdir(path.dirname(dest), { recursive: true });

  if (info.isDirectory()) {
    await cp(src, dest, { recursive: true });
    return;
  }

  await cp(src, dest);
}

async function injectApiBaseUrl() {
  const templatePath = path.join(rootDir, "tender-automation/frontend/config.template.js");
  const outputPath = path.join(distDir, "tender-automation/frontend/config.js");
  const apiBaseUrl = process.env.API_BASE_URL || "";

  const template = await readFile(templatePath, "utf8");
  const replaced = template.replaceAll("__API_BASE_URL__", apiBaseUrl);
  await writeFile(outputPath, replaced, "utf8");
}

async function main() {
  await rm(distDir, { recursive: true, force: true });
  await mkdir(distDir, { recursive: true });

  for (const entry of includeEntries) {
    await copyEntry(entry);
  }

  await injectApiBaseUrl();
  console.log("Build completed: dist/ is ready for deployment.");
}

main().catch((error) => {
  console.error("Build failed:", error);
  process.exit(1);
});
