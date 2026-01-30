import cv2
import math
import json
import os

# --- FUNÇÕES DE MATEMÁTICA/VISUAL ---

def count_fingers(hand_landmarks):
    """Conta os dedos levantados."""
    contador = 0
    pulso = hand_landmarks.landmark[0]
    
    # Dedão
    ponta_dedao = hand_landmarks.landmark[4]
    art_dedao = hand_landmarks.landmark[3]
    if abs(ponta_dedao.x - art_dedao.x) > 0.05:
        if abs(ponta_dedao.x - hand_landmarks.landmark[17].x) > 0.2:
             contador += 1

    # Outros 4 dedos
    pontas = [8, 12, 16, 20]
    articulacoes = [6, 10, 14, 18]
    for ponta, art in zip(pontas, articulacoes):
        p_obj = hand_landmarks.landmark[ponta]
        a_obj = hand_landmarks.landmark[art]
        dist_ponta = math.hypot(p_obj.x - pulso.x, p_obj.y - pulso.y)
        dist_art = math.hypot(a_obj.x - pulso.x, a_obj.y - pulso.y)
        if dist_ponta > dist_art:
            contador += 1
    return contador

def draw_modern_overlay(img, progresso, texto_principal, texto_secundario=""):
    """
    Desenha uma interface HUD moderna transparente sobre a imagem.
    """
    h_img, w_img, _ = img.shape
    
    # 1. Criar uma cópia para fazer o efeito de vidro (transparência)
    overlay = img.copy()
    
    # --- Configuração do Painel Inferior ---
    # Desenhamos um retângulo preto na parte de baixo
    cv2.rectangle(overlay, (0, h_img - 80), (w_img, h_img), (0, 0, 0), -1)
    
    # --- Painel Superior (Status) ---
    # Desenhamos um painel menor no topo para mensagens
    cv2.rectangle(overlay, (0, 0), (w_img, 50), (10, 10, 10), -1)

    # 2. Aplicar transparência (Alpha Blending)
    # alpha 0.4 significa 40% de opacidade do retângulo preto
    alpha = 0.6
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    # --- Barra de Progresso (Glow Effect) ---
    # Barra de fundo (cinza)
    bar_x, bar_y, bar_w, bar_h = 50, h_img - 40, w_img - 100, 10
    cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (100, 100, 100), -1)
    
    # Cor dinâmica (Vermelho -> Amarelo -> Verde Neon)
    if progresso < 0.3: cor = (50, 50, 255)    # Vermelho
    elif progresso < 0.8: cor = (0, 255, 255)  # Amarelo
    else: cor = (50, 255, 50)                  # Verde Neon

    # Barra preenchida
    fill_w = int(bar_w * progresso)
    if fill_w > 0:
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), cor, -1)

    # --- Textos (Clean Typography) ---
    # Texto Central (Ação)
    fonte = cv2.FONT_HERSHEY_DUPLEX # Fonte mais limpa que a Simplex
    cv2.putText(img, texto_principal, (bar_x, bar_y - 15), fonte, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Texto Secundário (Status no Topo)
    if texto_secundario:
         cv2.putText(img, texto_secundario, (20, 35), fonte, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
         
    # Contador de dedos (Canto direito inferior, estilo "Score")
    # Vamos desenhar um circulo visual
    cv2.circle(img, (w_img - 50, h_img - 40), 30, (255, 255, 255), 2, cv2.LINE_AA)

# --- FUNÇÕES DE ARQUIVO (NOVO) ---

def load_json_config(caminho):
    """Carrega configuração e garante estrutura correta."""
    padrao = {"volume": 1.0, "gestures": {}, "aliases": {}} # Nova estrutura padrão
    
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r') as f:
                data = json.load(f)
                
                # Migração 1: Formato antigo só com gestos
                if "gestures" not in data:
                    data = {"volume": 1.0, "gestures": data}
                
                # Migração 2: Adicionar aliases se não existir
                if "aliases" not in data:
                    data["aliases"] = {}
                    
                return data
        except:
            return padrao
    return padrao

def save_json_config(caminho, dados):
    try:
        with open(caminho, 'w') as f:
            json.dump(dados, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar config: {e}")