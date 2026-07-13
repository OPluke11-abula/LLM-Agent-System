# Release evidence

## 0.1.1 Windows NSIS installer

| Field | Value |
| --- | --- |
| File | `ai-agent-topology-viewer_0.1.1_x64-setup.exe` |
| Platform | Windows x64 |
| Format | NSIS installer |
| Authenticode signature | **Not signed** |
| SHA-256 | `1D4A47DA57E60D641EFE729E7F347DBABCAE84033D1AF0EF45220CE0B6C49B47` |

Verify the tracked file before execution:

```powershell
Get-FileHash .\releases\ai-agent-topology-viewer_0.1.1_x64-setup.exe -Algorithm SHA256
```

The checksum is an integrity check, not a publisher signature. Build a fresh
installer with:

```powershell
npm.cmd --prefix viewer run tauri -- build --bundles nsis
```

MSI is not published because the current Windows WiX validation environment
does not pass ICE checks. No signing certificate or provenance attestation is
claimed for this release.
