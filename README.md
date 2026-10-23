# 🎵 FlowMusic 360

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows)](https://microsoft.com)
[![Plugin](https://img.shields.io/badge/Flow%20Launcher-Plugin-blueviolet)](https://www.flowlauncher.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Reprodutor de músicas minimalista estilo **Dynamic Island (macOS Sonoma / MyDockFinder)** integrado ao **Flow Launcher**. Projetado para ter **zero lag**, reproduzir suas músicas locais com capas em alta definição e flutuar com pura transparência acrílica de 32 bits.

---

## ✨ Destaques & Funcionalidades

- 🌓 **Tema Duplo Dinâmico:** Alternância instantânea com 1 clique entre o **Tema Claro (Opal Glass)** e o **Tema Escuro (Obsidian Glass)** diretamente no ícone Sol/Lua da ilha ou digitando `m tema`.
- 🏝️ **Ilha Flutuante Acrílica (32-Bit Per-Pixel Alpha):** Janela translúcida nativa Win32 acelerada por GPU (`UpdateLayeredWindow`) com 60 FPS e **0% de uso de CPU**.
- 🔊 **Volume Tátil no Scroll:** Role a rodinha do mouse para cima ou para baixo sobre a ilha para ajustar o volume suavemente!
- 🖼️ **Capas de Álbuns Automáticas:** Baixa e faz cache de capas oficiais via iTunes Search API com recorte squircle antirrugas.
- ⌨️ **Atalhos Globais (Zero Latência):** Registrados nativamente na API do Windows — funcionam mesmo dentro de jogos em tela cheia.
- 📥 **Downloader do YouTube Music Integrado:** Digite `m dl <link>` para baixar playlists inteiras em MP3 em segundo plano.
- 📁 **Gerenciador de Pastas:** Adicione novas pastas de música com `m pasta <caminho>` direto pelo Flow Launcher.

---

## 🚀 Instalação Rápida (1 Clique)

1. Tenha o [Python 3.10+](https://www.python.org/downloads/) e o [Flow Launcher](https://www.flowlauncher.com/) instalados.
2. Baixe ou clone este repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/FlowMusic.git
   cd FlowMusic
   ```
3. Execute o instalador automático:
   ```cmd
   Instalar.bat
   ```
4. Pronto! O Flow Launcher sincronizará o plugin e a ilha iniciará silenciosamente em segundo plano.

---

## 🎮 Controles da Ilha Flutuante

| Elemento | Ação |
| :--- | :--- |
| **Sol / Lua ☀️🌙** | Alterna entre o Tema Claro (Opal) e Escuro (Obsidian). |
| **Fechar ✕** | Oculta a ilha imediatamente. |
| **Barra de Progresso** | Clique em qualquer ponto para avançar ou retroceder a música. |
| **Scroll do Mouse** | Role para cima/baixo para aumentar ou diminuir o volume. |
| **Capa do Álbum** | Clique na capa para pausar / despausar. |
| **Deck Inferior** | `Aleatório`, `Anterior`, `-10s`, `Play/Pause`, `+10s`, `Próximo`, `Favoritar ❤️`. |

---

## ⌨️ Atalhos Globais de Teclado

Funcionam em qualquer tela, janela ou jogo:

| Atalho | Ação |
| :--- | :--- |
| **`Ctrl + Alt + Espaço`** | Play / Pause |
| **`Ctrl + Alt + →`** | Próxima música |
| **`Ctrl + Alt + ←`** | Música anterior |
| **`Ctrl + Alt + ↑`** | Aumentar volume (+10%) |
| **`Ctrl + Alt + ↓`** | Diminuir volume (-10%) |
| **`Ctrl + Alt + M`** | Exibir / Ocultar a Ilha Dinâmica |
| **`Ctrl + Alt + S`** | Alternar Modo Aleatório (Shuffle) |

---

## 🔍 Comandos no Flow Launcher (Palavra-chave: `m`)

| Comando | Descrição |
| :--- | :--- |
| **`m`** | Abre o painel geral (faixa atual, fila, playlists e atalhos). |
| **`m <texto>`** | Busca instantânea por título, artista, número ou álbum. |
| **`m tema`** | Alterna entre o Tema Claro e Escuro. |
| **`m pasta <caminho>`** | Adiciona uma nova pasta à biblioteca de músicas. |
| **`m fav`** | Abre a playlist de músicas favoritas ❤️. |
| **`m dl <link>`** | Baixa uma playlist do YouTube Music diretamente para sua biblioteca. |
| **`m startup`** | Ativa ou desativa a inicialização automática silenciosa com o Windows. |
| **`m hud`** | Alterna a posição da Ilha (*Topo Central*, *Canto Direito*, etc.). |

---

## 🧪 Testes Unitários

Execute a suíte completa de testes automatizados com:
```bash
python -m unittest discover tests
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja [LICENSE](LICENSE) para mais detalhes.
