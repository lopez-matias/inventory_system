import https from "node:https";

const HOST = "cleanup-mirrors-mystery-surely.trycloudflare.com";

export default function handler(req, res) {
  if (!["GET", "HEAD"].includes(req.method)) {
    res.statusCode = 405;
    res.setHeader("Allow", "GET, HEAD");
    return res.end("Method Not Allowed");
  }

  const url = new URL(req.url, "https://localhost");
  const route = url.searchParams.get("__route") || "";

  url.searchParams.delete("__route");

  const path = "/" + route.replace(/^\/+/, "") + url.search;

  const upstream = https.request(
    {
      hostname: HOST,
      servername: HOST,
      port: 443,
      method: req.method,
      path,
      headers: {
        Host: HOST,
        Accept: req.headers.accept || "*/*"
      },
      timeout: 15000
    },
    (response) => {
      res.statusCode = response.statusCode || 502;

      for (const header of [
        "content-type",
        "content-length",
        "content-encoding",
        "etag",
        "last-modified",
        "location"
      ]) {
        if (response.headers[header] !== undefined) {
          res.setHeader(header, response.headers[header]);
        }
      }

      res.setHeader("Cache-Control", "no-store");
      response.pipe(res);
    }
  );

  upstream.on("timeout", () => {
    upstream.destroy(new Error("Upstream timeout"));
  });

  upstream.on("error", (error) => {
    console.error("StockFlow upstream error:", error.message);

    if (!res.headersSent) {
      res.statusCode = 502;
      res.end("StockFlow upstream unavailable");
    } else {
      res.destroy();
    }
  });

  upstream.end();
}