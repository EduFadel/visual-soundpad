import cv2
import mediapipe as mp
import pygame
import os
import time
import threading
import customtkinter as ctk

# Importando módulos locais
from interface import SoundpadInterface
from helpers import count_fingers, draw_modern_overlay, load_json_config, save_json_config

ARQUIVO_CONFIG = "config.json"

# --- 1. CONFIGURAÇÃO DE ÁUDIO (Anti-Delay) ---
try:
    # Frequência 48000Hz para casar com VoiceMeeter e evitar som "robô"
    pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=4096)
    pygame.mixer.init()
except Exception as e:
    print(f"Erro starting audio system: {e}")

# --- 2. VARIÁVEIS GLOBAIS ---
rodando_ia = False
sons_carregados = {} 

# Carrega a configuração inicial usando o helper
dados_config = load_json_config(ARQUIVO_CONFIG)

# --- 3. GERENCIAMENTO DE SONS ---

def reload_sounds():
    """Lê a configuração global e carrega os sons no Pygame."""
    global sons_carregados
    print("--- Reloading sounds ---")
    
    vol = dados_config.get("volume", 1.0)
    gestos = dados_config.get("gestures", {})
    aliases = dados_config.get("aliases", {}) # Pega os apelidos
    
    novos_sons = {}
    
    for gesto_str, caminho in gestos.items():
        if caminho and os.path.exists(caminho):
            try:
                qtd = int(gesto_str)
                som = pygame.mixer.Sound(caminho)
                som.set_volume(vol)
                
                # LÓGICA NOVA: Prioriza o Alias, senão usa nome do arquivo
                if gesto_str in aliases:
                    nome_exibicao = aliases[gesto_str]
                else:
                    nome_exibicao = os.path.splitext(os.path.basename(caminho))[0]
                
                novos_sons[qtd] = {"obj": som, "txt": nome_exibicao}
                print(f"[OK] Gesture {qtd}: {nome_exibicao}")
            except Exception as e:
                print(f"[ERRO] Error loading {caminho}: {e}")
    
    sons_carregados = novos_sons

# --- 4. CALLBACKS (Pontes entre Interface e Lógica) ---

def update_config_callback():
    """Chamado pela interface quando o usuário muda volume ou arquivos."""
    save_json_config(ARQUIVO_CONFIG, dados_config)
    reload_sounds()

def toggle_camera_callback():
    """Liga ou Desliga a thread da visão computacional."""
    global rodando_ia
    if not rodando_ia:
        rodando_ia = True
        # Inicia a thread como 'daemon' (morre junto com o app)
        threading.Thread(target=main_camera_loop, daemon=True).start()
    else:
        rodando_ia = False

# --- 5. LOOP DA VISÃO COMPUTACIONAL (O Coração da IA) ---

def main_camera_loop():
    global rodando_ia
    
    # Configuração do MediaPipe para 2 mãos
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(model_complexity=0, max_num_hands=2, min_detection_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils
    
    cap = cv2.VideoCapture(0)
    
    # Variáveis de controle de tempo
    gesto_analisado = -1
    inicio_contagem = 0
    ja_tocou = False
    
    # Textos para o Overlay
    status_topo = "Waiting for gesture..."
    msg_principal = "Starting..."
    
    # Garante que os sons estão atualizados ao abrir a câmera
    reload_sounds()

    while rodando_ia and cap.isOpened():
        success, img = cap.read()
        if not success: break

        # Espelha e converte cores
        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        gesto_agora = 0
        
        # Desenha esqueleto e conta dedos (Soma das duas mãos)
        if results.multi_hand_landmarks:
            ignorar_segunda_mao = False

            # Se detectar 2 mãos, verifica se elas não são a mesma (sobrepostas)
            if len(results.multi_hand_landmarks) == 2:
                pulso1 = results.multi_hand_landmarks[0].landmark[0]
                pulso2 = results.multi_hand_landmarks[1].landmark[0]
                
                # Calcula a distância entre os pulsos (horizontal e vertical)
                dist_x = abs(pulso1.x - pulso2.x)
                dist_y = abs(pulso1.y - pulso2.y)
                
                # Se a distância for menor que 10% da tela, considera duplicata
                if dist_x < 0.1 and dist_y < 0.1:
                    ignorar_segunda_mao = True

            # Loop para desenhar e contar
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                # Se marcamos para ignorar e este é o segundo item (índice 1), pula
                if i == 1 and ignorar_segunda_mao:
                    continue
                
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                gesto_agora += count_fingers(hand_lms)
        
        # --- Lógica de Timer (1 Segundo) ---
        if gesto_agora != gesto_analisado:
            gesto_analisado = gesto_agora
            inicio_contagem = time.time()
            ja_tocou = False
            status_topo = "Detecting..."
            progresso = 0.0
        else:
            tempo_decorrido = time.time() - inicio_contagem
            progresso = min(tempo_decorrido / 1.0, 1.0) # 1.0 segundo para ativar
            
            # Verifica se existe som para esse gesto
            if gesto_agora in sons_carregados:
                nome_som = sons_carregados[gesto_agora]['txt']
                
                if not ja_tocou:
                    msg_principal = f"Loading: {nome_som}"
                    status_topo = f"Hold... {int(progresso*100)}%"
                    
                    if tempo_decorrido >= 1.0:
                        try:
                            sons_carregados[gesto_agora]["obj"].play()
                            ja_tocou = True
                            msg_principal = f"Sound: {nome_som}"
                            status_topo = "Success!"
                        except:
                            msg_principal = "Error playing sound"
                else:
                    # Mantém a mensagem de sucesso enquanto segura o gesto
                    msg_principal = f"Sound: {nome_som}"
                    status_topo = "Release to restart"
            else:
                msg_principal = "No defined sound"
                status_topo = f"Fingers: {gesto_agora}"
                progresso = 0.0

        # --- Desenha o HUD Moderno ---
        # Usa a função nova do helpers.py com transparência
        draw_modern_overlay(img, progresso, msg_principal, status_topo)
        
        # Adiciona contador visual extra no canto
        h, w, _ = img.shape
        cv2.putText(img, str(gesto_agora), (w - 60, h - 35), 
                    cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)

        cv2.imshow("Visual Soundpad AI", img)
        
        # Tecla de emergência 'q' para fechar apenas a câmera
        if cv2.waitKey(1) == ord('q'):
            rodando_ia = False
            break
            
    cap.release()
    cv2.destroyAllWindows()
    hands.close()

# --- 6. INICIALIZAÇÃO DO APP ---

if __name__ == "__main__":
    # Importante: CustomTkinter exige ctk.CTk() em vez de tk.Tk()
    root = ctk.CTk()
    
    # Inicializa a Interface passando as funções de controle
    app = SoundpadInterface(
        root, 
        dados_config, 
        toggle_camera_callback, 
        update_config_callback
    )
    
    # Garante que tudo feche ao clicar no X
    def on_closing():
        global rodando_ia
        rodando_ia = False
        root.destroy()
        os._exit(0) # Força o encerramento de todas as threads
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()