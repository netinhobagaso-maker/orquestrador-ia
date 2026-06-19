import os
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. CAPTURA DAS VARIÁVEIS DE AMBIENTE (Configuradas no painel da Vercel)
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
        
        # Validação de segurança básica das chaves
        if not all([SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY]):
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Erro Interno: Chaves de ambiente ausentes na Vercel.")
            return

        try:
            # 2. CAPTURA DE PREÇOS EM TEMPO REAL (CoinGecko API)
            url_precos = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,monero&vs_currencies=usd"
            dados_mercado = requests.get(url_precos, timeout=10).json()
            preco_btc = dados_mercado['bitcoin']['usd']
            preco_xmr = dados_mercado['monero']['usd']
            
            # 3. CONSULTA À IA LLAMA DA META (Via API do Groq)
            url_llama = "https://api.groq.com/openai/v1/chat/completions"
            headers_llama = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt_ia = (
                f"Você é a IA gerente de uma operação de mineração na nuvem. O preço atual do Monero é ${preco_xmr} USD. "
                "Se o preço for maior que $130, responda APENAS com a palavra 'LIGAR'. "
                "Se for menor ou igual, responda APENAS com 'DESLIGAR'. Não use pontos ou frases, apenas uma palavra."
            )
            
            payload_llama = {
                "model": "llama3-8b-8192",  # Modelo Oficial Open-Source da Meta
                "messages": [{"role": "user", "content": prompt_ia}],
                "temperature": 0.0
            }
            
            resposta_llama = requests.post(url_llama, json=payload_llama, headers=headers_llama, timeout=10).json()
            decisao_ia = resposta_llama['choices'][0]['message']['content'].strip().upper()
            
            # 4. SALVAR DADOS E DECISÃO DA IA NO SUPABASE
            url_supabase = f"{SUPABASE_URL}/rest/v1/historico_mercado"
            headers_supabase = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            
            dados_salvar = {
                "preco_btc_usd": preco_btc,
                "preco_xmr_usd": preco_xmr,
                "status_rede": f"IA_{decisao_ia}"
            }
            
            requests.post(url_supabase, json=dados_salvar, headers=headers_supabase, timeout=10)
            
            # 5. RETORNO DE SUCESSO NA TELA DO CELULAR
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            
            resposta_sucesso = (
                f"🤖 [SISTEMA NUVEM] Executado com Sucesso!\n"
                f"📊 Preço BTC: ${preco_btc:,} USD\n"
                f"📊 Preço XMR: ${preco_xmr:,} USD\n"
                f"🧠 Comando da IA Llama: {decisao_ia}\n"
                f"💾 Histórico registrado no Supabase."
            )
            self.wfile.write(resposta_sucesso.encode('utf-8'))

        except Exception as e:
            # Tratamento de erros caso alguma API caia
            self.send_response(500)
            self.end_headers()
            erro_msg = f"Falha na execução do Orquestrador: {str(e)}"
            self.wfile.write(erro_msg.encode('utf-8'))
