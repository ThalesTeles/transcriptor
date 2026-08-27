import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import os
import re  # Biblioteca nativa do Python para extrair o ID da URL

def extrair_id_da_url(url):
    """Extrai o ID do vídeo de qualquer formato de link do YouTube"""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def gerar_transcricoes(links_videos, nome_arquivo):
    with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
        for i, link in enumerate(links_videos, start=1):
            print(f"[{i}/{len(links_videos)}] Processando: {link}...")

            video_id = None
            titulo = "Título não encontrado"

            # 1. Tentar pegar o título com yt-dlp (Sem travar se falhar)
            try:
                ydl_opts = {
                    'quiet': True,
                    'skip_download': True,
                    'extract_flat': True, # A MÁGICA ESTÁ AQUI: Ignora checagem de formatos de mídia
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(link, download=False)
                    if info:
                        titulo = info.get('title', titulo)
                        video_id = info.get('id', None)
            except Exception as e:
                print("  ⚠️  Aviso: Não foi possível obter o título, mas continuaremos com a transcrição...")

            # Se o yt-dlp falhou, extraímos o ID diretamente da URL com Regex
            if not video_id:
                video_id = extrair_id_da_url(link)

            if not video_id:
                print("  ❌ Erro: Link inválido. Não foi possível identificar o ID do vídeo.")
                continue

            # 2. Baixar a transcrição pelo ID
            try:
                ytt_api = YouTubeTranscriptApi()
                # Use list() pois fetch() retorna um iterador de dicionários e o TextFormatter espera uma lista
                lista_transcricao = list(ytt_api.fetch(video_id, languages=['pt', 'en']))

                formatador = TextFormatter()
                texto_formatado = formatador.format_transcript(lista_transcricao)

                arquivo.write(f"TÍTULO: {titulo}\n")
                arquivo.write(f"LINK: {link}\n")
                arquivo.write("-" * 50 + "\n")
                arquivo.write(texto_formatado + "\n\n")
                arquivo.write("=" * 50 + "\n\n")

                print(f"  ✅ Sucesso: '{titulo}'")

            except Exception as e:
                print(f"  ❌ Erro ao obter transcrição. (Detalhe: {e})")
                arquivo.write(f"TÍTULO: {titulo}\n")
                arquivo.write(f"LINK: {link}\n")
                arquivo.write(f"Erro: Não foi possível obter a transcrição. (Detalhe: {e})\n\n")
                arquivo.write("=" * 50 + "\n\n")

    print("\n" + "=" * 55)
    print(f"🎉 FINALIZADO! O arquivo '{nome_arquivo}' foi salvo com sucesso.")
    print("=" * 55)

def iniciar_programa():
    print("=" * 55)
    print("🎙️  EXTRATOR DE TRANSCRIÇÕES DO YOUTUBE")
    print("=" * 55)
    print("Cole os links dos vídeos abaixo. Para finalizar e gerar")
    print("o arquivo, basta pressionar 'Enter' com a linha vazia.\n")

    links = []
    contador = 1

    while True:
        link = input(f"VÍDEO {contador} - Cole o link (ou Enter vazio para finalizar): ").strip()
        if link == "":
            break
        links.append(link)
        contador += 1

    if not links:
        print("\nNenhum link foi inserido. Programa encerrado.")
        return

    print("\n" + "-" * 55)
    nome_arquivo = input("Qual nome você quer dar ao arquivo? [Pressione Enter para usar 'transcricoes.txt']: ").strip()

    if not nome_arquivo:
        nome_arquivo = "transcricoes.txt"
    elif not nome_arquivo.lower().endswith('.txt'):
        nome_arquivo += '.txt'

    pasta_destino = "transcricoes"

    # Cria a pasta caso ela não exista
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    # Junta o nome da pasta com o nome do arquivo (ex: transcricoes/meu_arquivo.txt)
    caminho_completo = os.path.join(pasta_destino, nome_arquivo)

    print(f"\n⚙️  Iniciando a extração de {len(links)} vídeo(s)...\n")
    # Passa o caminho completo em vez de apenas o nome do arquivo
    gerar_transcricoes(links, caminho_completo)

if __name__ == "__main__":
    iniciar_programa()
