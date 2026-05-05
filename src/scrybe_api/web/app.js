const sampleUrls = [
  "https://brahmai.in",
  "https://example.com/article",
  "https://news.ycombinator.com",
];

const sampleOutputs = [
`GET /v1/parse/json?url=https://brahmai.in

{
  "format": "json",
  "document": {
    "metadata": {
      "title": "BRAHMAI – Research & Engineering",
      "content_type": "webpage"
    },
    "markdown": "Title: BRAHMAI – Research & Engineering\\n...",
    "warnings": []
  }
}`,
`GET /v1/parse/markdown?url=https://example.com/article

Title: Example Article
Meta Description: Short summary
URL Source: https://example.com/article

Markdown Content:
# Example Article

Hello world from SCRYBE.`,
`POST /v1/jobs

{
  "url": "https://example.com/report.pdf",
  "output_format": "json",
  "chunk": true,
  "summarize": true
}`
];

function cycleConsole() {
  const urlNode = document.getElementById("sample-url");
  const outputNode = document.getElementById("sample-output");
  if (!urlNode || !outputNode) return;

  let index = 0;
  setInterval(() => {
    index = (index + 1) % sampleUrls.length;
    urlNode.textContent = sampleUrls[index];
    outputNode.textContent = sampleOutputs[index];
  }, 3200);
}

function revealOnScroll() {
  const items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      }
    },
    { threshold: 0.16 }
  );

  items.forEach((item, idx) => {
    item.style.transitionDelay = `${Math.min(idx * 60, 240)}ms`;
    observer.observe(item);
  });
}

async function hydrateCapabilities() {
  const strip = document.getElementById("capability-strip");
  if (!strip) return;

  try {
    const response = await fetch("/v1/capabilities");
    if (!response.ok) return;
    const data = await response.json();

    const pills = [
      data.playwright_available ? "Playwright ready" : "Static fetch only",
      data.liteparse_available ? "OCR adapter ready" : "OCR adapter missing",
      data.openai_configured ? "OpenAI configured" : "OpenAI optional",
      data.auth_enabled ? "Auth enabled" : "Open access",
    ];

    strip.innerHTML = "";
    pills.forEach((label) => {
      const node = document.createElement("span");
      node.className = "cap-pill";
      node.textContent = label;
      strip.appendChild(node);
    });
  } catch {
    // ignore capability hydration errors on the landing page
  }
}

window.addEventListener("DOMContentLoaded", () => {
  cycleConsole();
  revealOnScroll();
  hydrateCapabilities();
});
