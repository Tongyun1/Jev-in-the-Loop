# Security and privacy

The currently implemented module is Jev-in-the-Loop: Browser. Read its
[security and privacy policy](plugins/jev-browser-plugin/SECURITY.md) before use.

Browser tasks send goals, supplied text and visible page/control information to TypeSafe.
Chrome remote debugging grants broad access to its profile. Use public, non-sensitive pages
and keep debugging access local. Heuristic stops are not a complete security boundary.

Keep secrets and browser-session data outside this repository. Use the empty configuration
template in the Browser module. Do not include private data or credentials in issues or examples.
No private security-reporting channel has been configured for this pre-release yet.
