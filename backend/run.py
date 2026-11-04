import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Supporto Debugger Remoto (VS Code / PyCharm) tramite debugpy
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")
if DEBUG_MODE:
    try:
        import debugpy
        debugpy_port = int(os.getenv("DEBUG_PORT", "5678"))
        debugpy.listen(("0.0.0.0", debugpy_port))
        print(f"[DEBUGGER ATTIVO] debugpy in ascolto su 0.0.0.0:{debugpy_port}. Puoi agganciare VS Code (F5)!")
    except Exception as e:
        print(f"[DEBUGGER WARNING] Impossibile avviare debugpy: {e}")

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0" if os.path.exists("/.dockerenv") or os.getenv("DATABASE_URL", "").startswith("postgresql://") else "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    reload_enabled = os.getenv("RELOAD", "true" if DEBUG_MODE else "false").lower() in ("true", "1")

    print("=" * 65)
    print(">> ENTERPRISE SERVICE INSTANTIATOR - PORTALE AZIENDALE")
    print("=" * 65)
    print(f"Interfaccia Web Utente:        http://localhost:{port}")
    print(f"Documentazione API (Swagger):   http://localhost:{port}/docs")
    if DEBUG_MODE:
        print(f"Porta Debugger Remoto (debugpy): 5678")
    print("=" * 65)
    print("Premi Ctrl+C per arrestare il server.\n")

    uvicorn.run("app.main:app", host=host, port=port, app_dir=BASE_DIR, reload=reload_enabled)
