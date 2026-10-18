import http.server
import threading


class ServidorDeArquivos:
    def __init__(self, mapa, codigo_padrao=404):
        class Atendente(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                corpo = mapa.get(self.path)
                if corpo is None:
                    self.send_response(codigo_padrao)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *args):
                pass

        self.servidor = http.server.HTTPServer(("127.0.0.1", 0), Atendente)
        threading.Thread(target=self.servidor.serve_forever,
                         daemon=True).start()

    @property
    def base(self):
        return f"http://127.0.0.1:{self.servidor.server_port}"

    def fechar(self):
        self.servidor.shutdown()
        self.servidor.server_close()
