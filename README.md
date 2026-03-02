## 🧠 Diferenciais Técnicos

### Tratamento de Mídia vs. Documento
Embora o WhatsApp Web utilize um elemento de `input[@type="file"]` comum para uploads, este script separa os fluxos de envio:
- **Modo Mídia:** Aciona o seletor de "Fotos e Vídeos", garantindo que o WhatsApp processe o buffer para visualização rápida.
- **Modo Documento:** Aciona o seletor de "Documento", garantindo a integridade do arquivo original. Isso evita que imagens de alta resolução sejam comprimidas ou convertidas indevidamente em stickers pela inteligência da plataforma.

### Verificação de Fluxo de Saída (Delivery Check)
Diferente de automações simples que apenas disparam o clique, este módulo realiza um polling no DOM em busca do ícone `msg-time` (pendente). O script só libera a próxima tarefa quando confirma que a mensagem foi processada pelo servidor, garantindo que nenhum dado seja perdido em conexões instáveis.