const dates = /^(\d{4})\/(\d{2})\/(\d{2})\/summary-(?:zh|en)(?:\.html)?$/;
const fragments = /^editions\/(\d{4}-\d{2}-\d{2})\/(?:zh\.html|en\.html|edition\.json)$/;

// Current content is a versioned Static Asset. Only an unmatched old date
// needs Worker execution to report that the edition has been removed.
export function retiredEdition(request: Request, current?: string): Response | null {
  if (!current || !["GET", "HEAD"].includes(request.method)) return null;
  let path: string;
  try {
    path = decodeURIComponent(new URL(request.url).pathname).replace(/^\/+|\/+$/g, "").replace(/\/+/g, "/");
  } catch {
    return null;
  }
  const dated = path.match(dates);
  const day = dated?.slice(1).join("-") ?? path.match(fragments)?.[1];
  return day && day !== current
    ? new Response(null, {status: 410, headers: {"Cache-Control": "no-store"}})
    : null;
}
