import {env} from "cloudflare:test";
import {expect, it} from "vitest";
import {editionStore, latestEditionRoute, validateLatest} from "../src/latest-edition";

const day = "2026-11-22";
const artifact = "a".repeat(40);
const build = "reader-build";
const settings = {...env, SITE_EDITION_DATE: day, SITE_ARTIFACT_COMMIT: artifact, SITE_BUILD_KEY: build};
const edition = {
  day, artifact, build,
  home: `<header data-latest-edition-date="${day}"></header>`,
  page: `<section data-date="${day}"></section>`,
  api: JSON.stringify({date: day, items: [{id: "a"}]}),
  rss: "<rss><channel><item></item></channel></rss>",
};
const at = (path: string, method = "GET") => new Request("https://xiyu.news" + path, {method});

it("accepts the exact bound deployment and one RSS item", () => {
  expect(validateLatest(edition, settings)).toBe(true);
  expect(validateLatest({...edition, build: "stale"}, settings)).toBe(false);
  expect(validateLatest({...edition, api: '{"date":"2026-11-21","items":[1]}'}, settings)).toBe(false);
  expect(validateLatest({...edition, rss: "<item></item><item></item>"}, settings)).toBe(false);
});

it("serves one stored revision, drops older dates and falls back safely during code changes", async () => {
  await editionStore(settings).writeLatestEdition(edition);
  for (const [path, body] of [
    ["/", edition.home],
    ["/2026/11/22/summary-zh", edition.page],
    ["/2026/11/22/summary-zh.html/", edition.page],
    ["/api/latest.json", edition.api],
    ["/editions/2026-11-22/edition.json", edition.api],
    ["/feed.xml", edition.rss],
  ] as const) {
    const response = await latestEditionRoute(at(path), settings);
    expect(response?.headers.get("Cache-Control")).toBe("no-store");
    expect(await response?.text()).toBe(body);
  }
  expect(await (await latestEditionRoute(at("/", "HEAD"), settings))?.text()).toBe("");
  expect((await latestEditionRoute(at("/2026/11/21/summary-zh"), settings))?.status).toBe(410);
  expect((await latestEditionRoute(at("/editions/2026-11-21/edition.json"), settings))?.status).toBe(410);
  expect(await latestEditionRoute(at("/"), {...settings, SITE_BUILD_KEY: "other-build"})).toBeNull();
  expect(await latestEditionRoute(at("/", "POST"), settings)).toBeNull();
});
