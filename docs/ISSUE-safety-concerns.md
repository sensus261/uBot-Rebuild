# Title: Safety & trust review before running this build (checklist)

Tracking issue for risks to understand/verify before running uBot + `eXLib.mix` on a live
GameForge Metin2 account. Findings marked **Checked** come from a quick local inspection;
they are not a full audit.

## 1. `eXLib.mix` is an unreviewed prebuilt binary (highest risk)
It is loaded **inside the game process**, so it has the same access as the game itself.
- Committed as a binary, no CI, no reproducible build, no source in this repo
  (source: `ikevin127/MetinPythonLibV2-Rebuild`). SHA-256 of the committed file:
  `dc584b57f18ce59ac3d0f6099fc37451ba34b354ae167378c690d5db3fbcadf0`
- **Checked** — PE imports only `KERNEL32`, `USER32`, `SHLWAPI`, `python27.dll`. No
  WinSock / WinInet / WinHTTP imports, so no obvious direct networking code.
- **Checked** — leftover exported names `OpenWebsocket`, `SendWebsocket`, `CloseWebsocket`,
  `JWT_Token` (README says the server-comms code was stubbed out). Not verified that they
  are inert.
- **Open** — `CreateProcessW` is imported and I did not find where it is used.
- **Open** — no disassembly or sandbox run was done.
- [ ] Build the DLL from source and compare behaviour with the committed binary
- [ ] Review the DLL source for outbound connections / process creation / file writes
- [ ] Decide whether to replace the committed binary with a self-built one

## 2. Python scripts (`init.py`, `OpenBot/`)
- **Checked** — grep of the project's own `.py` files (excluding vendored `OpenBot/lib/`) found no
  `socket`, `urllib`, `requests`, `subprocess`, `os.system`, `ctypes`, `base64` or hardcoded
  hosts/IPs. The only URL is a forum link in a comment.
- `exec(...)` appears in `init.py` (module bootstrap) and in `PythonManager.py`
  (runs text typed into the "Python File Loader" box — local, but arbitrary code execution
  by design).
- **Open** — vendored `OpenBot/lib/` (`simplejson`, `decimal`, `numbers`, `struct`) not reviewed.
- [ ] Full read-through of `init.py` and `OpenBot/Modules/`
- [ ] Diff vendored libs against upstream

## 3. Account risk (ToS / anti-cheat)
- Automation and memory tampering violate Metin2's ToS; bans are possible.
- The client folder contains a `cheat_blocker/` directory and the client is packed/protected,
  so detection is plausible. This build adds no evasion.
- Some features (speed/teleport, spam) are more detectable and affect other players.
- [ ] Use a throwaway account only, with a unique password, 2FA, and no payment details
- [ ] Never run on a main account

## 4. Client version drift
- Targets GF **26.1.11**; tested on **26.2.10** and the hackbar loads.
- With drift, some signatures/offsets may be wrong. The loader logs
  `sendAddr=0x00000000 hooked=0` (send hook unresolved — documented as a TODO), and other
  features may silently misbehave.
- [ ] Re-validate signatures with the DLL repo's pattern tools after each client update

## 5. Supply chain / provenance
- This is a fork; upstream commits are authored by another person, and the README states the
  reverse engineering was AI-driven and validated in game only.
- [ ] Pin to a reviewed commit; read diffs (especially `eXLib.mix`) before pulling upstream
- [ ] Don't run `.exe`/injector downloads from forums

## 6. Verify behaviour at runtime
- [ ] Run once in a VM or Windows Sandbox
- [ ] Watch connections (TCPView / Resource Monitor): expect only the game/launcher endpoints
- [ ] Watch file/registry writes with Process Monitor; expected writes are logs next to
      `metin2client.exe` (e.g. `*_hook_init.txt`, `Phase1Diag.txt`, `OpenBot/Saves`)
- [ ] Check what the GameForge launcher does with unknown files in the client folder
      (repair/update may delete them, or flag them)

## 7. Housekeeping
- [ ] Review `ubot-deploy.ps1` before use (it only copies/removes `eXLib.mix`, `init.py`,
      `OpenBot/` and keeps `.ubot-backup` copies)
- [ ] Don't paste logs publicly without checking them for account/character names
