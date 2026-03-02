import pathlib
import time
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class WhatsApp:
    """Implementação de automação para WhatsApp Web com validação de status de entrega."""
    
    _instance = None
    
    # Mapeamento de seletores (XPaths e IDs) para facilitar manutenção da interface
    SELECTORS = {
        "side_panel": (By.ID, "side"),
        "qr_canvas": (By.XPATH, '//canvas'),
        "chat_input": (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'),
        "attach_btn": (By.XPATH, '//span[contains(@data-icon,"plus")]'),
        "btn_document": (By.XPATH, '//span[contains(text(),"Document")]'),
        "btn_media": (By.XPATH, '//span[contains(text(),"Photos & videos")]'),
        "file_input": (By.XPATH, '//input[@type="file"]'),
        "send_btn": (By.XPATH, '//span[contains(@data-icon,"send")]'),
        "loading_spinner": (By.XPATH, '//span[@data-visualcompletion="loading-state"]'),
        "pending_icon": (By.XPATH, '//*[contains(@data-icon, "msg-time")]') # Ícone de relógio (pendente)
    }

    def __new__(cls, *args, **kwargs):
        """Implementação do padrão Singleton para evitar múltiplas instâncias do driver."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, headless: bool = False):
        if hasattr(self, 'driver'): return
        
        # Configurações do Chrome WebDriver
        chrome_options = Options()
        chrome_options.set_capability("unhandledPromptBehavior", "accept")
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Define diretório local para persistência de dados da sessão (evita ler QR Code toda vez)
        session_path = str(pathlib.Path("./chrome-data").resolve())
        chrome_options.add_argument(f"user-data-dir={session_path}")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 60)
        self.login()

    def login(self):
        """Gerencia o fluxo de carregamento da página e autenticação via QR Code."""
        self.driver.get("https://web.whatsapp.com")
        print("🔎 Verificando sessão...")
        try:
            # Verifica se o painel lateral carregou (indica sessão ativa)
            self.wait.until(EC.presence_of_element_located(self.SELECTORS["side_panel"]))
            print("✅ Sessão ativa!")
        except:
            print("📱 Aguardando leitura do QR Code...")
            self.wait.until(EC.presence_of_element_located(self.SELECTORS["qr_canvas"]))
            self.wait.until(EC.presence_of_element_located(self.SELECTORS["side_panel"]))
            print("✅ Login realizado!")

    def _wait_for_delivery(self, timeout=30):
        """Faz polling na interface para verificar se o ícone de pendente desapareceu."""
        print("⏳ Aguardando confirmação de entrega...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Busca elementos com o ícone de relógio
            pending = self.driver.find_elements(*self.SELECTORS["pending_icon"])
            if not pending:
                print("✅ Mensagem entregue ao servidor!")
                return True
            time.sleep(1)
        print("⚠️ Timeout: A entrega demorou mais que o esperado.")
        return False

    def _open_chat(self, phone: str):
        """Utiliza a API de URL do WhatsApp para abrir chats diretamente pelo número."""
        clean_phone = phone.replace(" ", "").replace("+", "")
        self.driver.get(f"https://web.whatsapp.com/send?phone={clean_phone}")
        self.wait.until(EC.presence_of_element_located(self.SELECTORS["chat_input"]))
        time.sleep(2) # Buffer para estabilização do DOM

    def send_text(self, phone: str, message: str):
        """Envia mensagem de texto simples e aguarda confirmação."""
        try:
            self._open_chat(phone)
            msg_box = self.driver.find_element(*self.SELECTORS["chat_input"])
            msg_box.send_keys(message + Keys.ENTER)
            self._wait_for_delivery()
            print(f"📩 Texto enviado para {phone}")
        except Exception as e:
            print(f"❌ Erro ao enviar texto: {e}")

    def _send_file(self, phone: str, file_path: str, message: str, mode: str):
        """Lógica interna compartilhada para upload de mídias e documentos."""
        self._open_chat(phone)
        full_path = str(pathlib.Path(file_path).resolve())
        
        try:
            # Aciona o menu de anexos
            self.wait.until(EC.element_to_be_clickable(self.SELECTORS["attach_btn"])).click()
            time.sleep(1)

            # Seleciona o tipo de upload baseado no parâmetro 'mode'
            selector_key = "btn_document" if mode == "document" else "btn_media"
            self.wait.until(EC.element_to_be_clickable(self.SELECTORS[selector_key])).click()
            time.sleep(1.5)

            # Interage com o input de arquivo oculto para realizar o upload
            inputs = self.driver.find_elements(*self.SELECTORS["file_input"])
            inputs[-1].send_keys(full_path)

            # Contorno para fechar janela de diálogo do SO e forçar clique de envio via JS
            pyautogui.press('esc')
            time.sleep(1.5)
            
            send_btn = self.wait.until(EC.element_to_be_clickable(self.SELECTORS["send_btn"]))
            self.driver.execute_script("arguments[0].click();", send_btn)

            # Monitora o spinner de carregamento do upload
            print(f"⏳ Fazendo upload de {mode}...")
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.invisibility_of_element_located(self.SELECTORS["loading_spinner"])
                )
            except:
                pass

            # Envia legenda/mensagem complementar, se houver
            if message:
                time.sleep(1)
                msg_box = self.wait.until(EC.presence_of_element_located(self.SELECTORS["chat_input"]))
                msg_box.send_keys(message + Keys.ENTER)

            # Aguarda a mensagem sair do estado de pendente
            self._wait_for_delivery(timeout=45)
            
            print(f"✅ {mode.capitalize()} finalizado com sucesso!")
            return True

        except Exception as e:
            print(f"❌ Falha no envio de {mode}: {e}")
            pyautogui.press('esc')
            return False

    def send_document(self, phone: str, file_path: str, message: str = None):
        """Encapsulamento para envio em modo Documento."""
        return self._send_file(phone, file_path, message, mode="document")

    def send_media(self, phone: str, file_path: str, message: str = None):
        """Encapsulamento para envio em modo Mídia (Fotos e Vídeos)."""
        return self._send_file(phone, file_path, message, mode="media")

    def close(self):
        """Encerra a sessão do WebDriver."""
        self.driver.quit()
        print("🛑 Driver encerrado.")

def run_notification_task():
    """Exemplo de rotina de execução para envio de notificações."""
    phone = "55xxxxxxxxxxx"
    file_path = r"C:\caminho\para\seu\arquivo.png"

    bot = None
    try:
        bot = WhatsApp(headless=False)
        
        # Fluxo sequencial de testes
        bot.send_media(phone, file_path, "Exemplo de envio de mídia")
        bot.send_document(phone, file_path, "Exemplo de envio de documento")
        bot.send_text(phone, "Exemplo de envio de texto puro")
        
    except Exception as e:
        print(f"🚨 Erro na rotina: {e}")
    finally:
        if bot:
            bot.close()

if __name__ == "__main__":
    run_notification_task()