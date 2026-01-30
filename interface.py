import customtkinter as ctk
from tkinter import filedialog
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

FONT_TITLE = ("Roboto Medium", 18)
FONT_NORMAL = ("Roboto", 12)
FONT_SMALL = ("Roboto", 10)
FONT_ICON = ("Segoe UI Emoji", 16)
BTN_HEIGHT = 28
BTN_MAIN_HEIGHT = 40

# Altura estimada de cada linha do menu (botão + padding)
MENU_ROW_HEIGHT = 42 

def truncate_text(text, max_length=35):
    if len(text) > max_length: return text[:max_length-3] + "..."
    return text

class SoundpadInterface:
    def __init__(self, root, config_inicial, callback_iniciar_ia, callback_atualizar_config):
        self.root = root
        self.config = config_inicial
        self.callback_iniciar_ia = callback_iniciar_ia
        self.callback_atualizar_config = callback_atualizar_config
        self.labels_caminhos = {} 
        self.rodando = False
        self.menu_aberto = False 

        self.root.title("Visual Soundpad AI")
        self.root.geometry("400x750")
        
        # --- HEADER ---
        header_frame = ctk.CTkFrame(root, fg_color="transparent")
        header_frame.pack(pady=(15, 5), fill="x", padx=20)
        
        ctk.CTkLabel(header_frame, text="🖐️ Gesture Soundpad", font=FONT_TITLE).pack()
        
        # Botão Trigger do Menu
        self.btn_perfil = ctk.CTkButton(header_frame, 
                                        text=f"Perfil: {self.get_perfil_atual()} ▼", 
                                        fg_color="#333333", hover_color="#444444",
                                        command=self.toggle_menu_perfis)
        self.btn_perfil.pack(pady=5, fill="x")

        # --- MENU FLUTUANTE (Inicializado vazio) ---
        # A altura será definida dinamicamente no abrir_menu
        self.dropdown_frame = ctk.CTkScrollableFrame(root, corner_radius=10, 
                                                     fg_color="#222222", border_width=1, border_color="#444444")
        
        # --- LISTA PRINCIPAL ---
        self.main_frame = ctk.CTkScrollableFrame(root, corner_radius=10, fg_color="transparent")
        self.main_frame.pack(pady=5, padx=10, fill="both", expand=True)

        for i in range(1, 11):
            self.criar_slot_vertical_layout(self.main_frame, i)

        # --- FOOTER ---
        self.footer_frame = ctk.CTkFrame(root, fg_color=("#2b2b2b", "#2b2b2b"), corner_radius=15)
        self.footer_frame.pack(fill="x", side="bottom", pady=15, padx=15)

        vol_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        vol_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(vol_frame, text="Vol:", font=FONT_SMALL, width=30).pack(side="left")
        
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=100, command=self.ao_mudar_volume, height=15)
        self.vol_slider.set(self.config.get("volume", 1.0) * 100)
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=10)

        self.btn_action = ctk.CTkButton(self.footer_frame, text="INICIAR CÂMERA", 
                                        command=self.ao_clicar_start,
                                        height=BTN_MAIN_HEIGHT, font=("Roboto", 14, "bold"),
                                        fg_color="#2CC985", hover_color="#229A65")
        self.btn_action.pack(fill="x", padx=10, pady=(5, 15))

        self.main_frame.bind("<Button-1>", lambda e: self.fechar_menu())
        self.refresh_ui_slots()

    # --- LÓGICA DE PERFIS ---

    def get_perfil_atual(self):
        return self.config.get("current_profile", "Padrão")

    def toggle_menu_perfis(self):
        if self.menu_aberto:
            self.fechar_menu()
        else:
            self.abrir_menu()

    def fechar_menu(self):
        self.dropdown_frame.place_forget()
        self.btn_perfil.configure(text=f"Perfil: {self.get_perfil_atual()} ▼")
        self.menu_aberto = False

    def abrir_menu(self):
        # 1. Remove visualmente o menu antes de recalcular (Isso reseta a geometria)
        self.dropdown_frame.place_forget()
        self.dropdown_frame.update() # Força a atualização da tela

        # 2. Limpa os widgets internos
        for widget in self.dropdown_frame.winfo_children():
            widget.destroy()

        perfis = self.config.get("profiles", {})
        
        # 3. Recria os itens
        for nome_perfil in perfis:
            self.criar_item_menu_customizado(nome_perfil)

        # 4. Adiciona o botão de criar
        btn_add = ctk.CTkButton(self.dropdown_frame, text="+ Criar Novo Perfil", 
                                fg_color="transparent", border_width=1, border_color="#555",
                                hover_color="#333333", height=30,
                                command=self.criar_novo_perfil)
        btn_add.pack(fill="x", pady=5, padx=5)

        # --- CÁLCULO MANUAL (Ajustado para ficar justo) ---
        qtd_perfis = len(perfis)
        
        # Matemática:
        # Perfil: 35px (altura frame) + 4px (padding vertical) = 39px
        # Botão Add: 30px (altura) + 10px (padding vertical) = 40px
        # Padding extra do container Scrollable: ~5px
        
        altura_calculada = (qtd_perfis * 39) + 0
        
        # Limites: Mínimo 50px, Máximo 220px (Scroll ativa se passar de 220)
        altura_final = max(50, min(altura_calculada, 220))

        # 5. Aplica a altura e reposiciona
        self.dropdown_frame.configure(height=altura_final)
        self.dropdown_frame.place(x=20, y=90, relwidth=0.9) 
        
        self.dropdown_frame.lift()
        self.btn_perfil.configure(text=f"Perfil: {self.get_perfil_atual()} ▲")
        self.menu_aberto = True
        
    def criar_item_menu_customizado(self, nome_perfil):
        row = ctk.CTkFrame(self.dropdown_frame, fg_color="transparent", height=35)
        row.pack(fill="x", pady=2)

        ativo = (nome_perfil == self.get_perfil_atual())
        cor_txt = "#2CC985" if ativo else "white"
        
        btn_nome = ctk.CTkButton(row, text=nome_perfil, fg_color="transparent", 
                                 anchor="w", text_color=cor_txt, hover_color="#333333",
                                 command=lambda p=nome_perfil: self.selecionar_perfil(p))
        btn_nome.pack(side="left", fill="x", expand=True)

        if nome_perfil != "Padrão":
             btn_edit = ctk.CTkButton(row, text="✏️", width=30, fg_color="transparent", font=FONT_ICON,
                                      hover_color="#444444", text_color="#F39C12",
                                      command=lambda p=nome_perfil: self.renomear_perfil(p))
             btn_edit.pack(side="right")

        if nome_perfil != "Padrão":
            btn_del = ctk.CTkButton(row, text="🗑️", width=30, fg_color="transparent", 
                                    text_color="#E74C3C", font=FONT_ICON, hover_color="#444444",
                                    command=lambda p=nome_perfil: self.apagar_perfil(p))
            btn_del.pack(side="right")

    # --- AÇÕES DO MENU ---

    def selecionar_perfil(self, nome):
        self.config["current_profile"] = nome
        self.fechar_menu()
        self.refresh_ui_slots()
        self.callback_atualizar_config()

    def criar_novo_perfil(self):
        dialog = ctk.CTkInputDialog(text="Nome do novo perfil:", title="Novo Perfil")
        nome = dialog.get_input()
        if nome:
            nome = nome.strip()
            if not nome: return
            if nome in self.config["profiles"]: return
            
            self.config["profiles"][nome] = {"gestures": {}, "aliases": {}}
            self.selecionar_perfil(nome) 

    def apagar_perfil(self, nome):
        if nome == self.get_perfil_atual():
             self.selecionar_perfil("Padrão") # Muda pro padrão antes de apagar o atual
        
        if nome in self.config["profiles"]:
            del self.config["profiles"][nome]
        
        self.abrir_menu() 
        self.callback_atualizar_config()

    def renomear_perfil(self, nome_antigo):
        dialog = ctk.CTkInputDialog(text=f"Renomear '{nome_antigo}' para:", title="Editar Perfil")
        novo_nome = dialog.get_input()
        
        if novo_nome:
            novo_nome = novo_nome.strip()
            if not novo_nome: return
            if novo_nome in self.config["profiles"]: return

            dados = self.config["profiles"][nome_antigo]
            self.config["profiles"][novo_nome] = dados
            del self.config["profiles"][nome_antigo]
            
            if self.get_perfil_atual() == nome_antigo:
                self.config["current_profile"] = novo_nome
                self.btn_perfil.configure(text=f"Perfil: {novo_nome} ▲")
            
            self.abrir_menu() 
            self.callback_atualizar_config()

    # --- ATUALIZAÇÃO DA UI PRINCIPAL ---

    def get_dados_perfil_ativo(self):
        nome = self.get_perfil_atual()
        if nome not in self.config["profiles"]:
            nome = "Padrão"
            self.config["current_profile"] = "Padrão"
        return self.config["profiles"][nome]
    
    def criar_slot_vertical_layout(self, parent, numero_gesto):
        card = ctk.CTkFrame(parent, corner_radius=8, fg_color=("#3a3a3a", "#333333"), height=45)
        card.pack(pady=3, fill="x", anchor="n")
        
        lbl_num = ctk.CTkLabel(card, text=str(numero_gesto), width=24, height=24, 
                               fg_color="#444444", corner_radius=12, font=("Arial", 12, "bold"))
        lbl_num.pack(side="left", padx=(8, 5), pady=8)

        lbl_arquivo = ctk.CTkLabel(card, text="...", font=FONT_NORMAL, anchor="w")
        lbl_arquivo.pack(side="left", fill="x", expand=True, padx=5)
        self.labels_caminhos[numero_gesto] = lbl_arquivo

        btn_edit = ctk.CTkButton(card, text="✏️", width=BTN_HEIGHT, fg_color="transparent", font=FONT_ICON, text_color="#E67E22", hover_color="#444444",
                                   command=lambda: self.renomear_som(numero_gesto))
        btn_edit.pack(side="right")
        
        btn_limpar = ctk.CTkButton(card, text="🗑️", width=BTN_HEIGHT, fg_color="transparent", font=FONT_ICON, text_color="#E74C3C", hover_color="#444444",
                                   command=lambda: self.limpar_slot(numero_gesto))
        btn_limpar.pack(side="right")

        btn_pasta = ctk.CTkButton(card, text="📂", width=BTN_HEIGHT, fg_color="transparent", font=FONT_ICON, text_color="#3498DB", hover_color="#444444",
                                  command=lambda: self.selecionar_arquivo(numero_gesto))
        btn_pasta.pack(side="right", padx=(5, 0))

    def refresh_ui_slots(self):
        dados = self.get_dados_perfil_ativo()
        gestos = dados.get("gestures", {})
        aliases = dados.get("aliases", {})
        
        for i in range(1, 11):
            str_num = str(i)
            path = gestos.get(str_num, None)
            
            if i in self.labels_caminhos: 
                if path and os.path.exists(path):
                    if str_num in aliases:
                        txt = aliases[str_num]
                        cor = "#4CC9F0"
                    else:
                        txt = os.path.basename(path)
                        cor = "white"
                    self.labels_caminhos[i].configure(text=truncate_text(txt, 25), text_color=cor)
                else:
                    self.labels_caminhos[i].configure(text="Selecionar áudio...", text_color="gray")

    # --- MÉTODOS DE SLOT ---

    def renomear_som(self, numero_gesto):
        dados = self.get_dados_perfil_ativo()
        str_num = str(numero_gesto)
        
        if str_num not in dados["gestures"]: return

        dialog = ctk.CTkInputDialog(text="Novo nome:", title="Rename Sound")
        novo = dialog.get_input()
        if novo:
            dados["aliases"][str_num] = novo
            self.refresh_ui_slots()
            self.callback_atualizar_config()

    def limpar_slot(self, numero_gesto):
        dados = self.get_dados_perfil_ativo()
        str_num = str(numero_gesto)
        
        mudou = False
        if str_num in dados["gestures"]:
            del dados["gestures"][str_num]
            mudou = True
        if str_num in dados["aliases"]:
            del dados["aliases"][str_num]
            mudou = True
            
        if mudou:
            self.refresh_ui_slots()
            self.callback_atualizar_config()

    def selecionar_arquivo(self, numero_gesto):
        arquivo = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if arquivo:
            dados = self.get_dados_perfil_ativo()
            dados["gestures"][str(numero_gesto)] = arquivo
            
            if str(numero_gesto) in dados["aliases"]:
                del dados["aliases"][str(numero_gesto)]
                
            self.refresh_ui_slots()
            self.callback_atualizar_config()
            
    def ao_mudar_volume(self, valor):
        self.config["volume"] = float(valor) / 100.0
        self.callback_atualizar_config()

    def ao_clicar_start(self):
        self.rodando = not self.rodando
        texto = "STOP CAMERA" if self.rodando else "START CAMERA"
        cor = "#E74C3C" if self.rodando else "#2CC985"
        hover = "#C0392B" if self.rodando else "#229A65"
        self.btn_action.configure(text=texto, fg_color=cor, hover_color=hover)
        self.callback_iniciar_ia()