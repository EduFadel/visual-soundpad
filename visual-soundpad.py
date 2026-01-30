import cv2
import mediapipe as mp
import pygame
import os
import time
import math
import json
import threading
import tkinter as tk
from tkinter import filedialog

ARQUIVO_CONFIG = "config.json"

# --- AUDIO CONFIGURATION ---
try:
    # Pre-init to match VoiceMeeter defaults (48kHz)
    pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=4096)
    pygame.mixer.init()
except Exception as e:
    print(f"Error starting audio system: {e}")

# Global Variables
rodando_ia = False
config_audios = {} 
sons_carregados = {} 
VOLUME_GLOBAL = 1.0  # Default 100%

# --- ENGINE FUNCTIONS ---

def carregar_sons_na_memoria():
    """Reloads sounds into memory based on current config."""
    global sons_carregados, config_audios, VOLUME_GLOBAL
    print("--- Reloading Sounds ---")
    novos_sons = {}
    
    config_atual = config_audios.copy()
    
    for gesto_str, caminho in config_atual.items():
        if caminho and os.path.exists(caminho):
            try:
                qtd = int(gesto_str)
                som = pygame.mixer.Sound(caminho)
                # Aplica o volume salvo
                som.set_volume(VOLUME_GLOBAL)
                
                nome_arquivo = os.path.basename(caminho)
                novos_sons[qtd] = {"obj": som, "txt": nome_arquivo}
                print(f"[OK] Gesture {qtd}: {nome_arquivo}")
            except Exception as e:
                print(f"[ERROR] {caminho}: {e}")
    
    sons_carregados = novos_sons

def contar_dedos(hand_landmarks):
    """Counts extended fingers using geometric distance from wrist."""
    contador = 0
    pulso = hand_landmarks.landmark[0]

    # Thumb (Side logic)
    ponta_dedao = hand_landmarks.landmark[4]
    articulacao_dedao = hand_landmarks.landmark[3]
    if abs(ponta_dedao.x - articulacao_dedao.x) > 0.05:
        if abs(ponta_dedao.x - hand_landmarks.landmark[17].x) > 0.2:
             contador += 1

    # Other 4 fingers (Distance from wrist logic)
    pontas = [8, 12, 16, 20]
    articulacoes = [6, 10, 14, 18]
    for ponta_id, art_id in zip(pontas, articulacoes):
        ponta = hand_landmarks.landmark[ponta_id]
        art = hand_landmarks.landmark[art_id]
        dist_ponta_pulso = math.hypot(ponta.x - pulso.x, ponta.y - pulso.y)
        dist_art_pulso = math.hypot(art.x - pulso.x, art.y - pulso.y)
        if dist_ponta_pulso > dist_art_pulso:
            contador += 1
    return contador

def desenhar_barra(img, progresso, texto):
    """Draws the progress bar on the OpenCV window."""
    x, y, w, h = 50, 400, 540, 40
    cv2.rectangle(img, (x, y), (x + w, y + h), (50, 50, 50), -1)
    
    if progresso < 0.5: cor = (0, 0, 255)
    elif progresso < 1.0: cor = (0, 255, 255)
    else: cor = (0, 255, 0)
    
    largura_atual = int(w * progresso)
    cv2.rectangle(img, (x, y), (x + largura_atual, y + h), cor, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 2)
    cv2.putText(img, texto, (x + 10, y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

def loop_visao_computacional():
    """Main CV Loop running in a separate thread."""
    global rodando_ia
    
    mp_hands = mp.solutions.hands
    # MUDANÇA 1: max_num_hands=2 (Agora aceita duas mãos)
    hands = mp_hands.Hands(model_complexity=0, max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils
    
    cap = cv2.VideoCapture(0)
    
    gesto_sendo_analisado = -1
    inicio_contagem = 0
    ja_tocou = False
    TEMPO_ESPERA = 1.0 
    msg_topo = "AI Started. Minimize window."

    carregar_sons_na_memoria()

    while rodando_ia and cap.isOpened():
        success, img = cap.read()
        if not success: break

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        gesto_agora = 0 # Reinicia a contagem a cada frame

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                
                # MUDANÇA 2: += (Soma os dedos da mão esquerda com a direita)
                # Se tiver 1 mão com 5 dedos e outra com 2, o total será 7.
                gesto_agora += contar_dedos(hand_lms)
        
        # O resto da lógica continua igual...
        if gesto_agora != gesto_sendo_analisado:
            gesto_sendo_analisado = gesto_agora
            inicio_contagem = time.time()
            ja_tocou = False
            msg_topo = "Detecting..."
        else:
            tempo_decorrido = time.time() - inicio_contagem
            progresso = min(tempo_decorrido / TEMPO_ESPERA, 1.0)
            
            if gesto_agora in sons_carregados:
                if not ja_tocou:
                    info_barra = f"Hold... {int(progresso*100)}%"
                    desenhar_barra(img, progresso, info_barra)
                    if tempo_decorrido >= TEMPO_ESPERA:
                        try:
                            sons_carregados[gesto_agora]["obj"].play()
                            msg_topo = f"PLAYED: {sons_carregados[gesto_agora]['txt']}"
                            ja_tocou = True
                        except:
                            msg_topo = "Error playing sound"
                else:
                    desenhar_barra(img, 1.0, f"Success: {sons_carregados[gesto_agora]['txt']}")
            else:
                msg_topo = "No audio set for this gesture"

        cv2.rectangle(img, (0,0), (640, 50), (0,0,0), -1)
        cv2.putText(img, msg_topo, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(img, f"Fingers: {gesto_agora}", (20, 100), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
        
        cv2.imshow("AI VISION (Do not close, just minimize)", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            rodando_ia = False
            break
            
    cap.release()
    cv2.destroyAllWindows()
    hands.close()

# --- GUI INTERFACE ---

class SoundpadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Gesture Soundpad")
        self.root.geometry("600x650")
        self.root.configure(bg="#2b2b2b")
        
        self.labels_caminhos = {}
        
        # 1. Carrega configuração (Volume e Gestos)
        self.carregar_configuracao()
        
        lbl_titulo = tk.Label(root, text="Gesture Configuration", bg="#2b2b2b", fg="white", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=10)

        frame_grid = tk.Frame(root, bg="#2b2b2b")
        frame_grid.pack(pady=5, padx=10, fill="both", expand=True)

        for i in range(1, 11):
            col = 0 if i <= 5 else 1
            row = (i - 1) if i <= 5 else (i - 6)
            self.criar_slot(frame_grid, i, row, col)

        # --- VOLUME CONTROL ---
        frame_vol = tk.Frame(root, bg="#2b2b2b")
        frame_vol.pack(pady=10, fill="x", padx=20)
        
        lbl_vol = tk.Label(frame_vol, text="Master Volume:", bg="#2b2b2b", fg="#cccccc", font=("Arial", 10, "bold"))
        lbl_vol.pack(side="left")
        
        self.vol_scale = tk.Scale(frame_vol, from_=0, to=100, orient="horizontal", 
                                  bg="#2b2b2b", fg="white", highlightbackground="#2b2b2b",
                                  troughcolor="#555555", activebackground="#00ff00",
                                  command=self.atualizar_volume)
        
        # 2. Define o slider com o volume carregado do JSON
        self.vol_scale.set(VOLUME_GLOBAL * 100) 
        self.vol_scale.pack(side="left", fill="x", expand=True, padx=10)
        # ----------------------

        self.btn_action = tk.Button(root, text="START CAMERA", command=self.alternar_ia, 
                                    bg="#00ff00", fg="black", font=("Arial", 14, "bold"), height=2)
        self.btn_action.pack(pady=10, fill="x", padx=20)
        
        lbl_info = tk.Label(root, text="Configure VoiceMeeter before starting!", bg="#2b2b2b", fg="#aaaaaa")
        lbl_info.pack(pady=5)

    def criar_slot(self, parent, numero_gesto, row, col):
        frame_slot = tk.Frame(parent, bg="#3b3b3b", bd=1, relief="flat")
        frame_slot.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        parent.grid_columnconfigure(col, weight=1)

        lbl_num = tk.Label(frame_slot, text=f"{numero_gesto} Fingers:", bg="#3b3b3b", fg="#00ff00", font=("Arial", 10, "bold"), width=9)
        lbl_num.pack(side="left", padx=5)

        path_atual = config_audios.get(str(numero_gesto), "No sound")
        nome_arquivo = os.path.basename(path_atual) if path_atual != "No sound" else "..."
        
        lbl_arquivo = tk.Label(frame_slot, text=nome_arquivo, bg="#3b3b3b", fg="white", width=15, anchor="w")
        lbl_arquivo.pack(side="left", fill="x", expand=True)
        self.labels_caminhos[numero_gesto] = lbl_arquivo

        btn_limpar = tk.Button(frame_slot, text="❌", command=lambda: self.limpar_slot(numero_gesto), 
                               bg="#552222", fg="#ff5555", relief="flat", width=2)
        btn_limpar.pack(side="right", padx=2, pady=2)

        btn_sel = tk.Button(frame_slot, text="📂", command=lambda: self.selecionar_arquivo(numero_gesto), 
                            bg="#555", fg="white", relief="flat")
        btn_sel.pack(side="right", padx=2, pady=2)

    def atualizar_volume(self, valor_str):
        global VOLUME_GLOBAL
        novo_vol = float(valor_str) / 100.0
        VOLUME_GLOBAL = novo_vol
        
        if sons_carregados:
            for item in sons_carregados.values():
                if item["obj"]:
                    item["obj"].set_volume(VOLUME_GLOBAL)
        
        # Salva a configuração sempre que mexer no volume
        # (Para otimizar, poderia salvar só ao soltar o mouse, mas assim é mais seguro)
        self.salvar_configuracao()

    def limpar_slot(self, numero_gesto):
        str_num = str(numero_gesto)
        if str_num in config_audios:
            del config_audios[str_num]
            self.labels_caminhos[numero_gesto].config(text="...")
            self.salvar_configuracao()
            if rodando_ia:
                carregar_sons_na_memoria()

    def selecionar_arquivo(self, numero_gesto):
        arquivo = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if arquivo:
            config_audios[str(numero_gesto)] = arquivo
            self.labels_caminhos[numero_gesto].config(text=os.path.basename(arquivo))
            self.salvar_configuracao()
            if rodando_ia:
                carregar_sons_na_memoria()

    def salvar_configuracao(self):
        """Save both gestures and volume to JSON"""
        data = {
            "volume": VOLUME_GLOBAL,
            "gestures": config_audios
        }
        with open(ARQUIVO_CONFIG, 'w') as f:
            json.dump(data, f, indent=4)

    def carregar_configuracao(self):
        """Load gestures and volume intelligently"""
        global config_audios, VOLUME_GLOBAL
        if os.path.exists(ARQUIVO_CONFIG):
            try:
                with open(ARQUIVO_CONFIG, 'r') as f:
                    data = json.load(f)
                    
                    # Verifica se é o formato novo ou antigo
                    if "gestures" in data:
                        # Formato Novo v5.0
                        config_audios = data["gestures"]
                        VOLUME_GLOBAL = data.get("volume", 1.0)
                    else:
                        # Formato Antigo (Migração)
                        config_audios = data
                        VOLUME_GLOBAL = 1.0
            except:
                config_audios = {}
                VOLUME_GLOBAL = 1.0

    def alternar_ia(self):
        global rodando_ia
        if not rodando_ia:
            rodando_ia = True
            self.btn_action.config(text="STOP CAMERA", bg="#ff3333", fg="white")
            t = threading.Thread(target=loop_visao_computacional)
            t.daemon = True 
            t.start()
        else:
            rodando_ia = False
            self.btn_action.config(text="START CAMERA", bg="#00ff00", fg="black")

if __name__ == "__main__":
    root = tk.Tk()
    app = SoundpadApp(root)
    
    def on_closing():
        global rodando_ia
        rodando_ia = False
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()