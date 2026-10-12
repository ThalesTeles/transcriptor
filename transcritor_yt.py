from pathlib import Path
import re

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
    YouTubeRequestFailed,
)

IDIOMAS = ['pt', 'en']
SEPARADOR = "=" * 50

def extrair_id_da_url(url):
    """Extrai o ID do vídeo de qualquer formato de link do YouTube"""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def gera_nome_valido(arquivo: Path) -> Path:
    """
    Retorna um caminho que ainda não existe, adicionando um sufixo numérico
    em caso de colisão (ex: transcricao.txt -> transcricao_1.txt).
    """
    contador_colisoes = 1
    candidato = arquivo
    while candidato.exists():
        candidato = arquivo.with_name(f"{arquivo.stem}_{contador_colisoes}{arquivo.suffix}")
        contador_colisoes += 1
    return candidato

def obter_metadados_video(link: str) -> tuple:
    """
    Tenta extrair os metadados via yt-dlp.
    Retorna: (titulo, video_id).
    Lança: DownloadError, ExtractorError em caso de falha da biblioteca.
    """
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
        'no_warnings': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)

    titulo = info.get('title', "Título não encontrado") if info else "Título não encontrado"
    video_id = info.get('id') if info else None

    return titulo, video_id

def obter_transcricao(video_id: str) -> str:
    """
    Baixa a legenda do vídeo (prioridade: pt, depois en) e retorna o texto puro.
    Lança: as exceções da YouTubeTranscriptApi em caso de falha.
    """
    transcricao = YouTubeTranscriptApi().fetch(video_id, languages=IDIOMAS)
    return TextFormatter().format_transcript(transcricao)

def registrar_falha(arquivo, link, msg_erro, titulo=None) -> None:
    print(msg_erro)
    cabecalho = f"TÍTULO: {titulo}\n" if titulo else ""
    arquivo.write(f"{cabecalho}LINK: {link}\n{msg_erro}\n{SEPARADOR}\n\n")

def gerar_log(caminho_arquivo, sucessos, falhas) -> None:
    """Adiciona ao final do arquivo um resumo da execução."""
    with open(caminho_arquivo, "a", encoding="utf-8") as arquivo:
        arquivo.write("RESUMO DA EXECUÇÃO\n")
        arquivo.write(f"Transcrições obtidas: {sucessos}\n")
        arquivo.write(f"Falhas: {falhas}\n")
        arquivo.write(f"Total de vídeos: {sucessos + falhas}\n")

def gerar_transcricoes(links_videos, caminho_arquivo):
    sucessos = 0
    falhas = 0

    try:
        with open(caminho_arquivo, "x", encoding="utf-8") as arquivo:
            for i, link in enumerate(links_videos, start=1):
                print(f"\n[{i}/{len(links_videos)}] Processando: {link}...")

                video_id = None
                titulo = "Título não encontrado"

                # 1. TENTATIVA DE EXTRAÇÃO DE METADADOS (yt-dlp)
                # Falhar aqui não impede a transcrição: o ID ainda pode ser extraído da URL
                try:
                    titulo, video_id = obter_metadados_video(link)
                except DownloadError:
                    print("Aviso [yt-dlp]: Falha na rede, vídeo privado ou bloqueado. Continuando sem o título...")
                except ExtractorError:
                    print("Aviso [yt-dlp]: O algoritmo de extração falhou (atualize o yt-dlp). Continuando sem o título...")

                # Fallback de ID caso o yt-dlp não extraia
                if not video_id:
                    video_id = extrair_id_da_url(link)

                if not video_id:
                    falhas += 1
                    registrar_falha(arquivo, link, "Erro de Lógica: Link inválido ou formato desconhecido.")
                    continue

                # 2. TENTATIVA DE EXTRAÇÃO DE LEGENDA (YouTubeTranscriptApi)
                try:
                    texto = obter_transcricao(video_id)
                # Tratamento Atômico de Exceções da API
                except TranscriptsDisabled:
                    falhas += 1
                    registrar_falha(arquivo, link, "Erro [API]: O criador do vídeo desativou as legendas.", titulo)
                    continue

                except NoTranscriptFound:
                    falhas += 1
                    msg_erro = f"Erro [API]: Legendas encontradas, mas nenhuma nos idiomas {', '.join(IDIOMAS)}."
                    registrar_falha(arquivo, link, msg_erro, titulo)
                    continue

                except VideoUnavailable:
                    falhas += 1
                    msg_erro = f"Erro [API]: O vídeo '{video_id}' não está mais disponível no YouTube."
                    registrar_falha(arquivo, link, msg_erro, titulo)
                    continue

                except (RequestBlocked, YouTubeRequestFailed) as e:
                    falhas += 1
                    msg_erro = f"Erro [Rede/Bloqueio]: O YouTube bloqueou a requisição ou a rede falhou. Detalhe: {type(e).__name__}"
                    registrar_falha(arquivo, link, msg_erro, titulo)
                    continue

                except Exception as e:
                    # Captura residual apenas para o imponderável (erros de sintaxe ou bibliotecas internas)
                    falhas += 1
                    msg_erro = f"Erro Crítico Inesperado: {e.__class__.__name__} - {e}"
                    registrar_falha(arquivo, link, msg_erro, titulo)
                    continue

                sucessos += 1
                arquivo.write(f"TÍTULO: {titulo}\nLINK: {link}\n{'-' * 50}\n{texto}\n\n{SEPARADOR}\n\n")
                print(f"Sucesso: Transcrição extraída para '{titulo}'")

    except FileExistsError:
        # Se chegar aqui, houve uma Race Condition (muito raro, pois o nome já foi validado antes)
        print(f"\nErro Crítico: O Arquivo {caminho_arquivo.name} foi criado por outro processo no meio da execução.")
        return # Ejeta da função

    # 3. VERIFICAÇÃO FINAL DE ESTADO
    gerar_log(caminho_arquivo, sucessos, falhas)
    print("\n" + "=" * 55)
    if falhas == 0 and sucessos > 0:
        print(f"FINALIZADO COM SUCESSO ABSOLUTO!")
        print(f"O arquivo '{caminho_arquivo.name}' contém {sucessos} transcrições completas.")
    elif sucessos > 0 and falhas > 0:
        print(f"FINALIZADO COM AVISOS!")
        print(f"O arquivo '{caminho_arquivo.name}' foi gerado.")
        print(f"Resumo: {sucessos} extrações completas | {falhas} falhas registradas no log.")
    else:
        print(f"FALHA TOTAL!")
        print(f"O arquivo '{caminho_arquivo.name}' foi gerado, mas NENHUMA transcrição foi obtida.")
        print(f"Resumo: {falhas} falhas registradas no log.")
    print("=" * 55)

def iniciar_programa():
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
    nome_arquivo = input("Qual nome você quer dar ao arquivo? [Pressione Enter para usar 'transcricao.txt']: ").strip()

    if not nome_arquivo:
        nome_arquivo = "transcricao.txt"
    elif not nome_arquivo.lower().endswith('.txt'):
        nome_arquivo += '.txt'

    pasta_destino_obj = Path("transcricoes")
    pasta_destino_obj.mkdir(parents=True, exist_ok=True)

    caminho_completo = gera_nome_valido(pasta_destino_obj / nome_arquivo)
    if caminho_completo.name != nome_arquivo:
        print(f"O arquivo '{nome_arquivo}' já existe. Salvando como '{caminho_completo.name}'.")

    print(f"\nIniciando a extração de {len(links)} vídeo(s)...\n")
    gerar_transcricoes(links, caminho_completo)

if __name__ == "__main__":
    iniciar_programa()
