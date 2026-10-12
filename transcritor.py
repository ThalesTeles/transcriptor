"""
Script para transcrever audio de arquivos (.mp4, .mp3, .ogg) usando faster-whisper.

Este script usa o modelo Whisper (da OpenAI) atraves da biblioteca
faster-whisper, uma reimplementacao otimizada (motor CTranslate2) que
roda bem em CPU, sem precisar de GPU nem de muita RAM.

Nota sobre "muitos parametros": os modelos de transcricao Whisper sao
bem menores que LLMs de texto. O "tiny" tem ~39 milhoes de parametros
e o "base" ~74 milhoes -- para comparacao, LLMs de texto costumam ter
bilhoes. Os modelos tiny/base rodam tranquilamente em notebooks comuns,
sem GPU.

INSTALACAO (rodar uma vez no terminal):
    pip install faster-whisper

Diferente do pacote original openai-whisper, o faster-whisper le o
audio com a biblioteca PyAV (que ja traz o FFmpeg embutido) -- nao e
preciso instalar o FFmpeg separadamente no sistema.

USO:
    python transcritor.py caminho/para/audio.ogg
    python transcritor.py caminho/para/pasta_com_arquivos/
    python transcritor.py caminho/para/audio.ogg --saida-dir saidas/aula01
"""

import argparse
import sys
from pathlib import Path

from faster_whisper import WhisperModel


# ----------------- CONFIGURACOES ----------------- #
# Modelos disponiveis (do mais leve/rapido ao mais pesado/preciso):
#   "tiny"     -> ~75 MB  - mais rapido, ideal p/ PC bem fraco
#   "base"     -> ~145 MB - bom equilibrio (padrao deste script)
#   "small"    -> ~484 MB - mais preciso, ainda roda bem em CPU comum
#   "medium"   -> ~1.5 GB - precisa de mais RAM e tempo
#   "large-v3" -> ~3 GB   - recomendado so com GPU ou muita paciencia
MODELO = "small"

# Idioma do audio, para acelerar e melhorar a precisao.
# Use None para deteccao automatica.
IDIOMA = "pt"

# "int8" reduz o uso de memoria e acelera a inferencia em CPU,
# com perda de qualidade praticamente imperceptivel.
COMPUTE_TYPE = "int8"

# Beam size da decodificacao: menor (ex: 1) = mais rapido e mais leve,
# um pouco menos preciso. 5 e o padrao recomendado.
BEAM_SIZE = 5

# Conjunto de extensões aceitas pelo script
# para realizar a transcrição do áudio
EXTENSOES = {'.mp4', '.mp3', '.ogg'}

# Diretorio usado para salvar as transcricoes quando --saida-dir nao e passado
PASTA_SAIDA_PADRAO = "transcricoes"
# --------------------------------------------------- #


def carregar_modelo():
    print(f"Carregando modelo '{MODELO}' (na primeira vez, baixa automaticamente)...")
    return WhisperModel(MODELO, device="cpu", compute_type=COMPUTE_TYPE)


def formatar_tempo(segundos):
    m, s = divmod(int(segundos), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def transcrever_arquivo(model, caminho_video):
    print(f"\n>> Transcrevendo: {caminho_video}")

    segments, info = model.transcribe(
        caminho_video,
        language=IDIOMA,
        beam_size=BEAM_SIZE,
        vad_filter=True,  # pula trechos de silencio: mais rapido e mais limpo
    )

    print(f"   Idioma detectado: {info.language} (confianca: {info.language_probability:.0%})")

    linhas_com_tempo = []
    trechos_texto = []
    for segment in segments:
        inicio = formatar_tempo(segment.start)
        fim = formatar_tempo(segment.end)
        texto = segment.text.strip()
        print(f"   [{inicio} -> {fim}] {texto}")
        linhas_com_tempo.append(f"[{inicio} -> {fim}] {texto}")
        trechos_texto.append(texto)

    return "\n".join(linhas_com_tempo), " ".join(trechos_texto)



def salvar_transcricao(pasta_saida, nome_base, texto_com_tempos, texto_puro):
    pasta = Path(pasta_saida)
    # parents=True cria toda a estrutura de diretorios que ainda nao existir
    pasta.mkdir(parents=True, exist_ok=True)

    arquivo_com_tempos = pasta / f"{nome_base}_com_tempos.txt"
    arquivo_texto = pasta / f"{nome_base}.txt"
    arquivo_com_tempos.write_text(texto_com_tempos, encoding="utf-8")
    arquivo_texto.write_text(texto_puro, encoding="utf-8")

    print(f"   Salvo em: {arquivo_texto} e {arquivo_com_tempos}")


def coletar_arquivos(caminho):
    p = Path(caminho)
    if p.is_dir():
        return sorted(str(f) for f in p.iterdir() if f.is_file() and f.suffix.lower() in EXTENSOES)
    if p.is_file() and p.suffix.lower() in EXTENSOES:
        return [str(p)]
    return []


def ler_argumentos():
    parser = argparse.ArgumentParser(
        description="Transcreve o audio de arquivos usando faster-whisper."
    )
    parser.add_argument(
        "entrada",
        help=f"arquivo ou pasta com arquivos ({', '.join(sorted(EXTENSOES))})",
    )
    parser.add_argument(
        "--saida-dir", "-saida-dir",
        dest="saida_dir",
        default=PASTA_SAIDA_PADRAO,
        help=f"diretorio onde as transcricoes serao salvas (padrao: {PASTA_SAIDA_PADRAO})",
    )
    return parser.parse_args()


def main():
    args = ler_argumentos()

    arquivos = coletar_arquivos(args.entrada)
    if not arquivos:
        print(f"Nenhum arquivo ({', '.join(sorted(EXTENSOES))}) encontrado em: {args.entrada}")
        sys.exit(1)

    print(f"Encontrados {len(arquivos)} arquivo(s).")
    model = carregar_modelo()

    for arquivo in arquivos:
        nome_base = Path(arquivo).stem
        texto_com_tempos, texto_puro = transcrever_arquivo(model, arquivo)
        salvar_transcricao(args.saida_dir, nome_base, texto_com_tempos, texto_puro)

    print("\nConcluido!")


if __name__ == "__main__":
    main()
