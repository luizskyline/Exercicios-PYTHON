#!/usr/bin/env python3
"""
Patreon Advanced Content Downloader
Script avançado para baixar conteúdos pagos do Patreon
Inclui funcionalidades como filtros, configurações avançadas e interface melhorada
"""

import os
import sys
import subprocess
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
import configparser


def normalize_str(normalize_me):
    """Função para normalizar strings (remover caracteres inválidos)"""
    return " ".join(re.sub(r'[<>:!"/\\|?*]', '', normalize_me)
                    .replace('\t', '')
                    .replace('\n', '')
                    .replace('.', '')
                    .split(' ')).strip()


class PatreonAdvancedDownloader:
    def __init__(self, config_file=None):
        self.session_cookie = None
        self.output_dir = "downloads"
        self.patreon_dl_path = "patreon-dl"
        self.config_file = config_file
        self.settings = self.load_settings()
        
        # Adicionar caminhos comuns para patreon-dl no Windows
        self.possible_patreon_dl_paths = [
            "patreon-dl", # Tentar PATH primeiro
            os.path.join(os.environ.get("APPDATA", ""), "npm", "patreon-dl"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm", "patreon-dl"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "nodejs", "patreon-dl"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "nodejs", "patreon-dl"),
        ]
        # Adicionar .cmd para Windows
        if sys.platform == "win32":
            self.possible_patreon_dl_paths = [p + ".cmd" for p in self.possible_patreon_dl_paths] + self.possible_patreon_dl_paths

    def load_settings(self):
        """Carrega configurações do arquivo de configuração"""
        settings = {
            'include_comments': False,
            'include_campaign_info': True,
            'include_content_info': True,
            'include_preview_media': True,
            'include_all_media_variants': True,
            'log_level': 'info',
            'ffmpeg_path': None,
            'filter_by_tier': None,
            'filter_by_date_after': None,
            'filter_by_date_before': None,
            'filter_by_media_type': None
        }
        
        if self.config_file and os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            if 'settings' in config:
                for key, value in config['settings'].items():
                    if key in settings:
                        # Converter strings para tipos apropriados
                        if isinstance(settings[key], bool):
                            settings[key] = config.getboolean('settings', key)
                        else:
                            settings[key] = value
        
        return settings
    
    def save_settings(self):
        """Salva configurações em arquivo"""
        config = configparser.ConfigParser()
        config['settings'] = {}
        
        for key, value in self.settings.items():
            config['settings'][key] = str(value)
        
        config_path = self.config_file or 'patreon_downloader_config.ini'
        with open(config_path, 'w') as f:
            config.write(f)
        
        print(f"Configurações salvas em: {config_path}")
    
    def check_dependencies(self):
        """Verifica dependências necessárias"""
        print("Verificando dependências...")
        
        # Verificar patreon-dl
        found_patreon_dl = False
        for p in self.possible_patreon_dl_paths:
            try:
                result = subprocess.run([p, '--help'], 
                                      capture_output=True, text=True, check=True)
                if result.returncode == 0:
                    self.patreon_dl_path = p
                    found_patreon_dl = True
                    print(f"✅ patreon-dl encontrado em: {self.patreon_dl_path}")
                    break
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        
        if not found_patreon_dl:
            print("❌ patreon-dl não está instalado ou não foi encontrado em nenhum dos caminhos esperados.")
            print("Instale com: npm i -g patreon-dl")
            return False
        
        # Verificar FFmpeg (opcional)
        try:
            ffmpeg_path = self.settings['ffmpeg_path'] or 'ffmpeg'
            result = subprocess.run([ffmpeg_path, '-version'], 
                                  capture_output=True, text=True, check=True)
            if result.returncode == 0:
                print("✅ FFmpeg encontrado!")
            else:
                print("⚠️  FFmpeg não encontrado - alguns vídeos podem não ser baixados.")
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠️  FFmpeg não encontrado - alguns vídeos podem não ser baixados.")
        
        return True
    
    def interactive_setup(self):
        """Configuração interativa inicial"""
        print("\n=== Configuração Inicial ===")
        
        # Cookie de sessão
        if not self.session_cookie:
            print("\nPara baixar conteúdo exclusivo, você precisa do cookie de sessão.")
            print("Consulte 'patreon_cookie_instructions.md' para instruções.")
            cookie = input("Cole o valor do cookie 'session_id': ").strip()
            if cookie:
                self.session_cookie = cookie
        
        # Diretório de saída
        output_dir = input(f"\nDiretório de saída (atual: {self.output_dir}): ").strip()
        if output_dir:
            self.output_dir = output_dir
        
        # Configurações avançadas
        print("\n=== Configurações Avançadas ===")
        
        # Incluir comentários
        include_comments = input("Incluir comentários nos downloads? (s/n): ").lower()
        self.settings['include_comments'] = include_comments in ['s', 'sim', 'y', 'yes']
        
        # Nível de log
        log_levels = ['info', 'debug', 'warn', 'error', 'none']
        print(f"\nNíveis de log disponíveis: {', '.join(log_levels)}")
        log_level = input(f"Nível de log (atual: {self.settings['log_level']}): ").strip()
        if log_level in log_levels:
            self.settings['log_level'] = log_level
        
        # Filtros
        print("\n=== Filtros (opcional) ===")
        
        # Filtro por tier
        tier_filter = input("Filtrar por tier específico (deixe vazio para todos): ").strip()
        if tier_filter:
            self.settings['filter_by_tier'] = tier_filter
        
        # Filtro por tipo de mídia
        media_types = ['video', 'image', 'audio', 'attachment']
        print(f"Tipos de mídia disponíveis: {', '.join(media_types)}")
        media_filter = input("Filtrar por tipo de mídia (deixe vazio para todos): ").strip()
        if media_filter in media_types:
            self.settings['filter_by_media_type'] = media_filter
        
        # Salvar configurações
        save_config = input("\nSalvar essas configurações? (s/n): ").lower()
        if save_config in ['s', 'sim', 'y', 'yes']:
            self.save_settings()
    
    def get_urls_from_file(self, file_path):
        """Lê URLs de um arquivo"""
        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
        except Exception as e:
            print(f"Erro ao ler arquivo {file_path}: {e}")
        
        return urls
    
    def create_advanced_config(self, url):
        """Cria arquivo de configuração avançado para patreon-dl"""
        config_content = f"""# Configuração avançada do patreon-dl
# Gerada automaticamente em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[request]
cookie = session_id={self.session_cookie}
"""
        
        # Adicionar FFmpeg se especificado
        if self.settings['ffmpeg_path']:
            config_content += f"ffmpeg = {self.settings['ffmpeg_path']}\n"
        
        config_content += f"""
[output]
outDir = {os.path.abspath(self.output_dir)}

[include]
# Configurações de inclusão
campaign.info = {str(self.settings['include_campaign_info']).lower()}
content.info = {str(self.settings['include_content_info']).lower()}
preview.media = {str(self.settings['include_preview_media']).lower()}
content.media = true
all.media.variants = {str(self.settings['include_all_media_variants']).lower()}
comments = {str(self.settings['include_comments']).lower()}
"""
        
        # Adicionar filtros se especificados
        if self.settings['filter_by_tier']:
            config_content += f"posts.in.tier = {self.settings['filter_by_tier']}\n"
        
        if self.settings['filter_by_media_type']:
            config_content += f"posts.with.media.type = {self.settings['filter_by_media_type']}\n"
        
        if self.settings['filter_by_date_after']:
            config_content += f"posts.published.after = {self.settings['filter_by_date_after']}\n"
        
        if self.settings['filter_by_date_before']:
            config_content += f"posts.published.before = {self.settings['filter_by_date_before']}\n"
        
        config_content += """
[filenameSanitization]
replaceInvalidChars = true

[logger]
# Configurações de log
"""
        
        # Criar arquivo de configuração
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        config_path = f"patreon_config_{timestamp}.conf"
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        return config_path
    
    def download_content(self, urls):
        """Executa download de múltiplas URLs"""
        if isinstance(urls, str):
            urls = [urls]
        
        total_urls = len(urls)
        successful_downloads = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n{'='*60}")
            print(f"Processando URL {i}/{total_urls}: {url}")
            print(f"{'='*60}")
            
            # Extrair nome do criador
            creator_match = re.search(r'patreon\.com/([^/]+)', url)
            creator_name = creator_match.group(1) if creator_match else f"download_{i}"
            
            # Configurar diretório específico para este criador
            creator_output_dir = os.path.join(self.output_dir, normalize_str(creator_name))
            Path(creator_output_dir).mkdir(parents=True, exist_ok=True)
            
            # Atualizar diretório de saída temporariamente
            original_output_dir = self.output_dir
            self.output_dir = creator_output_dir
            
            try:
                # Criar arquivo de configuração
                config_file = self.create_advanced_config(url)
                
                # Comando patreon-dl
                cmd = [
                    self.patreon_dl_path,
                    '--config-file', config_file,
                    '--log-level', self.settings['log_level'],
                    '--no-prompt',
                    url
                ]
                
                print(f"Executando: {' '.join(cmd)}")
                print("Aguarde... O download pode levar alguns minutos.")
                
                # Executar comando
                process = subprocess.run(cmd, text=True)
                
                if process.returncode == 0:
                    print(f"✅ Download de '{creator_name}' concluído com sucesso!")
                    successful_downloads += 1
                else:
                    print(f"❌ Erro no download de '{creator_name}'. Código: {process.returncode}")
                
                # Limpar arquivo de configuração
                if os.path.exists(config_file):
                    os.remove(config_file)
                    
            except Exception as e:
                print(f"❌ Erro ao processar '{creator_name}': {e}")
            finally:
                # Restaurar diretório original
                self.output_dir = original_output_dir
        
        # Resumo final
        print(f"\n{'='*60}")
        print(f"RESUMO FINAL")
        print(f"{'='*60}")
        print(f"Total de URLs processadas: {total_urls}")
        print(f"Downloads bem-sucedidos: {successful_downloads}")
        print(f"Downloads com erro: {total_urls - successful_downloads}")
        print(f"Conteúdo salvo em: {os.path.abspath(self.output_dir)}")
        
        return successful_downloads == total_urls
    
    def list_creators_tiers(self, creators):
        """Lista tiers para múltiplos criadores"""
        if isinstance(creators, str):
            creators = [creators]
        
        for creator in creators:
            print(f"\n--- Tiers para {creator} ---")
            try:
                cmd = [self.patreon_dl_path, '--list-tiers', creator]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    print(f"Erro ao listar tiers: {result.stderr}")
                    
            except Exception as e:
                print(f"Erro: {e}")
    
    def run_cli(self, args):
        """Executa o downloader via linha de comando"""
        if args.setup:
            self.interactive_setup()
            return True
        
        if not self.check_dependencies():
            return False
        
        # Configurar cookie
        if args.cookie:
            self.session_cookie = args.cookie
        elif not self.session_cookie:
            print("❌ Cookie de sessão necessário!")
            print("Use --cookie ou execute --setup primeiro.")
            return False
        
        # Configurar diretório de saída
        if args.output_dir:
            self.output_dir = args.output_dir
        
        # URLs para processar
        urls = []
        
        if args.urls_file:
            urls.extend(self.get_urls_from_file(args.urls_file))
        
        if args.urls:
            urls.extend(args.urls)
        
        if not urls:
            print("❌ Nenhuma URL fornecida!")
            return False
        
        # Listar tiers se solicitado
        if args.list_tiers:
            creators = []
            for url in urls:
                match = re.search(r'patreon\.com/([^/]+)', url)
                if match:
                    creators.append(match.group(1))
            
            if creators:
                self.list_creators_tiers(creators)
            return True
        
        # Executar downloads
        return self.download_content(urls)
    
    def run_interactive(self):
        """Executa o downloader em modo interativo"""
        print("=== Patreon Advanced Content Downloader ===")
        print("Modo interativo ativado")
        
        if not self.check_dependencies():
            return False
        
        self.interactive_setup()
        
        if not self.session_cookie:
            print("❌ Cookie de sessão necessário para continuar!")
            return False
        
        # Obter URLs
        print("\n=== URLs para Download ===")
        urls = []
        
        while True:
            url = input("Digite uma URL (ou 'fim' para terminar): ").strip()
            if url.lower() in ['fim', 'end', 'done', '']:
                break
            
            if url.startswith("https://www.patreon.com/"):
                urls.append(url)
                print(f"✅ URL adicionada: {url}")
            else:
                print("❌ URL inválida! Deve começar com 'https://www.patreon.com/'")
        
        if not urls:
            print("❌ Nenhuma URL fornecida!")
            return False
        
        # Executar downloads
        return self.download_content(urls)


def main():
    """Função principal com argumentos de linha de comando"""
    parser = argparse.ArgumentParser(
        description="Patreon Advanced Content Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  %(prog)s --setup                           # Configuração interativa
  %(prog)s --cookie "abc123" url1 url2       # Download com cookie
  %(prog)s --urls-file urls.txt              # URLs de arquivo
  %(prog)s --list-tiers creator1 creator2    # Listar tiers
        """
    )
    
    parser.add_argument('urls', nargs='*', help='URLs do Patreon para download')
    parser.add_argument('--cookie', '-c', help='Cookie de sessão do Patreon')
    parser.add_argument('--output-dir', '-o', help='Diretório de saída')
    parser.add_argument('--urls-file', '-f', help='Arquivo com lista de URLs')
    parser.add_argument('--config', help='Arquivo de configuração')
    parser.add_argument('--setup', action='store_true', help='Configuração interativa')
    parser.add_argument('--list-tiers', action='store_true', help='Listar tiers dos criadores')
    
    args = parser.parse_args()
    
    try:
        downloader = PatreonAdvancedDownloader(args.config)
        
        if len(sys.argv) == 1:
            # Modo interativo se nenhum argumento
            success = downloader.run_interactive()
        else:
            # Modo CLI
            success = downloader.run_cli(args)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Operação interrompida pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

