import {expect, it} from "vitest";
import {retiredEdition} from "../src/latest-edition";

const current = "2026-11-22";
const at = (path: string, method = "GET") => new Request("https://xiyu.news" + path, {method});

it("only intercepts retired dated assets on read routes", () => {
  for (const path of ["/", "/api/latest.json", "/feed.xml", "/2026/11/22/summary-zh", "/editions/2026-11-22/edition.json"]) {
    expect(retiredEdition(at(path), current)).toBeNull();
  }
  for (const path of ["/2026/11/21/summary-zh", "/2026/11/21/summary-en.html/", "/editions/2026-11-21/edition.json"]) {
    expect(retiredEdition(at(path), current)?.status).toBe(410);
    expect(retiredEdition(at(path, "HEAD"), current)?.status).toBe(410);
    expect(retiredEdition(at(path, "POST"), current)).toBeNull();
  }
});
