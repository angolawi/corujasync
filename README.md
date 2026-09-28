# Concurso Downloader - Backup Inteligente de Cursos

Utilitário moderno em Python e aplicação desktop para automatizar o download inteligente, estruturado e resiliente de materiais de estudo (Livros Eletrônicos em PDF, Videoaulas em MP4 e materiais de apoio) com interface gráfica (GUI), compatibilidade com múltiplos navegadores e salvaguardas legais de proteção autoral.

---

## ⚡ Principais Funcionalidades

- **Interface Gráfica Moderna (GUI CustomTkinter):**
  - Aplicação desktop intuitiva em Dark/Light Mode.
  - Seleção facilitada de diretórios, modos de download e qualidades de vídeo.
  - Painel de progresso em tempo real com taxa de transferência (`MB/s`), tempo estimado restante (ETA) e console de logs limpo.
- **Smart Resume (Zero-Overhead):**
  - Mantém o estado dos downloads no arquivo `.download_state.json` dentro da pasta de destino.
  - Pula instantaneamente (0,001s) disciplinas e aulas já finalizadas sem sobrecarregar o navegador.
  - **Bootstrap do Disco:** Reconhece arquivos baixados em sessões anteriores e sincroniza o histórico automaticamente.
- **Suporte Multi-Navegador Resiliente:**
  - Gerenciado nativamente via **Selenium Manager** (Selenium 4.20+).
  - Detecção e inicialização automática: **Microsoft Edge**, **Google Chrome** ou **Mozilla Firefox**.
- **Download Atômico e Resiliente:**
  - Arquivos transferidos via extensão temporária `.part` e renomeados apenas após validação de integridade.
  - Pool de conexões HTTP persistente (*Keep-Alive*) e retries com backoff exponencial.
- **Download de Videoaulas e Materiais de Apoio (`--videos`):**
  - Suporte a resoluções `720p`, `480p` e `360p` com fallback automático.
  - Download sincronizado de *Slides*, *Resumos* e *Mapas Mentais* de cada bloco de vídeo.
- **Blindagem Jurídica e Proteção Técnica Integrada:**
  - **100% Client-Side:** Arquitetura sem servidores centrais, proxies ou nuvem intermediária.
  - **Preservação de Marcas D'água:** Mantém intactos os identificadores digitais e CPFs originais presentes nos PDFs e vídeos, garantindo rastreabilidade contra vazamentos.
  - **EULA Vinculante no 1º Boot:** Termo de responsabilidade obrigatório declarando titularidade legítima de acesso e vedação a compartilhamento pirata (Art. 184 do CP).

---

## 🖥️ Como Executar

### 1. Modo Gráfico Desktop (Padrão)
Para abrir a interface gráfica, basta rodar sem argumentos:
```bash
python main.py
```
*(ou explicitamente com `python main.py --gui`)*

### 2. Modo Linha de Comando (CLI)
Para usuários avançados ou automação via terminal:
```bash
# Download de pacote específico (apenas PDFs)
python main.py --curso 400565 -d "~/Downloads/Concursos"

# Download com videoaulas em 720p
python main.py --curso 400565 -d "~/Downloads/Concursos" --videos

# Download de todos os cursos matriculados
python main.py -d "~/Downloads/Concursos"
```

---

## 🛠️ Instalação e Requisitos

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/DemiurgoGM/AutoDownloadEstrategiaConcurso.git
   cd AutoDownloadEstrategiaConcurso
   ```

2. **Crie e ative o ambiente virtual:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   # .venv\Scripts\activate   # Windows
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Navegador:**
   Tenha instalado o Microsoft Edge, Google Chrome ou Mozilla Firefox atualizado. O driver é gerenciado de forma 100% automática.

---

## 📦 Gerando o Executável Desktop (Standalone)

Para gerar uma versão autônoma (`.exe` no Windows ou binário no Linux) para distribuição sem necessidade de instalar Python:

```bash
python build_desktop.py
```
O executável final pronto para uso será gerado na pasta `dist/ConcursoDownloader`.

---

## ⚙️ Argumentos da Linha de Comando

| Argumento | Tipo | Padrão | Descrição |
|---|---|---|---|
| `--gui` | Flag | `False` | Força a abertura da Interface Gráfica Desktop. |
| `-d, --dir PATH` | Texto | `Downloads/Cursos` | Diretório raiz onde os cursos serão salvos. |
| `--curso URL_OU_ID` | Texto | `None` | URL completa ou ID numérico de um pacote/curso específico. |
| `--videos` | Flag | `False` | Ativa o download das videoaulas (.mp4) e materiais de apoio. |
| `--qualidade` | Opção | `720p` | Qualidade preferencial dos vídeos: `720p`, `480p` ou `360p`. |
| `-e, --email EMAIL` | Texto | `""` | E-mail para tentativa de login automático. |
| `-p, --senha SENHA` | Texto | `""` | Senha para tentativa de login automático. |
| `-w, --wait-time SEC`| Inteiro | `60` | Tempo de espera (em segundos) para login manual no navegador. |
| `--force` | Flag | `False` | Força a checagem manual de tudo no navegador ignorando o cache. |
| `--no-color` | Flag | `False` | Desativa cores e temas especiais no terminal. |

---

## 🏛️ Blindagem Legal, Ética e Isenção de Responsabilidade

1. **Finalidade Estritamente Pessoal:** Este software destina-se **exclusivamente para uso privado de estudo e backup offline** de alunos devidamente matriculados, nos termos do Art. 46, II da Lei de Direitos Autorais (Lei nº 9.610/98).
2. **Vedação de Redistribuição:** O compartilhamento, rateio, venda, upload em redes sociais ou distribuição do material protegido é proibido e configura infração contratual e **crime tipificado no Art. 184 do Código Penal Brasileiro**.
3. **Preservação de Identificadores:** O aplicativo **não remove nem altera marcas d'água** contendo nome e CPF do assinante. O usuário é o único e exclusivo responsável pelo uso e destino dos arquivos baixados.
4. **Desassociação de Marca:** Projeto independente de código aberto. Não possui qualquer vínculo comercial, endosso ou afiliação com a empresa Estratégia Concursos ou qualquer outra entidade educacional.