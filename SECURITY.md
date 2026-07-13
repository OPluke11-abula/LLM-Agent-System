# Security policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Email
`we.are.findai@gmail.com` with a concise description, affected version or
commit, reproduction steps, and impact. Redact API keys, tokens, personal data,
and customer information.

We will acknowledge a report when practicable and coordinate a fix or mitigation
before public disclosure. This project is local-first; do not include private
workspace files in a report unless they are required to reproduce the issue.

## Supported versions

Only the latest `main` revision and the latest published release receive
security fixes. The 0.1.1 installer is unsigned; verify its checksum in
[`releases/README.md`](releases/README.md) before running it.

## Secure operation

- Bind development services to loopback unless remote access is intentional.
- Keep provider credentials in environment variables or an external secret
  store; never commit `.env` files.
- Treat generated code, imported skills, and workspace data as untrusted input.
