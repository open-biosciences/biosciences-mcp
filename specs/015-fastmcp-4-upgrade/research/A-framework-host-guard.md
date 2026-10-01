# A. Framework research: Host guard and FastMCP 4 breaking changes

Spec 015 (FastMCP 4 upgrade), Phase 0 research. Read-only. Researched 2026-09-30.

**Method.** Each version was installed into a throwaway uv venv (`uv venv --python 3.12` + `uv pip install fastmcp==X`) under the session scratchpad. Some intermediate wheels (`fastmcp-slim` 3.4.4/3.4.5/3.4.6/4.0.0, `fastmcp` 3.0.2/3.1.0/3.2.0/3.3.0/3.4.0, `mcp` 1.26.0) were downloaded with `pip download --no-deps` and unzipped. From 3.3 on, the server code ships in the `fastmcp-slim` distribution. The import path is still `fastmcp/...`, so source paths below are given relative to `site-packages/`. Upstream docs were read from the `v4.0.10` tag through `gh api` (raw `.mdx`), with their gofastmcp.com URLs given.

Resolved versions in fresh venvs (CONFIRMED, `importlib.metadata`):

| fastmcp | mcp resolved | mcp constraint (fastmcp-slim `Requires-Dist`) | starlette |
|---|---|---|---|
| 2.14.5 | 1.30.0 (Core's lock pins 1.26.0) | — | — |
| 3.4.2 | 1.30.0 | `mcp<2.0,>=1.24.0` | 1.7.0 |
| 3.4.3 | 1.30.0 | `mcp<2.0,>=1.24.0` | 1.7.0 |
| 3.4.7 | 1.30.0 | `mcp<2.0,>=1.24.0` | 1.7.0 |
| 4.0.10 | 2.2.0 | `mcp<3.0.0,>=2.0.0`, `mcp-types<3.0.0,>=2.0.0`, `httpx2>=2.5.0` | 1.7.0 |

Labels: **CONFIRMED** means read in source or docs, or reproduced empirically. **INFERRED** means reasoned from evidence but not directly observed.

---

## Decision-relevant summary

1. **The 421 comes from FastMCP's own code, not from Starlette or the mcp SDK.** It is `HostOriginGuardMiddleware` in `fastmcp/server/http.py`, added in fastmcp 3.4.3 by PrefectHQ/fastmcp#4405. The fastmcp 3.4.2 and 3.4.3 wheels declare the same mcp constraint, so no SDK change was involved. The mcp SDK has its own 421 path (`TransportSecurityMiddleware`), but that path is off when FastMCP passes no settings (3.x) and is explicitly disabled in 4.x. **CONFIRMED**.
2. **What triggered it in 3.4.3:** the guard was default-on in strict mode (`http_host_origin_protection: bool = True`). The allowlist was only `127.0.0.1`, `localhost`, `::1`, plus the bound socket address when that address is not unspecified. A server bound to `0.0.0.0` therefore accepted only localhost Host headers, and `biosciences-mcp.fastmcp.app` got 421. Reproduced locally: 3.4.3 returns 421 for `Host: biosciences-mcp.fastmcp.app`, and 3.4.2 returns 200. **CONFIRMED**.
3. **The 421 was fixed upstream in 3.4.4 and never returned.** 3.4.4 (PR #4439 then PR #4472) changed the default to `False`, meaning no middleware is installed. 4.0.0 forward-ported the same default (PR #4474), and it is still `False` in 4.0.10. With defaults, 3.4.7 and 4.0.10 return 200 for a public Host header, whether bound to 0.0.0.0 or 127.0.0.1. **The premise behind Edge's `<3.4.3` pin no longer holds for 3.4.4 and later, including 3.4.7 and 4.0.10.** **CONFIRMED** (source, release notes, local reproduction).
4. **Configuration knobs (identical names in 3.4.7 and 4.0.10):**
   - Settings `http_host_origin_protection` (`bool | "auto"`, default `False`), `http_allowed_hosts`, `http_allowed_origins`.
   - Environment variables `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION`, `FASTMCP_HTTP_ALLOWED_HOSTS`, `FASTMCP_HTTP_ALLOWED_ORIGINS`. Lists are given as JSON.
   - Keyword arguments `host_origin_protection=`, `allowed_hosts=`, `allowed_origins=` on `run_http_async()`/`run()` and `http_app()`.
   - There is no `fastmcp run` CLI flag, and the `fastmcp.json` schema has no field for this.
   - **Trap 1:** setting `FASTMCP_HTTP_*` through `fastmcp.json` `deployment.env` has no effect, because it is applied after `fastmcp.settings` has been loaded. Verified on 4.0.10.
   - **Trap 2:** setting `FASTMCP_HTTP_ALLOWED_HOSTS` alone does nothing, because the middleware is only installed when protection is not `False`. **CONFIRMED**.
5. **Recommendation for Horizon: do nothing.** Leave the guard at its default (off), and do not add `FASTMCP_HTTP_*` variables. Turning on `True`, or `"auto"` combined with an allowlist, validates the raw `Host` header only. No `X-Forwarded-Host` support exists in 4.0.10 (issue #4468). If Horizon's ingress rewrites `Host`, those settings would 421 again.
   - `"auto"` with no allowlist also returns 421 when the connection arrives on a loopback socket, for example from an in-pod sidecar proxy. Reproduced: via 127.0.0.1 the result is 421, via the LAN IP it is 200.
   - Whether the guard is "automatically relaxed when not bound to localhost": only in `"auto"` mode, and that check uses the socket address the request arrived on (`scope["server"]`), not the bind address. **CONFIRMED**.
   - How Horizon's ingress rewrites `Host` is not known (INFERRED risk).
6. **Upstream intent:** issue #5213 (open, 2026-09-22) proposes making the guard default-on again. The maintainer-side comment says any default change waits for a trusted-proxy design and would come with a deprecation warning, or in v5. **This is a re-pin risk for future 4.x minors.** Pin `fastmcp>=4.0.10,<4.1`, or add a deploy-time Host smoke test. **CONFIRMED** (issue text); the release-timing part is INFERRED.
7. **Horizon and 4.x support:**
   - No official version-support matrix was found.
   - The v4 docs site documents Horizon Deploy with no version caveat. It says Horizon installs dependencies from `pyproject.toml`/`requirements.txt`, and the entrypoint uses `fastmcp run` syntax.
   - FastMCP 4.0 itself added Horizon CLI account commands (`fastmcp login`/`whoami`/`logout`; there is still no deploy command).
   - Issue #3184 shows Horizon's build running `fastmcp inspect` with the repo's own pinned fastmcp, on Python 3.12.
   - No GitHub issue reports 421 or other failures for FastMCP 4 on Horizon.
   - Conclusion: Horizon runs whatever fastmcp version the repo resolves (INFERRED, strong). 4.x is not explicitly certified (INFERRED). A preview deployment of the branch is the real gate.
8. **Breaking changes in 4.0 that matter here (all CONFIRMED):**
   - `mount(server, namespace=None, tool_names=None)`: `prefix=` and `as_proxy=` are removed and raise `TypeError`.
   - MCP SDK model fields are snake_case (`input_schema`, `output_schema`, `is_error`, ...). A camelCase compatibility bridge emits a warning on each read and can be disabled with `FASTMCP_MCP_CAMELCASE_COMPAT=false`. The wire JSON is unchanged.
   - Docstring parsing has existed since **3.2.4**, not 4.0. The tool description becomes only the first text section. `Args:` entries move into the per-parameter schema `description`. **`Returns:` text is dropped entirely**: it goes nowhere, not even into the output schema. If a docstring has no parseable `Args:`, the whole docstring, including `Returns:`, is kept.
   - Tool argument validation errors are still a `CallToolResult` with `isError: true`, not a JSON-RPC error, in 2.14.5, 3.4.7 and 4.0.10. This holds in-memory and over HTTP, in both `auto` and `legacy` modes.
   - Extra arguments were already rejected in 2.14.5 (pydantic `unexpected_keyword_argument`). The new `additionalProperties: false` therefore changes the advertised schema, not server behaviour.
   - Lifespan: `FastMCP(lifespan=LifespanCallable | Lifespan | None)`, composable with `@lifespan` and `|`. A mounted child's lifespan now runs.
   - Context: `ctx.sample`/`sample_step`/`list_roots` are removed. `ctx.elicit()` needs `response_type` and raises on 2026-07-28 connections. `set_state` does not persist across sessionless requests.
   - The `fastmcp.json` `Deployment` schema is identical in 2.14.5 and 4.0.10.
   - Also: `httpx` became `httpx2` inside FastMCP, `McpError(ErrorData(...))` raises `TypeError`, and resource-not-found now uses error code `-32602`.

---

## Q1. Host guard: which layer, which version, and what triggers the 421

### Layer: FastMCP's own middleware (CONFIRMED)

- `fastmcp/server/http.py` in **3.4.3**:
  - `DEFAULT_HOSTS = ("127.0.0.1", "localhost", "::1")` at line 38.
  - `class HostOriginGuardMiddleware` at lines 223-269.
  - The 421 is at lines 245-248: `if not _host_matches(host, allowed_hosts): response = Response("Misdirected Request", status_code=421)`.
  - The allowlist is built at lines 259-269 from `DEFAULT_HOSTS`, plus `self.allowed_hosts`, plus `scope["server"][0]` *only if* that address is not unspecified (`_is_unspecified_host`). A `0.0.0.0` bind therefore adds nothing.
  - `create_streamable_http_app(..., host_origin_protection: bool = True, ...)` at line 495 inserts the middleware first in the stack when the value is truthy (lines 579-586).
- Settings in 3.4.3 (`fastmcp/settings.py`):
  - `Settings.model_config` uses `env_prefix="FASTMCP_"` and `env_nested_delimiter="__"` (lines 139-143).
  - `http_host_origin_protection: bool = True`, `http_allowed_hosts: list[str] | None = None`, `http_allowed_origins: list[str] | None = None` (lines 323-325).
- Transport mixin in 3.4.3 (`fastmcp/server/mixins/transport.py`): `run_http_async` (line 240) and `http_app` (line 339) take `host_origin_protection`/`allowed_hosts`/`allowed_origins` and fall back to the settings (lines 400-417).
- **Response text tells the layers apart.** FastMCP returns `"Misdirected Request"`. The mcp SDK's `TransportSecurityMiddleware` returns `"Invalid Host header"`, also with status 421:
  - mcp 1.26.0 `mcp/server/transport_security.py:120`
  - mcp 1.30.0 `:127`
  - mcp 2.2.0 `:116`
- **The SDK layer is not active:**
  - When `settings is None`, the SDK uses `TransportSecuritySettings(enable_dns_rebinding_protection=False)` (mcp 1.26.0 `:43`; mcp 1.30.0 `:47-50`; mcp 2.2.0 `:46-48`).
  - FastMCP 3.4.x never passes `security_settings`: `FastMCPStreamableHTTPSessionManager` forwards its default `None` (3.4.7 `fastmcp/server/http.py:43-63`, and the call at `:657-663` omits it).
  - FastMCP 4.0.10 explicitly passes `TransportSecuritySettings(enable_dns_rebinding_protection=False)` (`fastmcp/server/http.py:675-681`). The comment there reads: "FastMCP owns DNS-rebinding protection via HostOriginGuardMiddleware ... Always disable the SDK's own protection".
- **Starlette `TrustedHostMiddleware` is not involved.** It is not referenced anywhere in fastmcp; `grep -rn TrustedHost` returns no hits in any version.
- fastmcp 2.14.5 (Core) and 3.0.2 (Edge lock) contain no `HostOriginGuardMiddleware`, `421`, or `security_settings` wiring. **CONFIRMED** (grep returned zero hits).

### Version history (CONFIRMED)

| Version | Guard default | Notes / source |
|---|---|---|
| ≤ 3.4.2 | no guard | 3.4.2 `fastmcp/` has no `HostOriginGuardMiddleware` (grep) |
| **3.4.3** (2026-07-05) | `True` (strict, localhost-only allowlist) | PR [#4405](https://github.com/PrefectHQ/fastmcp/pull/4405) "Protect streamable HTTP from DNS rebinding"; [release v3.4.3](https://github.com/PrefectHQ/fastmcp/releases/tag/v3.4.3) |
| 3.4.4 (2026-07-09) | `False` (the type also allows `"auto"`) | [release v3.4.4](https://github.com/PrefectHQ/fastmcp/releases/tag/v3.4.4) "restores HTTP deployment compatibility after the 3.4.3 Host/Origin guard changed default behavior". PR [#4439](https://github.com/PrefectHQ/fastmcp/pull/4439) changed the default to `auto`, then PR [#4472](https://github.com/PrefectHQ/fastmcp/pull/4472) changed it to disabled ("restores the 3.x default to disabled ... until v4 can redesign default-on behavior with a complete trusted-proxy story"). 3.4.4 wheel `fastmcp/settings.py:323` = `False` |
| 3.4.5, 3.4.6, 3.4.7 | `False` | wheel `settings.py` 3.4.5:323, 3.4.6:343; 3.4.7 `settings.py:343` |
| 4.0.0 → 4.0.10 | `False` | PR [#4474](https://github.com/PrefectHQ/fastmcp/pull/4474) "Forward-port HTTP host guard compatibility" (in [v4.0.0 notes](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.0.0)); 4.0.0 wheel `settings.py:280`; 4.0.10 `settings.py:280` |

- **The mcp SDK played no part.** fastmcp 3.4.2 and 3.4.3 declare the identical constraint `mcp<2.0,>=1.24.0` (from `importlib.metadata.requires('fastmcp-slim')`), and both resolve mcp 1.30.0 today. The SDK's own protection defaults to off in 1.26, 1.30 and 2.2. **CONFIRMED**.
- Related upstream issue: [#4468](https://github.com/PrefectHQ/fastmcp/issues/4468), "Host guard 421s all traffic behind a reverse proxy, no way to validate the real public hostname (X-Forwarded-Host)". It was closed by #4472, which makes the guard opt-in. **X-Forwarded-Host support was never added**: `grep -rni forwarded` over 4.0.10 `fastmcp/` finds nothing in the guard.

### What triggers the 421

In **3.4.3**, any request whose `Host` header does not match `127.0.0.1`/`localhost`/`::1`, or the bound address when that address is not `0.0.0.0`/`::`, gets 421. Matching uses `fnmatchcase` after normalisation; `"*"` matches everything (`http.py:151-158`). So `biosciences-mcp.fastmcp.app` gets 421 whatever the bind address is. **CONFIRMED** by source and reproduction:

```
fastmcp 3.4.2 bind=0.0.0.0  Host=biosciences-mcp.fastmcp.app -> 200
fastmcp 3.4.3 bind=0.0.0.0  Host=biosciences-mcp.fastmcp.app -> 421
fastmcp 3.4.3 bind=127.0.0.1 Host=biosciences-mcp.fastmcp.app -> 421
fastmcp 3.4.3 + FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=false        -> 200
fastmcp 3.4.3 + FASTMCP_HTTP_ALLOWED_HOSTS='["biosciences-mcp.fastmcp.app"]' -> 200
fastmcp 3.4.7 / 4.0.10 defaults, either bind                     -> 200
```

The probe is `scratchpad/probe/probe.sh`. It POSTs an MCP `initialize` to `/mcp` with an overridden `Host` header against `mcp.run_http_async(host=..., port=...)`.

This matches Edge commit `d4b9502` (2026-07-06), which pinned `fastmcp<3.4.3` after hci-canon went down on Horizon. Five days later 3.4.4 removed the default-on behaviour.

---

## Q2. Configuration knobs in 3.4.7 and 4.0.10

All names below were read in source. They are the same in both versions unless a line says otherwise.

### Settings and environment variables (CONFIRMED)

- `fastmcp/settings.py`. The settings class reads environment variables with prefix `FASTMCP_` and nested delimiter `__`: 3.4.7 lines 139-143, 4.0.10 lines 37-41.
  - `http_host_origin_protection: bool | Literal["auto"] = False` (3.4.7:343, 4.0.10:280), environment variable `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION`.
  - `http_allowed_hosts: list[str] | None = None` (3.4.7:344, 4.0.10:281), environment variable `FASTMCP_HTTP_ALLOWED_HOSTS`. The value is a JSON list, for example `'["biosciences-mcp.fastmcp.app"]'`.
  - `http_allowed_origins: list[str] | None = None` (3.4.7:345, 4.0.10:282), environment variable `FASTMCP_HTTP_ALLOWED_ORIGINS`.
- The same environment variable names are documented in [gofastmcp.com/deployment/http#host-and-origin-protection](https://gofastmcp.com/deployment/http) (`docs/deployment/http.mdx` lines 104-150 at v4.0.10).

### Method parameters (CONFIRMED)

- `fastmcp/server/mixins/transport.py`:
  - `run_http_async(..., host_origin_protection: HostOriginProtection | None = None, allowed_hosts: list[str] | None = None, allowed_origins: list[str] | None = None, ...)`: 3.4.7 lines 258, 271-273; 4.0.10 lines 258, 271-273. `run(transport="http", **kw)` forwards to it.
  - `http_app(..., host_origin_protection=None, allowed_hosts=None, allowed_origins=None)`: 3.4.7 lines 370, 379-381; 4.0.10 lines 372, 381-383. Each `None` falls back to `fastmcp.settings.*` (3.4.7:430-446; 4.0.10:436-452).
  - `HostOriginProtection = bool | Literal["auto"]` (`http.py:39`). The middleware mode is `Literal["auto", "strict"]` (`http.py:40`).
- `create_streamable_http_app(..., host_origin_protection: HostOriginProtection = False, allowed_hosts=None, allowed_origins=None)`: 3.4.7 `http.py:552-554`, 4.0.10 `http.py:556-558`.
  - Any value other than `True`/`False`/`"auto"` raises `ValueError` (3.4.7:639-640; 4.0.10:649-650).
  - The middleware is inserted **only if `host_origin_protection is not False`**. `True` maps to `mode="strict"` and `"auto"` maps to `mode="auto"` (3.4.7:642-651; 4.0.10:652-661).
- No `FastMCP(...)` constructor argument controls the guard.
- The `fastmcp run` CLI has no flag for it (`grep host_origin|allowed_hosts` over `fastmcp/cli/*.py` in 4.0.10: no hits).
- The `fastmcp.json` `deployment` block has no field for it. The `Deployment` model fields are `transport`, `host`, `port`, `path`, `log_level`, `cwd`, `env`, `args` (4.0.10 `fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py:36-82`).

### How each mode behaves (CONFIRMED, 4.0.10 `http.py`; 3.4.7 is the same logic at offsets −2)

- Default `False`: the middleware is not installed, so every Host is accepted.
- `True` (strict): every request is validated against `DEFAULT_HOSTS`, plus `allowed_hosts`, plus the socket address it arrived on when that address is not unspecified (`_allowed_hosts_for_scope`, lines 310-320).
- `"auto"`, with no explicit `allowed_hosts`: Host is validated only when `scope["server"][0]` is loopback (`_should_validate_host`, lines 281-286; `_is_loopback_host`, lines 133-141). `scope["server"]` is the local address of the accepted socket, not the configured bind address.
- `"auto"` with explicit `allowed_hosts` behaves like strict (`has_explicit_allowed_hosts`, line 241 / 282).
- In `run_http_async`, `"auto"` with a loopback bind host also adds that host to the allowlist, which in turn makes validation strict (`_resolve_allowed_hosts_for_run`, `transport.py:52-65`).
- Origin checking returns 403 `"Forbidden Origin"`, separately from Host checking (lines 258-275).

Reproduction (fastmcp 4.0.10 and 3.4.7 behave the same; bound to `0.0.0.0`; requests sent to 127.0.0.1 and to the LAN IP):

| Env | via 127.0.0.1, public Host | via LAN IP, public Host |
|---|---|---|
| (defaults) | 200 | 200 |
| `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=auto` | **421** | 200 |
| `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true` | **421** | **421** |
| `FASTMCP_HTTP_ALLOWED_HOSTS=["biosciences-mcp.fastmcp.app"]` only | 200 (guard not installed) | 200 |
| `...=true` + `ALLOWED_HOSTS=["biosciences-mcp.fastmcp.app"]` | 200 | 200 |
| `...=auto` + `ALLOWED_HOSTS=["*.fastmcp.app"]` | 200 | 200 |

`fastmcp.json` `deployment.env` does not reach the guard (CONFIRMED by experiment on 4.0.10):

- With `"deployment": {"env": {"FASTMCP_HTTP_HOST_ORIGIN_PROTECTION": "true"}}` and `fastmcp run fastmcp.json --skip-env`, a public Host gets **200**, meaning the guard is not enabled.
- With the same variable set in the process environment, the result is **421**.
- Cause: `fastmcp/__init__.py:20` builds `settings = Settings()` at import time. `Deployment.apply_runtime_settings()` (`mcp_server_config.py:84-105`, called from `fastmcp/cli/run.py:136`) writes `os.environ` afterwards.
- Implication: anything in the `FASTMCP_*` settings family must be set in the Horizon console environment, not in `fastmcp.json`.

### How a deployment on Horizon should set it

- **Recommended: set nothing.** On 3.4.4 and later, and on 4.0.x, the default `False` accepts the `*.fastmcp.app` Host. No code or configuration change is needed. **CONFIRMED** for the framework. Horizon's runtime was not observed directly (INFERRED).
- If hardening is ever wanted, set both `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true` and `FASTMCP_HTTP_ALLOWED_HOSTS='["biosciences-mcp.fastmcp.app"]'` in the Horizon console. The equivalent code is `mcp.http_app(host_origin_protection=True, allowed_hosts=[...])`.
  - **Risk:** this only works if Horizon's ingress forwards the public Host unchanged. The guard reads the raw `Host` header only (#4468). That the 3.4.3 outage happened tells us the Host arriving at the pod was not localhost. It does not tell us whether it was the public name or an internal name (INFERRED). Verify on a preview deployment before relying on it.
- Do **not** use `"auto"` on Horizon. If the platform proxies over loopback inside the pod, auto mode validates and returns 421 (reproduced above). Even if it does not, auto mode gives no protection to a non-loopback-bound server.
- The guidance in Edge commit d4b9502 ("unpin and set `FASTMCP_HTTP_ALLOWED_HOSTS`") is incomplete for 3.4.4+/4.x. On its own that variable does nothing, because protection defaults to `False`. Simply unpinning is enough.

### Is it automatically relaxed when not bound to localhost?

- Under the defaults (3.4.4+, 4.x): the question does not arise, because the guard is off.
- In `"auto"` mode: yes in effect. Host is not validated unless the accepting socket is loopback, and the decision uses the socket address, not the configured bind host. Strict mode (`True`) is never relaxed. **CONFIRMED**.

### Forward risk

- Issue [#5213](https://github.com/PrefectHQ/fastmcp/issues/5213) (open, 2026-09-22, labels bug/http/security) asks to make `"auto"` or `True` the default. A comment on 2026-09-27 traces the history: default-on in 3.4.3 broke deployments, `"auto"` in #4439 still broke loopback-behind-proxy setups, and #4472/#4474 made it opt-in. The comment says any change would come in a 4.x minor with a deprecation warning first, or in FastMCP 5, and might wait for trusted-proxy support.
- Recommendation: pin a minor-bounded range (for example `fastmcp>=4.0.10,<4.1`) and add a post-deploy smoke test, `curl -H 'Host: biosciences-mcp.fastmcp.app'` returning something other than 421. INFERRED recommendation.

---

## Q3. Does FastMCP Cloud / Prefect Horizon support FastMCP 4.x?

| Evidence | What it shows | Label |
|---|---|---|
| [gofastmcp.com/deployment/prefect-horizon](https://gofastmcp.com/deployment/prefect-horizon) (v4 docs; the v3 copy is at [/v3/deployment/prefect-horizon](https://gofastmcp.com/v3/deployment/prefect-horizon)) | The v4 docs describe Horizon Deploy with no version restriction. "Horizon will automatically detect your server's Python dependencies from either a `requirements.txt` or `pyproject.toml`." The entrypoint "has the same syntax as the `fastmcp run` command". The URL form is `https://your-server-name.fastmcp.app/mcp`. Compared with the v3 page, the v4 page only adds a "FastMCP CLI Account" section (`fastmcp login`/`whoami`/`logout`, `HORIZON_API_KEY`). | CONFIRMED |
| [v4.0.0 release notes](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.0.0) | Include "Add Prefect Horizon authentication client and local state" (#4785) and "Add Prefect Horizon account commands" (#4786). 4.0.10 `fastmcp --help` lists `login`, `logout`, `whoami`. `fastmcp/cli/deploy/horizon_client.py:23` has `DEFAULT_HORIZON_API_ORIGIN = "https://horizon.prefect.io"`. There is still no `deploy` subcommand. | CONFIRMED |
| Issue [#3184](https://github.com/PrefectHQ/fastmcp/issues/3184) (Feb 2026) | The Horizon build log shows `fastmcp inspect -f fastmcp -o log.json "server.py:mcp"` running on `/usr/local/lib/python3.12/site-packages`, using the repo's pinned `fastmcp>=3.0.0rc1`. So Horizon runs the repo-resolved fastmcp version on Python 3.12. | CONFIRMED for 3.0rc1; for 4.x INFERRED |
| GitHub search, PrefectHQ/fastmcp issues: "421", "Misdirected Request", "Horizon", "fastmcp.app", "FastMCP Cloud", "Horizon 4.0", "host_origin_protection", "allowed_hosts" | Only #4468 (3.4.3, reverse proxy, closed by #4472) and #5213 (default-off complaint, open) relate to the guard. **No issue reports 421 or deploy failures for FastMCP 4.x on Horizon/FastMCP Cloud.** | CONFIRMED (absence as of 2026-09-30) |
| Version-support matrix | None found in the docs or release notes. | CONFIRMED (absence) |

Conclusions:

- Horizon is version-agnostic: it installs whatever `uv`/pip resolves from the repo (INFERRED, strong). The `fastmcp.json` `$schema` URL `.../fastmcp.json/v1.json` and the `Deployment` model are unchanged between 2.14.5 and 4.0.10 (`diff` shows only type-ignore comment changes), so the current `fastmcp.json` stays valid.
- Horizon's runtime is Python 3.12 (from #3184). That satisfies 4.0.10.
- One open question is whether Horizon's own build steps (`fastmcp inspect -f fastmcp`) work against a 4.x server. `inspect` still exists in 4.0.10's CLI (CONFIRMED), but this has not been run on Horizon. **Gate the upgrade on a Horizon PR preview deployment.** The docs say Horizon "builds preview deployments for every PR".

---

## Q4. FastMCP 4.0 breaking changes relevant to this codebase

Official guides:

- **3.x → 4.0:** [gofastmcp.com/getting-started/upgrading/from-fastmcp-3](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3). Source: `docs/getting-started/upgrading/from-fastmcp-3.mdx` @ v4.0.10, 459 lines.
- **2.x → 3.0:** [gofastmcp.com/getting-started/upgrading/from-fastmcp-2](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2). Source: `.../from-fastmcp-2.mdx` @ v4.0.10, 460 lines.
- Release notes: [v4.0.0](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.0.0) ("Breaking changes: server-initiated sampling and roots are removed ... `ctx.elicit()` is old-protocol-only, FastMCP 3's deprecated APIs are gone, MCP model fields are snake_case (with a warning compatibility bridge ...), and background tasks moved to `fastmcp-tasks`").

### 4a. `mount()` signature (CONFIRMED)

- 4.0.10 `fastmcp/server/server.py:2318-2322`: `def mount(self, server, namespace: str | None = None, tool_names: dict[str, str] | None = None) -> None`. **`prefix` and `as_proxy` are removed.** Passing either raises `TypeError` (the parameter list was printed by the probe).
- 3.4.7 `server.py:2124-2130`: `mount(self, server, namespace=None, as_proxy=None, tool_names=None, prefix=None  # deprecated, use namespace)`.
- 2.14.5: `mount(server, prefix, as_proxy, tool_names)`.
- Guide (from-fastmcp-3.mdx lines 269-281): `mount(sub, prefix="x")` becomes `mount(sub, namespace="x")`. `mount(sub, as_proxy=True)` becomes "wrap with `create_proxy(sub)`, then `mount` the proxy". "Either way, the child's lifespan and middleware now run".
- The 3.0 guide (from-fastmcp-2.mdx lines 340-347) marked `prefix` deprecated, "Removed in v4".
- Core's `gateway.py` passes `as_proxy=False` in all 12 calls (lines 54-156 in this worktree), plus `prefix=`. Both must go; PR #18 already drops them.

### 4b. Tool and MCP model field renames (CONFIRMED)

- The SDK v2 renames Python attributes to snake_case: `inputSchema` → `input_schema`, `outputSchema` → `output_schema`, `isError` → `is_error`, `structuredContent` → `structured_content`, `mimeType` → `mime_type`, `nextCursor`, and others. The wire JSON keeps camelCase aliases (from-fastmcp-3.mdx line 8: "The wire format does not change").
- The compatibility bridge routes camelCase reads to the new names with a `FastMCPDeprecationWarning` (guide lines 107-122). The setting is `mcp_camelcase_compat: bool = True` (4.0.10 `settings.py:123-...`), and the environment variable is `FASTMCP_MCP_CAMELCASE_COMPAT=false` (guide).
- FastMCP's own `Tool` model (4.0.10 `fastmcp/tools/base.py:236-255`) keeps `parameters` and `output_schema`. `to_mcp_tool` maps them to `input_schema=` and `output_schema=` (lines 291-292).
- Core's `src/` and `tests/` do not read `inputSchema`/`isError`/`outputSchema` attributes. `grep` found none. The contract tests use `result.data`/`result.text`.
- Protocol types moved to the `mcp_types` package and are re-exported as `mcp.types` (guide lines 134-142).

### 4c. Docstring parsing (CONFIRMED, introduced in 3.2.4, not 4.0)

- Introduced by PR [#3872](https://github.com/PrefectHQ/fastmcp/pull/3872), "Extract parameter descriptions from docstrings", in **v3.2.4** (2026-04-14; `docs/changelog.mdx` lines 1186-1201). The wheel check agrees: `fastmcp/utilities/docstring_parsing.py` is absent in 3.2.0 and present in 3.3.0. Edge's 3.0.2 lock predates it.
- Implementation, 4.0.10 `fastmcp/utilities/docstring_parsing.py:33-67`. The file is identical to 3.4.7 apart from a lazy import.
  - It tries the Google, NumPy and Sphinx parsers through griffe.
  - The **description is the first `text` section only** (lines 56-58).
  - The parameters come from the `parameters` section (lines 59-61).
  - **All other sections are discarded, including `Returns:`, `Raises:`, `Examples:`, and any text after `Args:`.**
  - If no parser finds parameters, the full docstring is returned unchanged (lines 66-67). A tool with `Returns:` but no `Args:` therefore keeps its `Returns:` text.
- `fastmcp/tools/function_parsing.py:304-347` injects the parameter descriptions into the JSON schema `properties.<name>.description`. An explicit `Field(description=...)` or `Annotated` wins (PR #3872 body).
- **`Returns:` text is dropped. It does not go into the output schema description.** The output schema comes from the return annotation only. Probe result for a `-> dict` tool with `Args:` and `Returns:`:
  - 2.14.5: description is the full docstring including `Args:` and `Returns:`; the inputSchema has no per-parameter descriptions.
  - 3.4.7 and 4.0.10: description is `"Search HGNC for genes by symbol.\n\nFuzzy discovery step."`, and inputSchema properties carry `"description": "Gene symbol or name, e.g. BRCA1."` and so on.
  - In all three, `outputSchema` is `{"additionalProperties": true, "type": "object"}`, with no `Returns` text anywhere.
- Implication for Core: any agent-facing guidance currently written in `Returns:` (for example, envelope shape hints) disappears from `tools/list` on 3.2.4+ and 4.x. Move it into the summary text above `Args:`, or into return-model `Field` descriptions. INFERRED recommendation.

### 4d. Tool argument validation errors (CONFIRMED)

- Probe: in-memory `Client(mcp)` plus HTTP `Client(url)`, with 4.0.10 in both `mode="auto"` and `mode="legacy"`.

| Case | 2.14.5 | 3.4.7 | 4.0.10 (auto & legacy, HTTP and in-memory) |
|---|---|---|---|
| wrong type (`page_size="abc"`) | `CallToolResult isError=true`, text = pydantic message | same | same |
| extra arg (`bogus=1`) | `isError=true` (`unexpected_keyword_argument`) | same | same |
| missing required | `isError=true` | same | same |
| coercible `"5"` → int | success | success | success |

- None of these raise a JSON-RPC error.
- 4.0.10 `fastmcp/server/server.py:1504-1516` catches the `ValidationError` and logs `"Invalid arguments for tool %r"`, with a summary of error types only, no input values. The exception then becomes an `isError` tool result.
- Server log detail is lower in 4.0.10: it logs `{'error_count', 'error_types'}`, where 3.4.7 logged the full pydantic errors including input values.
- **`additionalProperties: false` (new in 3.x and 4.x input schemas) does not change server behaviour.** Extra arguments were already rejected in 2.14.5. The risk is only on the client side: clients that validate against the schema now refuse earlier.
- Other wire error changes in 4.0: resource-not-found and prompt-not-found use code `-32602`, previously `-32002` (PR [#4445](https://github.com/PrefectHQ/fastmcp/pull/4445); guide line 394). Core exposes no resources, so this is not relevant. Unknown-tool behaviour was not probed (INFERRED unchanged; raises `NotFoundError`, `server.py:1501-1502`).

### 4e. Lifespan API in 4.0.10 (CONFIRMED)

- Constructor: `FastMCP(..., lifespan: LifespanCallable | Lifespan | None = None, ...)` (4.0.10 `fastmcp/server/server.py:323`).
- `LifespanCallable = Callable[["FastMCP[LifespanResultT]"], AbstractAsyncContextManager[LifespanResultT]]` (lines 224-226).
- Composable form, in `fastmcp/server/lifespan.py`:
  - `LifespanFn = Callable[["FastMCP[Any]"], AsyncIterator[dict[str, Any] | None]]` (line 55).
  - `class Lifespan` (line 61) supports composition with `|`.
  - `def lifespan(fn: LifespanFn) -> Lifespan` is a decorator (line 176). Usage: `@lifespan async def x(server): yield {...}`, then `FastMCP("s", lifespan=a | b)`. `ContextManagerLifespan` wraps a legacy `@asynccontextmanager`.
  - Unchanged from 3.4.7 apart from typing casts (diff).
- Over HTTP the lifespan is now driven by the SDK session manager: "Drive the FastMCP lifespan through the SDK session manager" (#4446) and "Test lifespan fires once per process over HTTP" (#4480), both in the v4.0.0 notes. See also 4.0.10 `http.py:683-686`.
- A mounted child's lifespan runs, entered at server start and not per request (guide line 281).
- Read through `ctx.lifespan_context` (4.0.10 `fastmcp/server/context.py:418`).
- Neither repo uses a lifespan today.

### 4f. Context API changes (CONFIRMED)

- Removed in 4.0.10: `ctx.sample`, `ctx.sample_step`, `ctx.list_roots`. They are absent from `fastmcp/server/context.py`, and the guide says they raise `AttributeError`.
- `ctx.elicit(...)` overloads (lines 958-1017) now require `response_type`. They raise on 2026-07-28 (sessionless) connections; use the guard pattern / `InputRequiredResult` instead.
- `ctx.set_state`/`get_state` (lines 1110, 1164) do not persist across requests on sessionless connections.
- `Middleware.on_initialize` never runs on sessionless connections.
- Middleware `on_message`/`on_request` now see every inbound message, including notifications and invalid requests (guide line 390).
- Kept: `ctx.info`/`debug`/`warning`/`error`/`log`, `report_progress`, `read_resource`, `request_context`, `session_id`.
- Core does not use `Context` (grep of `src/` and `tests/`).
- Other removals listed in the guide that do not affect this codebase: `FastMCP.as_proxy`, `import_server`, tool `serializer=`/`exclude_args=`, `FASTMCP_DECORATOR_MODE`, `McpError(ErrorData(...))`, `httpx` → `httpx2` inside FastMCP (Core's own clients use `httpx` independently, which is unaffected), and tasks moving to `fastmcp-tasks`.

### 4g. `fastmcp.json` and deployment schema (CONFIRMED)

- `fastmcp/utilities/mcp_server_config/v1/mcp_server_config.py`: `diff` between 2.14.5 and 4.0.10 shows only type-ignore comment changes, and `schema.json` is identical. `Deployment` fields are `transport` (`stdio|http|sse|streamable-http`), `host`, `port`, `path`, `log_level`, `cwd`, `env`, `args` (4.0.10 lines 36-82).
- Core's `fastmcp.json` (`source.path`/`entrypoint`, `environment.python`/`project`, `deployment.transport: http`, `log_level: INFO`) needs no change.
- Caveat from Q2: `deployment.env` cannot set `FASTMCP_*` settings for the guard, because they are read at import, before `apply_runtime_settings`.

### Environment floors in 4.0 (CONFIRMED, guide lines 95-103)

- Pydantic ≥ 2.12.
- Starlette ≥ 1.0.1 for the server extra; FastAPI ≥ 0.133.0 if it is co-installed.
- mcp ≥ 2.0 (2.2.0 resolved); `mcp-types`; `httpx2`.

---

## Reproduction artefacts (scratch, not in any checkout)

`/tmp/claude-1000/-home-donbr-open-biosciences-biosciences-mcp/b10d4503-f44c-4318-86bb-c652dcff1883/scratchpad/`:

- `envs/v{2.14.5,3.4.2,3.4.3,3.4.7,4.0.10}/`: throwaway venvs.
- `envs/dl/`: unzipped wheels (fastmcp-slim 3.4.4/3.4.5/3.4.6/4.0.0; fastmcp 3.0.2-3.4.0; mcp 1.26.0).
- `probe/probe.sh`, `probe/server.py`: Host-header probe.
- `probe/fastmcp.json`: the `deployment.env` experiment.
- `probe/behav.py`, `probe/httpval.py`: docstring, schema and validation probes.
- `docs/`: upgrade guides, changelog, `http.mdx`, Horizon pages as fetched.
