import os
import sys
import time
import subprocess
from pathlib import Path

# Bootstrap transparente para libtk8.6 no Linux
local_lib = os.path.expanduser("~/.local/usr/lib")
if os.path.isdir(local_lib) and sys.platform != "win32":
    curr_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if local_lib not in curr_ld:
        os.environ["LD_LIBRARY_PATH"] = f"{local_lib}:{curr_ld}"
        os.environ["TCL_LIBRARY"] = os.path.join(local_lib, "tcl8.6")
        os.environ["TK_LIBRARY"] = os.path.join(local_lib, "tk8.6")
        os.execv(sys.executable, [sys.executable] + sys.argv)

# Adiciona diretório raiz do projeto ao sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.gui.app import CorujaSyncApp
from ui.gui.views.download_view import DownloadView
from ui.gui.views.search_view import SearchView


def run_recording():
    output_dir = Path("landing/assets")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_video = Path("/tmp/corujasync_demo_raw.mp4")
    if raw_video.exists():
        raw_video.unlink()

    print("[1/4] Inicializando interface gráfica em Modo Escuro (1120x720)...")
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")

    app = CorujaSyncApp()
    app.geometry("1120x720+60+60")
    app.resizable(False, False)
    app.update()

    wid = app.winfo_id()
    print(f"[2/4] Disparando gravação FFmpeg via x11grab no Window ID {wid} ({hex(wid)})...")
    ffmpeg_log = open("/tmp/ffmpeg_rec.log", "w")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "x11grab",
        "-window_id", str(wid),
        "-i", ":0.0",
        "-r", "25",
        "-t", "13",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(raw_video)
    ]
    rec_proc = subprocess.Popen(ffmpeg_cmd, stdout=ffmpeg_log, stderr=ffmpeg_log)

    dl_view: DownloadView = app.views["download"]
    search_view: SearchView = app.views["search"]

    # Roteiro cronometrado da demonstração (14 segundos)
    def step_1():
        dl_view.entry_curso.delete(0, "end")
        dl_view.entry_curso.insert(0, "https://www.estrategiaconcursos.com.br/app/dashboard/aluno/pacote/240502/")
        dl_view.append_log("=== Pacote de Disciplinas ===\nDestino: /home/angolaw/Downloads/Cursos/Câmara dos Deputados\nAlvo: Câmara dos Deputados (Analista Legislativo - Pacote Completo)\n")

    def step_2():
        app.sidebar.set_status("Sincronizando...", state="running")
        dl_view.set_running_state(True)
        dl_view.append_log("[INFO] Sessão autenticada. Iniciando verificação delta de arquivos...\n")
        dl_view.append_log("\n━━━ [1/14] Disciplina: Direito Constitucional\n")
        dl_view.append_log("  → [1/12] Aula 00 - Conceito e Classificação das Constituições\n")
        dl_view.append_log("    📥 Livro Eletrônico Original (PDF) baixado com sucesso.\n", tag="success")
        dl_view.update_telemetry(
            current_file="Aula_00_Livro_Eletronico_versão_original.pdf",
            speed_mbps=18.4,
            eta_seconds=3,
            progress_ratio=0.35
        )

    def step_3():
        dl_view.append_log("  → [2/12] Aula 01 - Poder Constituinte Originário e Derivado\n")
        dl_view.append_log("    📥 Livro Eletrônico Original (PDF) baixado com sucesso.\n", tag="success")
        dl_view.append_log("    📝 Ementa salva em 'Assuntos_dessa_aula.txt'.\n")
        dl_view.update_telemetry(
            current_file="Aula_01_Livro_Eletronico_versão_original.pdf",
            speed_mbps=24.2,
            eta_seconds=1,
            progress_ratio=0.82
        )

    def step_4():
        dl_view.append_log("\n=======================================================\n"
                           "✓ DOWNLOADS CONCLUÍDOS COM SUCESSO! (Tempo: 18.2s)\n"
                           "=======================================================\n", tag="success")
        dl_view.update_telemetry(
            current_file="Sincronização 100% concluída",
            speed_mbps=0.0,
            eta_seconds=0,
            progress_ratio=1.0
        )
        dl_view.set_running_state(False)
        app.sidebar.set_status("Concluído", state="ready")

    def step_5():
        # Alterna para a Busca Global
        app.switch_view("search")
        search_view.entry_query.delete(0, "end")
        search_view.entry_query.insert(0, "Poder Constituinte")

    def step_6():
        # Executa pesquisa instantânea
        search_view._perform_search()

    def step_7():
        print("[3/4] Encerrando demonstração da janela...")
        app.destroy()

    app.after(600, step_1)
    app.after(2000, step_2)
    app.after(3600, step_3)
    app.after(5200, step_4)
    app.after(7200, step_5)
    app.after(8600, step_6)
    app.after(14000, step_7)

    app.mainloop()

    print("Aguardando finalização do processo FFmpeg...")
    rec_proc.wait()
    ffmpeg_log.close()

    if not raw_video.exists() or raw_video.stat().st_size == 0:
        print("[ERRO] Arquivo de vídeo bruto não foi gerado.")
        if os.path.exists("/tmp/ffmpeg_rec.log"):
            with open("/tmp/ffmpeg_rec.log") as f:
                print("FFmpeg Log:\n", f.read()[-500:])
        return False

    print("[4/4] Gerando mídias otimizadas para web...")

    # 1. MP4 com faststart e compactação H.264
    mp4_target = output_dir / "demo.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_video),
        "-c:v", "libx264", "-crf", "22", "-preset", "slow",
        "-movflags", "+faststart", "-pix_fmt", "yuv420p",
        str(mp4_target)
    ], check=True)
    print(f" ✓ Gerado: {mp4_target} ({mp4_target.stat().st_size / 1024:.1f} KB)")

    # 2. WebM (VP9)
    webm_target = output_dir / "demo.webm"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_video),
        "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32",
        str(webm_target)
    ], check=True)
    print(f" ✓ Gerado: {webm_target} ({webm_target.stat().st_size / 1024:.1f} KB)")

    # 3. GIF Animado com PaletteGen
    gif_target = output_dir / "demo.gif"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_video),
        "-vf", "fps=16,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
        str(gif_target)
    ], check=True)
    print(f" ✓ Gerado: {gif_target} ({gif_target.stat().st_size / 1024:.1f} KB)")

    # 4. Poster Frame (Thumbnail)
    poster_target = output_dir / "demo_poster.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-ss", "00:00:10", "-i", str(raw_video),
        "-vframes", "1", "-q:v", "2",
        str(poster_target)
    ], check=True)
    print(f" ✓ Gerado: {poster_target} ({poster_target.stat().st_size / 1024:.1f} KB)")

    print("\n🎉 Todas as mídias da demonstração foram geradas com sucesso em landing/assets/!")
    return True


if __name__ == "__main__":
    run_recording()
