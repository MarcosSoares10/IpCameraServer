import os
import time
from datetime import datetime, timedelta
import threading
from onvif import ONVIFCamera
import socket
import subprocess
import shutil

# Endpoint da camera descoberto com ODM
# ============ CONFIGURAÇÕES ============ 
cameras = {}

diretorio_saida = "F:/Videos"
diretorio_intermediario = "./Gravacoes"
duracao_segmento = 5 * 60  # 5 minutos em segundos

os.makedirs(diretorio_intermediario, exist_ok=True)
os.makedirs(diretorio_saida, exist_ok=True)

numerocamerasnolocal = 2

def ip_responde(ip, portas=[5000, 554], timeout=0.1):
    for porta in portas:
        try:
            with socket.create_connection((ip, porta), timeout=timeout):
                return True
        except Exception:
            continue
    return False

def descobrir_cameras_onvif(subrede="192.168.0.", portas=[5000, 554]):
    cameras_encontradas = []
    for i in range(1, 255):
        ip = f"{subrede}{i}"
        
        if not ip_responde(ip):
            print(f"{ip} não responde, pulando.")
            continue

        for porta in portas:
            print(f"Tentando ONVIF {ip}:{porta}")
            try:
                cam = ONVIFCamera(ip, porta, 'user', 'password', no_cache=True)
                info = cam.devicemgmt.GetDeviceInformation()
                print(f"Encontrada câmera ONVIF: {ip} - {info.Model}")
                cameras_encontradas.append(ip)
                break
            except Exception:
                print(f"Nao encontrada ONVIF {ip}:{porta}")
                continue
        
        if len(cameras_encontradas) >= numerocamerasnolocal:
            break
    return cameras_encontradas

# ============ FUNÇÃO PARA APAGAR VÍDEOS ANTIGOS (por câmera) ============
def apagar_videos_antigos(diretorio, nome_camera, dias=30):
    limite = datetime.now() - timedelta(days=dias)

    for arquivo in os.listdir(diretorio):
        caminho_completo = os.path.join(diretorio, arquivo)

        if nome_camera not in arquivo:
            continue
        
        if os.path.isfile(caminho_completo):
            mod_time = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
            if mod_time < limite:
                os.remove(caminho_completo)
                print(f"[LIMPEZA - {nome_camera}] Arquivo apagado: {arquivo}")

# ============ FUNÇÃO DE GRAVAÇÃO COM FFMPEG ============
def gravar_camera(nome_camera, url_rtsp):
    while True:
        agora = datetime.now()
        nome_arquivo_final = os.path.join(
            diretorio_intermediario,
            f"{nome_camera}_{agora.strftime('%Y-%m-%d_%H-%M')}.mp4"
        )

        # 1. Grava o stream original
        comando_gravar = [
            'ffmpeg',
            '-buffer_size', '2048k',
            '-use_wallclock_as_timestamps', '1',
            '-fflags', '+genpts+igndts',
            '-i', url_rtsp,
            '-t', str(duracao_segmento),
            '-c:v', 'libx265',
            '-c:a', 'aac',
            '-vsync', '1',
            '-y',
            nome_arquivo_final
        ]

        print(f"[{nome_camera}] Gravando arquivo: {nome_arquivo_final}")
        try:
            subprocess.run(comando_gravar, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[{nome_camera}] Erro ao gravar arquivo: {e}")
            time.sleep(5)
            continue

        destino = os.path.join(diretorio_saida, os.path.basename(nome_arquivo_final))
        if diretorio_intermediario != diretorio_saida:
            try:
                shutil.move(nome_arquivo_final, destino)
                print(f"[{nome_camera}] Arquivo movido para: {destino}")
            except Exception as e:
                print(f"[{nome_camera}] Erro ao mover arquivo: {e}")

        apagar_videos_antigos(diretorio_saida, nome_camera, dias=30)

# ============ INICIALIZAÇÃO MULTICÂMERA ============
ips_encontrados = descobrir_cameras_onvif()
for idx, ip in enumerate(ips_encontrados, 1):
    cameras[f"Camera_{idx}"] = f"rtsp://user:password@{ip}:554/onvif1"

print("Câmeras configuradas:", cameras)

threads = []
for nome, url in cameras.items():
    t = threading.Thread(target=gravar_camera, args=(nome, url))
    t.start()
    threads.append(t)
    time.sleep(1)

for t in threads:
    t.join()
