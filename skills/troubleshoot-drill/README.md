# troubleshoot-drill

Install:
1. Copy this folder to your agent's skills directory.
2. Create your data folder (default /opt/data/profiles/assistant/drill) and copy
   the three files from templates/ into it (or let the agent create them).
3. Edit config.md: set stack, areas, level_mode. Or just tell the agent
   "set my level to 3" / "add Proxmox to my stack".

Use: say "drill", answer with commands and checks, then state your cause and fix.
