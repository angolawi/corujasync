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

## ⚙️ Como Personalizar os Links de Checkout e Suporte

No final do arquivo [`landing/index.html`](file:///home/angolaw/development/AutoDownloadEstrategiaConcurso/landing/index.html), você encontra o objeto de configuração centralizado `APP_CONFIG`. Basta editar os links com os seus endereços reais:

```javascript
const APP_CONFIG = {
  productName: "CorujaSync",
  version: "2.0.0 Pro",
  
  // Link do instalador gratuito (GitHub Releases)
  downloadUrl: "https://github.com/DemiurgoGM/AutoDownloadEstrategiaConcurso/releases/latest",
  
  // Links de Checkout das Plataformas de Pagamento (Kiwify / Hotmart / Cakto)
  checkoutEdital: "https://kiwify.com.br/seu-link-edital",
  checkoutAnual: "https://kiwify.com.br/seu-link-anual",
  checkoutVitalicio: "https://kiwify.com.br/seu-link-vitalicio",
  
  // Contatos de Suporte
  supportEmail: "suporte@corujasync.com",
  whatsappUrl: "https://wa.me/5561999999999?text=Ol%C3%A1%2C%20tenho%20d%C3%BAvidas%20sobre%20o%20CorujaSync"
};
```

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
- **Mockup Interativo do App Desktop:** Permite ao visitante clicar nas abas laterais para visualizar as telas reais de Download, Busca em PDFs e Smart Watcher sem precisar instalar o app.
- **Tabela Comparativa Transparente:** Grátis vs Pro.
- **Tabela de Preços com Ancoragem Comercial:** Planos Edital (R$ 47), Anual (R$ 97) e Vitalício (R$ 147).
- **Salvaguardas Jurídicas Claras:** Citações à Lei de Direitos Autorais (Art. 46, II da Lei 9.610/98) e termo de não afiliação a terceiros.
