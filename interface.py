import customtkinter as ctk
from tkinter import filedialog
import os

# Configuração Global do Tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# --- Configurações de Estilo (Fontes e Tamanhos) ---
FONT_TITLE = ("Roboto Medium", 18)
FONT_NORMAL = ("Roboto", 12)
FONT_SMALL = ("Roboto", 10)
BTN_HEIGHT = 28 # Altura dos botões pequenos (X e Pasta)
BTN_MAIN_HEIGHT = 40 # Altura do botão Iniciar

def truncate_text(text, max_length=35):
    """Corta textos muito longos para não quebrar o layout."""
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

class SoundpadInterface:
    def __init__(self, root, config_inicial, callback_iniciar_ia, callback_atualizar_config):
        # ... (O __init__ continua igual, só lembre de garantir que aliases exista na config local se necessário, mas o helper já faz isso) ...
        self.root = root
        self.config = config_inicial
        self.callback_iniciar_ia = callback_iniciar_ia
        self.callback_atualizar_config = callback_atualizar_config
        self.labels_caminhos = {} 
        self.rodando = False
        
        # Garante que aliases existe localmente pra evitar erro visual
        if "aliases" not in self.config: self.config["aliases"] = {}

        # Configuração da Janela Principal (Mais estreita e alta)
        self.root.title("Visual Soundpad")
        self.root.geometry("400x700") # Tamanho compacto
        
        # --- Cabeçalho ---
        header_frame = ctk.CTkFrame(root, fg_color="transparent")
        header_frame.pack(pady=(15, 10))
        
        ctk.CTkLabel(header_frame, text="🖐️ Gesture Soundpad", font=FONT_TITLE).pack()
        ctk.CTkLabel(header_frame, text="Lista de Áudios", font=FONT_SMALL, text_color="gray").pack()

        # --- Lista de Slots (Scrollável) ---
        # Usamos pack para empilhar verticalmente
        self.main_frame = ctk.CTkScrollableFrame(root, corner_radius=10, fg_color="transparent")
        self.main_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # Cria os 10 slots em sequência vertical
        for i in range(1, 11):
            self.criar_slot_vertical(self.main_frame, i)

        # --- Rodapé (Volume e Iniciar) ---
        self.footer_frame = ctk.CTkFrame(root, fg_color=("#2b2b2b", "#2b2b2b"), corner_radius=15)
        self.footer_frame.pack(fill="x", side="bottom", pady=15, padx=15)

        # Slider de Volume (Mais compacto)
        vol_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        vol_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(vol_frame, text="Vol:", font=FONT_SMALL, width=30).pack(side="left")
        
        volume_inicial = self.config.get("volume", 1.0)
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=100, command=self.ao_mudar_volume, height=15)
        self.vol_slider.set(volume_inicial * 100)
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=10)

        # Botão Principal
        self.btn_action = ctk.CTkButton(self.footer_frame, text="INICIAR CÂMERA", 
                                        command=self.ao_clicar_start,
                                        height=BTN_MAIN_HEIGHT, font=("Roboto", 14, "bold"),
                                        fg_color="#2CC985", hover_color="#229A65")
        self.btn_action.pack(fill="x", padx=10, pady=(5, 15))

    def criar_slot_vertical(self, parent, numero_gesto):
        card = ctk.CTkFrame(parent, corner_radius=8, fg_color=("#3a3a3a", "#333333"), height=45)
        card.pack(pady=3, fill="x", anchor="n")

        # Número
        lbl_num = ctk.CTkLabel(card, text=str(numero_gesto), width=24, height=24, 
                                fg_color="#444444", corner_radius=12, font=("Arial", 12, "bold"))
        lbl_num.pack(side="left", padx=(8, 5), pady=8)

        # Nome do Arquivo / Alias
        str_num = str(numero_gesto)
        gestos = self.config.get("gestures", {})
        aliases = self.config.get("aliases", {})
        
        path_atual = gestos.get(str_num, None)
        
        if path_atual and os.path.exists(path_atual):
            # Se tiver alias, usa ele. Se não, usa nome do arquivo.
            if str_num in aliases:
                texto_base = aliases[str_num]
                cor_texto = "#4CC9F0" # Azul claro para indicar nome personalizado
            else:
                texto_base = os.path.basename(path_atual)
                cor_texto = "white"
                
            texto_display = truncate_text(texto_base, max_length=25)
        else:
            texto_display = "Selecionar áudio..."
            cor_texto = "gray"

        lbl_arquivo = ctk.CTkLabel(card, text=texto_display, font=FONT_NORMAL, 
                                   text_color=cor_texto, anchor="w")
        lbl_arquivo.pack(side="left", fill="x", expand=True, padx=5)
        self.labels_caminhos[numero_gesto] = lbl_arquivo

        # --- BOTÕES DE AÇÃO ---
        
        FONT_ICON = ("Segoe UI Emoji", 18) 

        # 1. Botão Lápis (Renomear)
        # Usei o emoji ✏️
        btn_edit = ctk.CTkButton(card, text="✏️", width=BTN_HEIGHT, height=BTN_HEIGHT, 
                                   fg_color="transparent", hover_color="#444444",
                                   font=FONT_ICON, text_color="#E67E22", # Laranja no texto
                                   command=lambda: self.renomear_som(numero_gesto))
        btn_edit.pack(side="right", padx=(0, 0))

        # 2. Botão Lixeira (Limpar)
        # Troquei o X pela Lixeira 🗑️ que é mais intuitiva
        btn_limpar = ctk.CTkButton(card, text="🗑️", width=BTN_HEIGHT, height=BTN_HEIGHT, 
                                   fg_color="transparent", hover_color="#444444",
                                   font=FONT_ICON, text_color="#E74C3C", # Vermelho no texto
                                   command=lambda: self.limpar_slot(numero_gesto))
        btn_limpar.pack(side="right", padx=0)

        # 3. Botão Pasta (Selecionar)
        # Usei a pasta aberta 📂
        btn_pasta = ctk.CTkButton(card, text="📂", width=BTN_HEIGHT, height=BTN_HEIGHT,
                                  fg_color="transparent", hover_color="#444444",
                                  font=FONT_ICON, text_color="#3498DB", # Azul no texto
                                  command=lambda: self.selecionar_arquivo(numero_gesto))
        btn_pasta.pack(side="right", padx=(5, 0))

    # --- FUNÇÃO NOVA ---
    def renomear_som(self, numero_gesto):
        str_num = str(numero_gesto)
        
        # Só permite renomear se já tiver um áudio selecionado
        if str_num not in self.config.get("gestures", {}):
            return

        # Abre Popup pedindo o nome
        dialog = ctk.CTkInputDialog(text="Novo nome para o áudio:", title="Renomear")
        novo_nome = dialog.get_input()
        
        if novo_nome:
            if "aliases" not in self.config: self.config["aliases"] = {}
            
            # Salva o apelido
            self.config["aliases"][str_num] = novo_nome
            
            # Atualiza visualmente na hora
            self.labels_caminhos[numero_gesto].configure(
                text=truncate_text(novo_nome, 25), 
                text_color="#4CC9F0"
            )
            # Salva no JSON
            self.callback_atualizar_config()

    # --- Métodos de Lógica (Iguais aos anteriores) ---
    def ao_mudar_volume(self, valor):
        novo_vol = float(valor) / 100.0
        self.config["volume"] = novo_vol
        self.callback_atualizar_config()

    def limpar_slot(self, numero_gesto):
        str_num = str(numero_gesto)
        mudou = False
        if str_num in self.config.get("gestures", {}):
            del self.config["gestures"][str_num]
            mudou = True
        
        # Se limpar o slot, remove o alias também pra não ficar lixo
        if str_num in self.config.get("aliases", {}):
            del self.config["aliases"][str_num]
            mudou = True
            
        if mudou:
            self.labels_caminhos[numero_gesto].configure(text="Selecionar áudio...", text_color="gray")
            self.callback_atualizar_config()

    def selecionar_arquivo(self, numero_gesto):
        arquivo = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if arquivo:
            if "gestures" not in self.config: self.config["gestures"] = {}
            self.config["gestures"][str(numero_gesto)] = arquivo
            
            # Atualiza o label usando a função de truncar
            nome_completo = os.path.basename(arquivo)
            self.labels_caminhos[numero_gesto].configure(text=truncate_text(nome_completo), text_color="white")
            self.callback_atualizar_config()

    def ao_clicar_start(self):
        self.rodando = not self.rodando
        if self.rodando:
            self.btn_action.configure(text="PARAR CÂMERA", fg_color="#E74C3C", hover_color="#C0392B")
        else:
            self.btn_action.configure(text="INICIAR CÂMERA", fg_color="#2CC985", hover_color="#229A65")
        self.callback_iniciar_ia()