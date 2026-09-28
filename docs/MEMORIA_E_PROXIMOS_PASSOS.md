# Memória de Projeto e Handover para Próxima Sessão

**Data:** 27 de Setembro de 2026  
**Status Atual:** Fase 1 a 4 concluídas e testadas com sucesso (16 testes unitários aprovados).  
**Branch:** `master`

---

## 📌 1. O Que Foi Concluído Hoje

### A. Arquitetura Modular e Clean Architecture
- **`core/events.py`:** Sistema de eventos desacoplado (`ProgressEvent`, `StatusEvent`, `DisciplineEvent`, `LessonEvent`, `VideoEvent`) com a interface abstrata `DownloadObserver`.
- **`core/config.py`:** Armazenamento multiplataforma de configurações e preferências nos caminhos padrão do SO (`~/.config/autoconcursodownloader` no Linux, `%LOCALAPPDATA%` no Windows).
- **`core/session.py`:** Sessão HTTP resiliente com Keep-Alive, retries exponenciais e pool de conexões.
- **`core/state_manager.py`:** Persistência atômica de progresso em `.download_state.json` com Smart Resume em 0,001s e bootstrap do disco.
- **`core/downloader.py`:** Download atômico (`.part` -> destino final) com proteção integral de metadados originais.
- **`core/crawler.py` & `core/processor.py`:** Extração e processamento de catálogo de cursos, pacotes, disciplinas, aulas e videoaulas desacoplados da interface.
- **`browser/driver_manager.py`:** Detecção e fallback automático entre navegadores instalados (**Microsoft Edge**, **Google Chrome**, **Mozilla Firefox**) via Selenium Manager nativo.

### B. Interface Gráfica Desktop Moderna (CustomTkinter)
- **`ui/gui/app.py`:** Aplicação desktop em Dark/Light Mode com abas estruturadas (*Download*, *Configurações & Login*, *Termos & Sobre*).
- **`ui/gui/workers.py`:** Worker thread assíncrono conectado via fila thread-safe (`queue.Queue`) — a janela nunca congela e exibe progresso com velocidade em tempo real (`MB/s`), tempo estimado (ETA) e console de logs formatado.
- **Suporte Híbrido:** Executável sem argumentos abre a GUI (`python main.py` ou `python main.py --gui`); executável com flags mantém o modo CLI intacto (`python main.py --curso ...`).

### C. Blindagem Jurídica e Salvaguardas Técnicas
- **EULA Vinculante no 1º Boot:** Modal interativo (`ui/gui/views/eula_dialog.py` e `legal/eula_text.py`) exigindo aceite prévio com declaração de titularidade legítima de acesso e ciência expressa do Art. 184 do Código Penal.
- **Preservação Absoluta das Marcas D'água:** O software não altera marcas d'água dos PDFs/vídeos. O CPF do assinante permanece estampado em todas as páginas, blindando o desenvolvedor contra responsabilidade por vazamentos de terceiros.
- **Arquitetura 100% Client-Side:** Zero servidores intermediários, sem nuvem, sem proxy e sem retenção externa de senhas.

### D. Empacotamento Desktop e Testes
- **`build_desktop.py`:** Script automatizado baseado em PyInstaller para gerar executável autônomo (*zero-setup*) em `dist/ConcursoDownloader`.
- **Suíte de Testes:** 16 testes unitários automatizados passando com 100% de sucesso (`python -m unittest discover -v`).

---

## 🎯 2. Pauta e Próximos Passos para Retomada (Amanhã)

Quando retomarmos, podemos avançar diretamente nas seguintes frentes discutidas hoje:

### Frente 1: Resiliência contra Mudanças de Layout do Site
1. **Módulo de Seletores Remotos "Over-The-Air" (OTA):**
   - Criar `core/selector_manager.py` que consulta um arquivo `selectors.json` (remoto via GitHub Gist ou fallback local).
   - Se o cursinho alterar uma classe CSS ou botão, você atualiza o JSON na nuvem e o app de todos os clientes se autocorrige sem precisar de novo executável.
2. **Interceptação de API Interna (Bypass de CSS):**
   - Capturar requisições JSON da API interna do Estratégia em vez de depender exclusivamente do DOM/HTML.

### Frente 2: Motor de Diagnóstico "Esperado vs. Encontrado"
1. **Módulo de Diagnóstico Automático:**
   - Em caso de falha na extração de PDFs/vídeos, capturar um snapshot semântico da página (filtrando dados sensíveis).
   - Comparar o elemento esperado (`Esperado: a.LessonButton com href da API`) com o que foi encontrado no DOM.
2. **Botão na GUI:**
   - Adicionar botão *"Exportar Diagnóstico / Reportar Falha"* na aba de Download para o cliente gerar um arquivo `.json` ou `.zip` pronto para enviar ao suporte.

### Frente 3: Comercialização e Sistema de Licenciamento
1. **Sistema de Ativação por Chave de Licença (License Key):**
   - Criação de gerador e validador de chaves criptográficas locais (HMAC/RSA) para ativação do software pós-pagamento.
2. **Integração com Plataformas de Checkout:**
   - Estrutura para plugar Kiwify, Hotmart ou Cakto via Webhook.
3. **Estratégia de Precificação:**
   - Definir entre assinatura anual (R$ 49,90/ano) ou licença por edital (R$ 34,90 a R$ 67,00).

### Frente 4: Roadmap de Funcionalidades Premium
- **Smart Watcher:** Download automático em segundo plano quando novas aulas forem postadas.
- **Indexador e Busca Global Offline:** Pesquisa textual em todos os PDFs baixados no computador.
- **Instalador Inno Setup:** Gerador de instalador `.exe` profissional com assistente passo a passo e atalho na Área de Trabalho.

---

## 💻 3. Comandos Úteis para Inicialização Rápida

- **Iniciar a Interface Gráfica:**
  ```bash
  python main.py
  ```
- **Rodar a Suíte de Testes:**
  ```bash
  python -m unittest discover -v
  ```
- **Compilar Novo Executável:**
  ```bash
  python build_desktop.py
  ```
