// Old Cloudflare Pages host -> canonical domain. Exact-host match so branch-preview
// hosts and the custom domain are never redirected; everything else falls through
// to the static assets (404.html, _headers, _redirects unchanged).
const OLD_HOST = "specialty-coffee-roasterdb.pages.dev";
const NEW_HOST = "roasterdb.dataengineered.io";

// Roaster pages retired because the brand sells through another roaster's store
// (since 2026-10-02): trescabezas.de 301s to 19grams.coffee, the same Shopify shop, so
// its sample coffee is listed under 19grams. Each language's old URL 301s to the same
// language's page. Answered here, before the asset layer, so an edge copy of a deleted
// page cannot keep serving it.
const MOVED_ROASTERS = { "tres-cabezas": "19grams" };
const ROASTER_PAGE = /^\/(?:(es|de|fr|pt-br)\/)?roasters\/([a-z0-9-]+)(?:\.html|\/)?$/;

// Repo-only files. Pages serves the whole repository root, so without this the
// translation catalogs, the build scripts, their config, the README and dotfiles
// would be downloadable from the site. They get the site's normal 404 instead
// (they stay in the GitHub repository).
const REPO_ONLY_PREFIXES = ["/locales/", "/scripts/"];
const REPO_ONLY_FILES = new Set(["/i18n.config.json", "/readme.md", "/vercel.json", "/requirements.txt"]);

// Matched on the decoded, slash-collapsed, lower-cased path, because the asset
// server also answers /locales%2Fes.json and //locales/es.json.
function isRepoOnly(pathname) {
  let path;
  try {
    path = decodeURIComponent(pathname);
  } catch {
    return true; // malformed escapes never name a real page
  }
  path = path.replace(/\/{2,}/g, "/").toLowerCase();
  if (REPO_ONLY_FILES.has(path)) return true;
  if (REPO_ONLY_PREFIXES.some((prefix) => path.startsWith(prefix))) return true;
  // dotfiles and dot-segments (.gitignore, .github/, ..), but keep /.well-known/ usable
  return path.split("/").some((seg) => seg.startsWith(".") && seg !== ".well-known");
}

export async function onRequest({ request, env, next }) {
  const url = new URL(request.url);
  if (url.hostname === OLD_HOST) {
    url.hostname = NEW_HOST;
    return Response.redirect(url.toString(), 301);
  }
  if (isRepoOnly(url.pathname)) {
    // A path that cannot exist makes Pages answer with 404.html, as for any unknown URL.
    const missing = await env.ASSETS.fetch(new URL("/__not_found__", url).toString());
    return new Response(missing.body, { status: 404, headers: missing.headers });
  }
  const m = ROASTER_PAGE.exec(url.pathname);
  if (m && Object.prototype.hasOwnProperty.call(MOVED_ROASTERS, m[2])) {
    url.pathname = `${m[1] ? `/${m[1]}` : ""}/roasters/${MOVED_ROASTERS[m[2]]}`;
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
