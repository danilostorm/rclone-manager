# Rclone Manager VPS v1.0.1

Edição Linux/VPS preparada para instalação em `/opt/rclone-manager`, incluindo Oracle Cloud/Ubuntu.

## Backup portátil

Compatível com o **Backup Completo Portátil v2** gerado pelas edições Unraid e ZorinOS. Permite migrar banco de dados, contas Google Drive, configurações do rclone, credenciais OAuth/tokens e Microsoft/OneDrive para a VPS.

> Backups completos contêm credenciais e tokens sensíveis. Guarde-os com segurança.

## OneDrive → Google Drive

Inclui as correções validadas de **Compartilhados comigo**, fallback Microsoft Graph `/content`, retomada e processamento arquivo por arquivo para reduzir o uso do disco local.

## Instalação

```bash
unzip rclone-manager-vps-v1.0.1.zip
cd rclone-manager-vps-v1.0.1
chmod +x install.sh
sudo ./install.sh
```

Diretório padrão: `/opt/rclone-manager`.
