from PIL import Image, ImageTk, ImageEnhance
import customtkinter as ctk
import subprocess
import os
import hashlib
import pystray
import threading
import tkinter.filedialog as fd
import tkinter.simpledialog as sd
from tkinter import messagebox

# --- Create Windows ---
app = ctk.CTk()
app.title("Indie Launcher")
app.geometry("1920x1080")

# --- Set application icon (taskbar + window) ---
icon_img = Image.open("picture.jpg")
icon_tk = ImageTk.PhotoImage(icon_img)
app.iconphoto(True, icon_tk) # noqa


# --- Extract Icon from .EXE ---
def extract_icon(path_exe, output_name):
    ico_path = "temp_icon.ico"
    icons_dir = "Icons"
    os.makedirs(icons_dir, exist_ok=True)

    subprocess.run(f'wrestool -x -t14 "{path_exe}" > {ico_path}', shell=True)
    subprocess.run(f"icotool -x -o . {ico_path}", shell=True)

    # Look for the largest PNG
    list_png = [png for png in os.listdir('.') if png.endswith('.png')]
    best_path = None
    if list_png:
        best = max(list_png, key=lambda png: Image.open(png).size[0])
        best_path = os.path.join(icons_dir, f"{output_name}.png")
        icon = Image.open(best)
        icon = icon.resize((128, 128), Image.LANCZOS)
        icon.save(best_path)

        for temp_png in list_png:
            if os.path.exists(temp_png):
                os.remove(temp_png)

    if os.path.exists(ico_path):
        os.remove(ico_path)

    return best_path


def launch_game(name, bottle_name):
    if bottle_name=="Jeux Linux":
        subprocess.Popen([name])
        return
    else:
        try:
            command = f'bottles-cli run -b "{bottle_name}" --exe "{name}"'
            subprocess.Popen(command, shell=True)
        except Exception as e:
            print(f"Error : {e}")

frame = ctk.CTkFrame(app, fg_color="transparent")
frame.pack(fill="both", expand=True, pady=20)

def populate_games():
    for widget in frame.winfo_children():
        widget.destroy()

    images_refs = []
    games_columns = 10
    for c in range(games_columns):
        frame.grid_columnconfigure(c, weight=1)

    game_names = []
    if os.path.exists("Name.txt"):
        with open("Name.txt", "r", encoding="utf-8") as f:
            game_names = [line.strip() for line in f if line.strip()]

    # --- Read Games Paths ---
    paths = []
    if os.path.exists("Path.txt"):
        with open("Path.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split(";")
                    exe_path = parts[0]
                    bottle = parts[1] if len(parts) > 1 else "Jeux Windows"
                    paths.append((exe_path, bottle))

    for i, (exe_path, bottle) in enumerate(paths):
        game_base_name = os.path.splitext(os.path.basename(exe_path))[0]
        game_hash_name = hashlib.md5(exe_path.encode("utf-8")).hexdigest()[:8]
        icon_path = os.path.join("Icons", f"{game_base_name}_{game_hash_name}.png")

        if not os.path.exists(icon_path) and exe_path.lower().endswith(".exe"):
            icon_path = extract_icon(exe_path, f"{game_base_name}_{game_hash_name}")

        img = Image.open(icon_path)
        ctk_img = ctk.CTkImage(img, size=(128, 128)) # if I change the picture myself
        images_refs.append(ctk_img)

        btn = ctk.CTkButton(
            frame,
            image=ctk_img,
            text="",
            fg_color="transparent",
            hover_color="none",
            command=lambda path=exe_path, b=bottle: launch_game(path, b)
        )

        def on_enter(_, btn=btn, img=img): # noqa
            enhancer = ImageEnhance.Brightness(img)
            darker_img = enhancer.enhance(0.5)
            ctk_darker_img = ctk.CTkImage(darker_img, size=(128, 128))
            btn.configure(image=ctk_darker_img)

        def on_leave(_, btn=btn, img=ctk_img): # noqa
            btn.configure(image=img)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        games_row = (i // games_columns) * 2
        games_col = i % games_columns
        btn.grid(row=games_row, column=games_col)

        label_text = game_names[i] if i < len(game_names) else game_base_name
        label = ctk.CTkLabel(
            frame,
            text=label_text,
            font=("Arial", 12),
            text_color="#FFFFFF"
        )
        label.grid(row=games_row + 1, column=games_col)
    last_row = ((len(paths) - 1) // games_columns + 1) * 2 # for the buttons at the end of the frame

    def choisir_bouteille():
        choix = []

        def set_bottle(name):
            choix.append(name)
            win.destroy()

        win = ctk.CTkToplevel(app)
        win.geometry("150x100")
        win_frame = ctk.CTkFrame(win, fg_color="transparent")
        win_frame.pack(expand=True)
        win.title("")

        ctk.CTkButton(
            win_frame,
            fg_color="#C71585",
            hover_color="#8B0A50",
            font=("Arial", 16, "bold"),
            text="Jeux Windows",
            command=lambda: set_bottle("Jeux Windows")
        ).pack(pady=5)

        ctk.CTkButton(
            win_frame,
            fg_color="#8A2BE2",
            hover_color="#7B1FA2",
            font=("Arial", 16, "bold"),
            text="Jeux Linux",
            command=lambda: set_bottle("Jeux Linux")
        ).pack(pady=5)

        win.grab_set()
        app.wait_window(win)
        return choix[0] if choix else "Jeux Windows"

    def new_game():
        exe_path = fd.askopenfilename( # noqa
            title="Sélectionner un fichier .exe",
            initialdir="/run/media/victor/Games/Jeux/",
            filetypes=[("Fichiers exécutables", "*.exe *.x86_64")]
        )
        if not exe_path:
            return
        elif not (exe_path.lower().endswith(".exe") or exe_path.lower().endswith(".x86_64")):
            messagebox.showerror("Erreur", "Veuillez sélectionner un fichier .exe valide.")
            return

        game_name = None
        while not game_name:
            game_name = sd.askstring("Nom du jeu", "Entrez le nom du jeu :")
            if game_name is None:  # Cancel
                return
            if not game_name.strip():
                game_name = None

        bouteille = choisir_bouteille()

        # Added in Path.txt and Name.txt
        with open("Path.txt", "a", encoding="utf-8") as file:
            file.write(f"{exe_path};{bouteille}\n") # A bit of an error here, but the case 'Jeux Japonais' is so rare that I will do it myself if that's the case
        with open("Name.txt", "a", encoding="utf-8") as file:
            file.write(f"{game_name}\n")

        if os.path.exists("Name.txt") and os.path.exists("Path.txt"):
            with open("Name.txt", "r", encoding="utf-8") as f_names, open("Path.txt", "r", encoding="utf-8") as f_paths:
                names = [line.strip() for line in f_names if line.strip()]
                raw_paths = [line.strip() for line in f_paths if line.strip()]
                jeux = []
                for path_line, name in zip(raw_paths, names):
                    jeux.append((path_line, name)) # tuple
                jeux = sorted(jeux, key=lambda x: x[0].lower())
            # Rewriting sorted files
            with open("Path.txt", "w", encoding="utf-8") as f_paths, open("Name.txt", "w", encoding="utf-8") as f_names:
                for path_line, name in jeux:
                    f_paths.write(f"{path_line}\n")
                    f_names.write(f"{name}\n")

        populate_games()

    def change_game_image():
        # Select an existing image in Icons
        icon_files = []
        for file in os.listdir("Icons"):
            if file.endswith(".png"):
                icon_files.append(file)
        if not icon_files:
            messagebox.showerror("Erreur", "Aucune image trouvée dans le dossier Icons.")
            return

        # Selector to choose the image to replace
        old_icon = fd.askopenfilename(
            title="Sélectionner l'image à remplacer",
            initialdir="Icons",
            filetypes=[("Image PNG", "*.png")]
        )
        if not old_icon:
            return
        elif not old_icon.endswith(".png"):
            messagebox.showerror("Erreur", "Sélection invalide.")
            return

        # Selector to choose the new image
        new_icon = fd.askopenfilename(
            title="Sélectionner la nouvelle image carrée",
            initialdir="/home/victor/Images/Captures/",
            filetypes=[("Image PNG", "*.png")]
        )
        if not new_icon:
            return
        elif not new_icon.endswith(".png"):
            messagebox.showerror("Erreur", "Sélection invalide.")
            return

        # Check that the image is a square
        new_img = Image.open(new_icon)
        if new_img.width != new_img.height:
            messagebox.showerror("Erreur", "L'image doit être carrée (même largeur et hauteur).")
            return

        # Overwrite the old image
        new_img.save(old_icon)
        #messagebox.showinfo("Succès", "Image remplacée avec succès.")
        populate_games()

    btns_frame = ctk.CTkFrame(frame, fg_color="transparent") # reproduce the configuration of the Notes buttons but with a grid
    btns_frame.grid(row=last_row, column=0, columnspan=games_columns, pady=(760,0), sticky="ew")
    btns_frame.grid_columnconfigure(0, weight=1)
    btns_frame.grid_columnconfigure(1, weight=0)
    btns_frame.grid_columnconfigure(2, weight=0)
    btns_frame.grid_columnconfigure(3, weight=1)

    btn_new_games = ctk.CTkButton(
        btns_frame,
        text="Nouveau Jeu",
        fg_color="#C71585",
        hover_color="#8B0A50",
        command=new_game
    )
    btn_new_games.grid(row=0, column=1, padx=(0, 10))

    btn_change_image = ctk.CTkButton(
        btns_frame,
        text="Changer l'image",
        fg_color="#FF00FF",
        hover_color="#B200B2",
        command=change_game_image
    )
    btn_change_image.grid(row=0, column=2)


# --- Function to hide the window and show the icon ---
def on_close():
    app.withdraw()  # hide the window
    threading.Thread(target=create_tray_icon, daemon=True).start()  # launches the icon in the tray

# --- Creating the icon in the system tray ---
def create_tray_icon():
    def on_quit(icon):
        icon.stop()
        app.destroy()  # closes the application completely

    def on_restore():
        app.deiconify()  # restore the window

    icon_image = Image.open("picture.jpg")

    menu = pystray.Menu(
        pystray.MenuItem("Ouvrir", on_restore),
        pystray.MenuItem("Quitter", on_quit)
    )

    tray_icon = pystray.Icon("IndieLauncher", icon_image, "Indie Launcher", menu)
    tray_icon.run()

# --- Associate with the cross ---
app.protocol("WM_DELETE_WINDOW", on_close)

populate_games()
app.mainloop()