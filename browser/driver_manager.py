import sys
from typing import Optional, Tuple
from selenium import webdriver
from selenium.common.exceptions import WebDriverException


def create_driver(
    preferred_browser: str = "auto",
    headless: bool = False,
) -> webdriver.Remote:
    """
    Inicializa uma instância do WebDriver usando Selenium Manager nativo do Selenium 4.
    Tenta o navegador preferido e, caso falhe ou esteja em 'auto', tenta sucessivamente:
    Edge -> Chrome -> Firefox.
    """
    browser_order = []
    preferred = preferred_browser.lower().strip()

    if preferred == "edge":
        browser_order = ["edge", "chrome", "firefox"]
    elif preferred == "chrome":
        browser_order = ["chrome", "edge", "firefox"]
    elif preferred == "firefox":
        browser_order = ["firefox", "chrome", "edge"]
    else:
        # Modo 'auto': no Windows prefere Edge por vir pré-instalado; no Linux/Mac prefere Chrome/Chromium
        if sys.platform == "win32":
            browser_order = ["edge", "chrome", "firefox"]
        else:
            browser_order = ["chrome", "edge", "firefox"]

    last_error: Optional[Exception] = None

    for browser_name in browser_order:
        try:
            if browser_name == "edge":
                options = webdriver.EdgeOptions()
                if headless:
                    options.add_argument("--headless=new")
                options.add_argument("--disable-notifications")
                options.add_argument("--start-maximized")
                driver = webdriver.Edge(options=options)
                return driver

            elif browser_name == "chrome":
                options = webdriver.ChromeOptions()
                if headless:
                    options.add_argument("--headless=new")
                options.add_argument("--disable-notifications")
                options.add_argument("--start-maximized")
                driver = webdriver.Chrome(options=options)
                return driver

            elif browser_name == "firefox":
                options = webdriver.FirefoxOptions()
                if headless:
                    options.add_argument("-headless")
                driver = webdriver.Firefox(options=options)
                driver.maximize_window()
                return driver

        except WebDriverException as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Não foi possível inicializar nenhum navegador suportado (Edge, Chrome ou Firefox). "
        f"Certifique-se de ter um navegador moderno instalado no sistema. Erro detalhado: {last_error}"
    )
