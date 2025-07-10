import cv2
import os
import time
from datetime import datetime, timedelta
import threading

# ============ CONFIGURAÇÕES ============
cameras = {
    "cam1": "rtsp://usuario:senha@ip1:554/stream1",
    "cam2": "rtsp://usuario:senha@ip2:554/stream1"
}

diretorio_saida = "./gravacoes"
duracao_segmento = 30 * 60  # 30 minutos em segundos
quatrocc = cv2.VideoWriter_fourcc(*'mp4v')
fps_padrao = 25

os.makedirs(diretorio_saida, exist_ok=True)

# ============ FUNÇÃO PARA APAGAR VÍDEOS ANTIGOS (por câmera) ============
def apagar_videos_antigos(diretorio, nome_camera, dias=30):
    limite = datetime.now() - timedelta(days=dias)

    for arquivo in os.listdir(diretorio):
        caminho_completo = os.path.join(diretorio, arquivo)

        # Verifica se o arquivo pertence à câmera atual
        if nome_camera not in arquivo:
            continue
        
        if os.path.isfile(caminho_completo):
            mod_time = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
            if mod_time < limite:
                os.remove(caminho_completo)
                print(f"[LIMPEZA - {nome_camera}] Arquivo apagado: {arquivo}")

# ============ FUNÇÃO DE GRAVAÇÃO ============
def gravar_camera(nome_camera, url_rtsp):
    cap = cv2.VideoCapture(url_rtsp)
    if not cap.isOpened():
        print(f"[{nome_camera}] Erro ao abrir a câmera.")
        return

    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or fps_padrao

    print(f"[{nome_camera}] Iniciando gravação.")

    try:
        while True:
            agora = datetime.now()
            fim_segmento = agora + timedelta(seconds=duracao_segmento)
            nome_arquivo = os.path.join(
                diretorio_saida,
                f"{nome_camera}_{agora.strftime('%Y-%m-%d_%H-%M')}.mp4"
            )

            out = cv2.VideoWriter(nome_arquivo, quatrocc, fps, (largura, altura))
            print(f"[{nome_camera}] Gravando: {nome_arquivo}")

            while datetime.now() < fim_segmento:
                ret, frame = cap.read()
                if not ret:
                    print(f"[{nome_camera}] Erro ao capturar frame.")
                    break
                out.write(frame)

            out.release()

            # Apaga vídeos antigos após cada ciclo de gravação
            apagar_videos_antigos(diretorio_saida, nome_camera, dias=30)

    except KeyboardInterrupt:
        print(f"[{nome_camera}] Gravação interrompida.")
    finally:
        cap.release()
        print(f"[{nome_camera}] Recursos liberados.")

# ============ INICIALIZAÇÃO MULTICÂMERA ============
threads = []
for nome, url in cameras.items():
    t = threading.Thread(target=gravar_camera, args=(nome, url))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
