"""Interactive prompts for initial setup and reconfiguration."""

import click
from pathlib import Path
from typing import Dict, Any


def run_initial_setup() -> Dict[str, Any]:
    """Run interactive setup wizard for first-time configuration."""
    click.echo("\n" + "=" * 70)
    click.secho("  Welcome to Instagram Username Extractor! 🎉", fg="cyan", bold=True)
    click.echo("=" * 70)
    click.echo("\nLet's configure your preferences (change anytime with --reconfigure)\n")
    
    config = {}
    
    # Basic settings
    click.secho("📁 Directory Settings", fg="yellow", bold=True)
    click.echo("\n💡 Tip: You can use any directory name - it doesn't have to be 'screenshots'")
    config['input_dir'] = click.prompt(
        "Screenshots directory (can be any folder name)",
        type=str,
        default=str(Path.home() / "Desktop" / "screenshots")
    )
    config['output_dir'] = click.prompt(
        "Output directory",
        type=str,
        default=str(Path.home() / "Desktop" / "leads")
    )
    
    # VLM settings
    click.echo("\n" + "-" * 70)
    click.secho("🤖 Extraction Engine Settings", fg="yellow", bold=True)
    config['vlm_enabled'] = click.confirm(
        "Enable VLM mode for higher accuracy? (slower)",
        default=True
    )
    
    if config['vlm_enabled']:
        vlm_model_choice = click.prompt(
            "VLM model",
            type=click.Choice(['glm-ocr:bf16', 'minicpm-v:8b-2.6-q8_0', 'qwen2.5-vl:7b'], case_sensitive=False),
            default='glm-ocr:bf16',
            show_choices=True
        )
        config['vlm_model'] = vlm_model_choice
    
    config['diagnostics'] = click.confirm(
        "Enable diagnostics mode? (debug images + detailed logs)",
        default=False
    )
    
    # Notion integration
    click.echo("\n" + "-" * 70)
    click.secho("📤 Notion Integration (Optional)", fg="yellow", bold=True)
    notion_enabled = click.confirm(
        "Enable Notion sync?",
        default=True
    )
    
    config['notion'] = {
        "enabled": notion_enabled,
        "token": "",
        "database_id": "",
        "validation_delay": 2.0,
        "skip_validation": False,
        "auto_sync": False,
    }
    
    if notion_enabled:
        config['notion']['token'] = click.prompt(
            "Notion integration token",
            type=str,
            hide_input=True,
            default=""
        )
        config['notion']['database_id'] = click.prompt(
            "Notion database ID",
            type=str,
            default=""
        )
        config['notion']['auto_sync'] = click.confirm(
            "Automatically sync to Notion after extraction?",
            default=True
        )
        config['notion']['skip_validation'] = click.confirm(
            "Skip Instagram validation? (faster but may add invalid accounts)",
            default=False
        )
        if not config['notion']['skip_validation']:
            config['notion']['validation_delay'] = click.prompt(
                "Instagram validation delay (seconds)",
                type=float,
                default=2.0
            )
    
    # Summary
    click.echo("\n" + "=" * 70)
    click.secho("✅ Configuration Complete!", fg="green", bold=True)
    click.echo("=" * 70)
    
    return config


def confirm_config(config: Dict[str, Any]) -> bool:
    """Show current config and ask for confirmation to proceed."""
    click.echo("\n" + "=" * 70)
    click.secho("Current Settings:", fg="cyan", bold=True)
    click.echo("=" * 70)
    click.echo(f"  Input:        {config['input_dir']}")
    click.echo(f"  Output:       {config['output_dir']}")
    click.echo(f"  VLM:          {'Enabled' if config['vlm_enabled'] else 'Disabled'}", nl=False)
    if config['vlm_enabled']:
        click.echo(f" ({config['vlm_model']})")
    else:
        click.echo()
    click.echo(f"  Diagnostics:  {'Enabled' if config['diagnostics'] else 'Disabled'}")
    click.echo(f"  Notion:       {'Enabled' if config['notion']['enabled'] else 'Disabled'}", nl=False)
    if config['notion']['enabled']:
        click.echo(f" (Auto-sync: {'Yes' if config['notion'].get('auto_sync', False) else 'No'})")
    else:
        click.echo()
    click.echo("=" * 70 + "\n")
    
    return click.confirm("Use these settings?", default=True)


def prompt_notion_sync() -> bool:
    """Ask if user wants to sync to Notion after extraction."""
    return click.confirm("\n🔄 Sync results to Notion?", default=True)


def prompt_reconfigure_option() -> str:
    """Prompt for what to reconfigure."""
    click.echo("\n" + "=" * 70)
    click.secho("Reconfigure Settings", fg="cyan", bold=True)
    click.echo("=" * 70)
    
    # Mapping of shortcuts to full options
    shortcuts = {
        'a': 'all',
        'd': 'directories',
        'e': 'extraction',
        'n': 'notion',
        'c': 'cancel'
    }
    
    valid_options = ['all', 'directories', 'extraction', 'notion', 'cancel']
    
    while True:
        choice = click.prompt(
            "What would you like to change?\n  [a]ll / [d]irectories / [e]xtraction / [n]otion / [c]ancel",
            type=str,
            default='all',
            show_default=True
        ).lower().strip()
        
        # Map shortcut to full option
        if choice in shortcuts:
            return shortcuts[choice]
        elif choice in valid_options:
            return choice
        else:
            click.secho(f"  ❌ Invalid option: '{choice}'", fg="red")
            click.echo(f"  Please choose: {', '.join(valid_options)} (or use first letter)\n")


def reconfigure_directories(config: Dict[str, Any]) -> Dict[str, Any]:
    """Reconfigure directory settings."""
    click.secho("\n📁 Directory Settings", fg="yellow", bold=True)
    click.echo("\n💡 Tip: You can specify any directory path - custom names are fully supported")
    config['input_dir'] = click.prompt(
        "Screenshots directory (any folder name or path)",
        type=str,
        default=config.get('input_dir', str(Path.home() / "Desktop" / "screenshots"))
    )
    config['output_dir'] = click.prompt(
        "Output directory",
        type=str,
        default=config.get('output_dir', str(Path.home() / "Desktop" / "leads"))
    )
    return config


def reconfigure_extraction(config: Dict[str, Any]) -> Dict[str, Any]:
    """Reconfigure extraction engine settings."""
    click.secho("\n🤖 Extraction Engine Settings", fg="yellow", bold=True)
    config['vlm_enabled'] = click.confirm(
        "Enable VLM mode for higher accuracy? (slower)",
        default=config.get('vlm_enabled', True)
    )
    
    if config['vlm_enabled']:
        config['vlm_model'] = click.prompt(
            "VLM model",
            type=click.Choice(['glm-ocr:bf16', 'minicpm-v:8b-2.6-q8_0', 'qwen2.5-vl:7b'], case_sensitive=False),
            default=config.get('vlm_model', 'glm-ocr:bf16'),
            show_choices=True
        )
    
    config['diagnostics'] = click.confirm(
        "Enable diagnostics mode?",
        default=config.get('diagnostics', False)
    )
    
    return config


def reconfigure_notion(config: Dict[str, Any]) -> Dict[str, Any]:
    """Reconfigure Notion integration settings."""
    click.secho("\n📤 Notion Integration", fg="yellow", bold=True)
    
    if 'notion' not in config:
        config['notion'] = {}
    
    notion_enabled = click.confirm(
        "Enable Notion sync?",
        default=config['notion'].get('enabled', True)
    )
    
    config['notion']['enabled'] = notion_enabled
    
    if notion_enabled:
        # Show current token/db (masked)
        current_token = config['notion'].get('token', '')
        current_db = config['notion'].get('database_id', '')
        
        if current_token:
            click.echo(f"Current token: {current_token[:10]}... (press Enter to keep)")
        if current_db:
            click.echo(f"Current database: {current_db[:8]}... (press Enter to keep)")
        
        new_token = click.prompt(
            "Notion integration token",
            type=str,
            default=current_token,
            show_default=False,
            hide_input=True
        )
        config['notion']['token'] = new_token if new_token else current_token
        
        new_db = click.prompt(
            "Notion database ID",
            type=str,
            default=current_db,
            show_default=False
        )
        config['notion']['database_id'] = new_db if new_db else current_db
        
        config['notion']['auto_sync'] = click.confirm(
            "Automatically sync to Notion after extraction?",
            default=config['notion'].get('auto_sync', True)
        )
        config['notion']['skip_validation'] = click.confirm(
            "Skip Instagram validation?",
            default=config['notion'].get('skip_validation', False)
        )
        if not config['notion']['skip_validation']:
            config['notion']['validation_delay'] = click.prompt(
                "Instagram validation delay (seconds)",
                type=float,
                default=config['notion'].get('validation_delay', 2.0)
            )
    
    return config
