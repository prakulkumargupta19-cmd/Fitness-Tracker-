/* ================================================================
   ATHLETE TRACKER — API CONFIGURATION
   ================================================================ */

(function () {
    "use strict";

    const isLocalHost =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";
    // When the static frontend is served by dev_server.py on port 8080,
    // keep API calls same-origin so the local proxy handles them. Directly
    // calling port 5000 from the browser creates an unnecessary CORS path.
    const usesLocalApiProxy =
        isLocalHost && ["8080", "8081"].includes(window.location.port);
    const localApiBase =
        isLocalHost && !usesLocalApiProxy
            ? `${window.location.protocol}//${window.location.hostname}:5000`
            : "";
    const configuredApiBase =
        usesLocalApiProxy
            ? ""
            : window.FITNESS_API_BASE ||
              window.APP_CONFIG?.API_BASE ||
              localApiBase;
    const apiBase = configuredApiBase.replace(/\/+$/, "");

    window.APP_CONFIG = {
        API_BASE: apiBase,
        // Set AUTH_BYPASS to true to preview any dashboard/page directly without logging in
        AUTH_BYPASS: false,
        DEMO_MODE: false,
        ROLE_MAP: {
            student: "student",
            coach: "coach",
            admin: "admin"
        },
        DISPLAY_ROLE: {
            player: "Student",
            coach: "Coach",
            admin: "Admin"
        },
        DASHBOARD_PAGES: {
            player: "student/student-dashboard.html",
            coach: "coach/coach-dashboard.html",
            admin: "admin/admin-dashboard.html"
        },
        LOGIN_PAGES: {
            player: "student/student-login.html",
            coach: "coach/coach-login.html",
            admin: "admin/admin-login.html"
        },
        DEBUG: false
    };

    // Local static servers use Flask on port 5000. Deployed pages remain
    // same-origin unless a public API origin is explicitly injected.
    window.FITNESS_API_BASE = apiBase;
    // Keep each portal in its own signed server session when tabs share an origin.
    const portalMatch = window.location.pathname.match(/^\/(admin|coach|student)\//i);
    const requestedPortalRole = new URLSearchParams(window.location.search).get("role");
    const portalRole = portalMatch
        ? portalMatch[1].toLowerCase()
        : ["admin", "coach", "student"].includes((requestedPortalRole || "").toLowerCase())
            ? requestedPortalRole.toLowerCase()
            : "";
    if (typeof window.fetch === "function") {
        const nativeFetch = window.fetch.bind(window);
        window.fetch = function (input, init) {
            let requestUrl;
            try {
                requestUrl = new URL(
                    typeof input === "string" || input instanceof URL ? input : input.url,
                    window.location.href
                );
            } catch (_) {
                return nativeFetch(input, init);
            }
            if (!/^\/api(?:\/|$)|^\/session(?:\/|$)|^\/logout(?:\/|$)/.test(requestUrl.pathname)) {
                return nativeFetch(input, init);
            }
            const headers = new Headers(input instanceof Request ? input.headers : undefined);
            new Headers(init && init.headers).forEach((value, name) => headers.set(name, value));
            if (portalRole) headers.set("X-Portal-Role", portalRole);
            const method = String((init && init.method) || (input instanceof Request && input.method) || "GET").toUpperCase();
            const isWrite = !["GET", "HEAD", "OPTIONS"].includes(method);
            if (isWrite && requestUrl.pathname !== "/api/csrf-token" && !headers.has("X-CSRFToken")) {
                const tokenUrl = new URL("/api/csrf-token", apiBase || window.location.origin);
                return nativeFetch(tokenUrl.toString(), {
                    method: "GET", credentials: "include",
                    headers: portalRole ? { "X-Portal-Role": portalRole } : {}, cache: "no-store"
                }).then((tokenResponse) => {
                    if (!tokenResponse.ok) throw new Error("Could not verify this session. Refresh and try again.");
                    return tokenResponse.json();
                }).then((tokenData) => {
                    if (!tokenData.csrf_token) throw new Error("Could not verify this session. Refresh and try again.");
                    headers.set("X-CSRFToken", tokenData.csrf_token);
                    return nativeFetch(input, { ...(init || {}), headers });
                });
            }
            return nativeFetch(input, { ...(init || {}), headers });
        };
    }
})();
