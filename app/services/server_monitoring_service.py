import threading
import time
from datetime import datetime

class ServerMonitoringService:
    def __init__(self):
        self.last_ping_time = datetime.now()
        self.is_server_active = True
        self.keep_alive_thread = None

    def start_keep_alive(self):
        """
        Iniciar thread de keep-alive
        """
        self.keep_alive_thread = threading.Thread(target=self._keep_alive, daemon=True)
        self.keep_alive_thread.start()

    def _keep_alive(self):
        """
        Método interno para mantener el servidor activo
        """
        while self.is_server_active:
            try:
                print(f"Server keep-alive check: {datetime.now()}")
                time.sleep(30)  # Check cada 30 segundos
            except Exception as e:
                print(f"Keep-alive error: {e}")

    def stop_keep_alive(self):
        """
        Detener el thread de keep-alive
        """
        self.is_server_active = False
        if self.keep_alive_thread:
            self.keep_alive_thread.join()

    def ping(self):
        """
        Actualizar tiempo de último ping
        
        :return: Información de estado del servidor
        """
        current_time = datetime.now()
        self.last_ping_time = current_time
        
        return {
            "status": "active",
            "timestamp": current_time.isoformat(),
            "uptime": "active"
        }