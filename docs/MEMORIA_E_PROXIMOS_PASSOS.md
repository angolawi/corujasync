# Memória de Projeto e Handover do Sistema Completo

**Data:** 28 de Setembro de 2026  
**Status Atual:** Arquitetura Modular, GUI Moderna, Blindagem Jurídica, Resiliência OTA, Diagnóstico Semântico, Sistema de Licenciamento Criptográfico e Recursos Premium (**Smart Watcher** + **Indexador de Busca**) concluídos e testados com **100% de sucesso (38 testes unitários aprovados)**.  
**Branch:** `master`

---

## 📌 1. O Que Foi Concluído no Projeto

### A. Arquitetura Modular e Clean Architecture
- **`core/events.py`:** Sistema de eventos desacoplado (`ProgressEvent`, `StatusEvent`, `DisciplineEvent`, `LessonEvent`, `VideoEvent`) com a interface abstrata `DownloadObserver`.
- **`core/config.py`:** Armazenamento multiplataforma de configurações e preferências nos caminhos padrão do SO (`~/.config/autoconcursodownloader` no Linux, `%LOCALAPPDATA%` no Windows).
- **`core/session.py`:** Sessão HTTP resiliente com Keep-Alive, retries exponenciais e pool de conexões.
- **`core/state_manager.py`:** Persistência atômica de progresso em `.download_state.json` com Smart Resume em 0,001s e bootstrap do disco.
- **`core/downloader.py`:** Download atômico (`.part` -> destino final) com proteção integral de metadados originais.
- **`core/crawler.py` & `core/processor.py`:** Extração e processamento de catálogo de cursos, pacotes, disciplinas, aulas e videoaulas desacoplados da interface.
- **`browser/driver_manager.py`:** Detecção e fallback automático entre navegadores instalados (**Microsoft Edge**, **Google Chrome**, **Mozilla Firefox**) via Selenium Manager nativo.

### B. Frente 1: Resiliência contra Mudanças de Layout (Seletores OTA e Interceptação de API)
- **`core/selectors.json`:** Mapeamento completo e versionado de seletores para todas as telas (login, popups, lista de cursos, pacotes, disciplinas, aulas, PDFs e vídeos).
- **`core/selector_manager.py`:**
  - Suporte nativo a **cadeias de fallback** (se o seletor primário falhar, testa alternativas em cascata).
  - Cache local versionado em `~/.config/autoconcursodownloader/selectors_cache.json`.
  - Atualização remota **Over-The-Air (OTA)** transparente: atualizações de classes CSS e layouts do site são corrigidas na nuvem sem precisar recompilar ou redistribuir o `.exe`.
  - Atualização assíncrona não bloqueante no boot da aplicação (`fetch_remote_async`).
- **`core/api_extractor.py`:**
  - **Bypass total de CSS:** intercepta estruturas de dados internas (`window.__NEXT_DATA__` e estados globais de SPAs). Aulas e IDs são extraídos mesmo se todas as classes CSS forem alteradas.
  - Varredura de segurança em código-fonte HTML via regex para URLs de APIs e mídias diretas.
  - Extração de tokens de autorização de `localStorage` e `sessionStorage`.

### C. Frente 2: Motor de Diagnóstico "Esperado vs. Encontrado"
- **`core/diagnostics.py`:**
  - **Higienização estrita LGPD:** Mascara CPFs, e-mails, senhas e tokens de autorização antes de qualquer geração de log ou snapshot.
  - **Snapshot Semântico:** Captura resumo estruturado do DOM (botões visíveis, links de download, cabeçalhos e amostra sanitizada do HTML) comparando o elemento esperado com o que foi renderizado.
  - **`DiagnosticsStore`:** Armazena falhas em memória e permite exportar relatório `.json` para suporte.
- **Botão na GUI (`ui/gui/app.py`):** Botão *"🛠 Exportar Diagnóstico"* na aba de Download que salva o arquivo com 1 clique.

### D. Frente 3: Comercialização e Sistema de Licenciamento
- **`legal/license_manager.py`:**
  - **Machine ID Determinístico e Anônimo:** Gera hash único de hardware (`XXXX-XXXX-XXXX-XXXX`) sem expor dados pessoais.
  - **Chaves Criptográficas Assinadas (HMAC-SHA256):** Padrão `CDL-<TIER>-<BASE64_PAYLOAD>-<SIGNATURE>` antifraude.
  - **Suporte a Múltiplos Planos:** Vitalício (sem expiração), Anual (365 dias), Edital (180 dias) ou customizado.
  - **Trava de Máquina:** Suporta licenças flutuantes (`ANY`) ou travadas ao computador do comprador.
- **CLI para Checkout / Webhooks (`tools/generate_license.py`):**
  - Permite criar chaves instantaneamente via terminal ou integrar a webhooks de plataformas como **Kiwify**, **Hotmart** ou **Cakto**.
- **Interface de Ativação na GUI:**
  - Exibe o Machine ID do cliente na aba *Configurações & Login*, campo de inserção da chave e feedback visual de ativação com persistência atômica.

### E. Frente 4: Recursos Premium e Distribuição
- **Smart Watcher (`core/watcher.py`):**
  - Monitor inteligente periódico que compara o catálogo online com o `.download_state.json`.
  - Detecta e baixa automaticamente apenas novas aulas e materiais publicados após o download inicial.
- **Indexador e Busca Global Offline (`core/indexer.py`):**
  - Motor de busca textual de alta performance em todos os PDFs baixados no computador.
  - Localiza termos, jurisprudências e leis em segundos com número de página, nome da disciplina e snippet de contexto.
- **Instalador Profissional Windows (`installer/concursodownloader.iss`):**
  - Script Inno Setup 6 pronto para gerar `Setup_ConcursoDownloader_v2.0.0.exe` com atalhos na Área de Trabalho/Menu Iniciar e desinstalador.

### F. Suíte de Testes
- **38 testes unitários automatizados** passando com **100% de sucesso** (`python -m unittest discover -v`):
  - `test_download_ui.py`
  - `test_state_manager.py`
  - `test_process_courses.py`
  - `test_video_download.py`
  - `test_legal_and_config.py`
  - `test_resilience_and_selectors.py`
  - `test_diagnostics_and_commercial.py`

---

## 💻 2. Guia de Comandos Úteis

### Iniciar Aplicação
```bash
# Iniciar a Interface Gráfica moderna
python main.py

# Iniciar modo CLI para download de pacote
python main.py --curso 400565 --videos --qualidade 720p
```

### Gerar Chaves de Licença para Clientes
```bash
# Exibir o Machine ID do computador atual
python tools/generate_license.py my-machine

# Gerar licença anual vinculada ao e-mail do comprador
python tools/generate_license.py create --client aluno@gmail.com --tier anual

# Gerar licença vitalícia travada no Machine ID do cliente
python tools/generate_license.py create --client aluno@gmail.com --tier vitalicio --machine ABCD-EF12-3456-7890

# Validar uma chave de licença
python tools/generate_license.py verify CDL-ANU-eyJjbGllbnQiOiJhbHVub0BnbWFpbC5jb20iLCJleHBpcmVzX2F0IjoiMjAyNy0wOS0yOCIsImlzc3VlZF9hdCI6IjIwMjYtMDktMjgiLCJtYWNoaW5lX2lkIjoiQU5ZIiwidGllciI6ImFudWFsIn0-60EFBFBDE78F3699
```

### Rodar a Suíte Completa de Testes
```bash
python -m unittest discover -v
```

### Compilar Executável e Gerar Instalador
```bash
# Compilar executável autônomo com PyInstaller
python build_desktop.py

# Gerar instalador Setup.exe para Windows (usando Inno Setup Compiler)
iscc installer/concursodownloader.iss
```
