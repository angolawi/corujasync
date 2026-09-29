# 🦉 CorujaSync - Landing Page de Vendas & Documentação

Landing page moderna, responsiva e de alta conversão para o **CorujaSync**, construída em **HTML5 puro + Tailwind CSS** com interatividade em Vanilla JavaScript e zero dependências de compilação.

---

## ⚡ Como Visualizar Localmente

Basta abrir o arquivo `index.html` diretamente no seu navegador ou iniciar um servidor estático local:

```bash
# Opção 1: Via Python (embutido)
python3 -m http.server 8000 --directory landing

# Opção 2: Via npx serve (Node.js)
npx serve landing
```

Acesse em: [http://localhost:8000](http://localhost:8000)

---

## ⚙️ Como Personalizar os Links de Checkout, Suporte e Captura de Leads

No final do arquivo [`index.html`](index.html), você encontra o objeto de configuração centralizado `APP_CONFIG`. Basta editar os links com os seus endereços reais:

```javascript
const APP_CONFIG = {
  productName: "CorujaSync",
  version: "2.0.0 Pro",
  
  // Link do instalador gratuito (GitHub Releases)
  downloadUrl: "https://github.com/corujasync/corujasync/releases/latest",
  
  // Links de Checkout das Plataformas de Pagamento (Kiwify / Hotmart / Cakto)
  checkoutEdital: "https://kiwify.com.br/seu-link-edital",
  checkoutAnual: "https://kiwify.com.br/seu-link-anual",
  checkoutVitalicio: "https://kiwify.com.br/seu-link-vitalicio",
  
  // Contatos de Suporte
  supportEmail: "suporte@corujasync.com",
  whatsappUrl: "https://wa.me/5561999999999?text=Ol%C3%A1%2C%20tenho%20d%C3%BAvidas%20sobre%20o%20CorujaSync",

  // Captura de Leads & Demonstração de Interesse
  leadCapture: {
    // Endpoint opcional de Webhook (Formspree, SheetDB, Google Sheets, Make, Zapier, n8n)
    // Deixe vazio ("") para usar persistência local (localStorage) + WhatsApp direto
    webhookUrl: "",
    // Mensagem inicial de contato direto para a seção de interesse
    whatsappMessage: "Olá! Tenho interesse no CorujaSync e gostaria de receber mais informações e novidades sobre o produto."
  }
};
```

### 📋 Como Funciona a Seção "Tenho Interesse"

A seção `#interesse` permite capturar visitantes interessados em novidades, cupons de desconto ou compatibilidade com preparatórios específicos:

1. **Persistência Automática no Navegador (`localStorage`):**
   - Todos os leads preenchidos são automaticamente salvos na chave `corujasync_leads` do `localStorage`.
   - Você pode consultar os leads no console do navegador a qualquer momento digitando:
     ```javascript
     JSON.parse(localStorage.getItem("corujasync_leads"))
     ```
2. **Integração com Webhook Externo:**
   - Para receber os dados no seu e-mail, planilha do Google ou CRM, basta colar a URL do seu endpoint em `webhookUrl` (ex.: Formspree: `https://formspree.io/f/seu-id`, SheetDB: `https://sheetdb.io/api/v1/...`).
3. **Conversão Imediata via WhatsApp:**
   - Após enviar o formulário, a tela de agradecimento oferece um botão de 1 clique para falar no WhatsApp com uma mensagem pré-formatada contendo o nome do interessado, e-mail, concurso/área e dúvida.
   - Há também um card dedicado de contato rápido via WhatsApp para quem preferir atendimento em tempo real.

---

## 🚀 Opções de Hospedagem Gratuita (1 Clique)

### 1. Vercel
1. Conecte seu repositório no [vercel.com](https://vercel.com).
2. Defina o **Root Directory** como `landing`.
3. Clique em **Deploy**. Sua landing page estará no ar com HTTPS e CDN global.

### 2. Cloudflare Pages
1. Crie um projeto em **Pages** no dashboard da Cloudflare.
2. Selecione este repositório e configure o diretório de build como `landing`.
3. Salve e publique.

### 3. Netlify
1. Arraste e solte a pasta `landing` no [app.netlify.com/drop](https://app.netlify.com/drop).
2. O site fica online em menos de 5 segundos com domínio próprio gratuito.

### 4. GitHub Pages
Você pode servir a landing page diretamente no GitHub Pages:
- Crie uma branch chamada `gh-pages` contendo o conteúdo da pasta `landing/` na raiz da branch, ou copie `index.html` para `docs/` e ative o GitHub Pages apontando para a pasta `/docs` nas configurações do repositório.

---

## 🎨 Características do Design

- **Dark Mode SaaS Premium por padrão** (inspirado em Linear, Raycast e Vercel).
- **Alternador de Tema Dark / Light** com persistência no `localStorage`.
- **Seção de Demonstração Real (#demonstracao):** Player de vídeo HTML5 responsivo com looping silencioso e fallback para GIF animado de 311 KB, demonstrando o download com telemetria e busca global estruturada por Concurso.
- **Mockup Interativo do App Desktop:** Permite ao visitante clicar nas abas laterais para visualizar as telas reais de Download, Busca em PDFs e Smart Watcher sem precisar instalar o app.
- **Tabela Comparativa Transparente:** Grátis vs Pro.
- **Seção de Captura de Leads VIP (#interesse):** Formulário completo de interesse comercial com suporte a Webhooks e WhatsApp direto.

---

## 🎥 Como Regerar o Vídeo e GIF de Demonstração

Para capturar uma nova versão do vídeo/GIF da demonstração automaticamente a partir do código do app desktop:

```bash
# Executa a demonstração automatizada e gera MP4, WebM, GIF e Poster em landing/assets/
python scripts/record_demo.py
```

Os arquivos gerados são otimizados para web:
- `landing/assets/demo.mp4` (~116 KB, H.264 + FastStart)
- `landing/assets/demo.webm` (~171 KB, VP9)
- `landing/assets/demo.gif` (~311 KB, PaletteGen 256 cores)
- `landing/assets/demo_poster.jpg` (~82 KB, frame de capa para carregamento instantâneo)
- **Tabela de Preços com Ancoragem Comercial:** Planos Edital (R$ 47), Anual (R$ 97) e Vitalício (R$ 147).
- **Salvaguardas Jurídicas Claras:** Citações à Lei de Direitos Autorais (Art. 46, II da Lei 9.610/98) e termo de não afiliação a terceiros.
