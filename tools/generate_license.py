#!/usr/bin/env python3
"""
Utilitário de linha de comando para geração de chaves de licença para clientes.
Pode ser executado diretamente ou chamado via webhook pós-checkout (Kiwify, Hotmart, Cakto).
"""
import argparse
import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para importações
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from legal.license_manager import generate_license_key, validate_license_key, get_machine_id


def main():
    parser = argparse.ArgumentParser(description="Gerador de Chaves de Licença - CorujaSync")
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("create", help="Gera uma nova chave de licença")
    gen_parser.add_argument("--client", required=True, help="E-mail ou identificador do comprador")
    gen_parser.add_argument(
        "--tier",
        choices=["vitalicio", "anual", "edital", "pro"],
        default="anual",
        help="Plano da licença (vitalicio, anual [365d], edital [180d], pro)",
    )
    gen_parser.add_argument(
        "--machine",
        default="ANY",
        help="Machine ID do comprador (ou 'ANY' para permitir qualquer computador)",
    )
    gen_parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Validade em dias (ignorado se plano for vitalicio)",
    )

    check_parser = subparsers.add_parser("verify", help="Verifica a validade de uma chave")
    check_parser.add_argument("key", help="Chave completa (ex: CSYNC-ANU-...)")

    machine_parser = subparsers.add_parser("my-machine", help="Exibe o Machine ID deste computador")

    args = parser.parse_args()

    if args.command == "create":
        days = args.days
        if days is None:
            if args.tier == "vitalicio":
                days = None
            elif args.tier == "edital":
                days = 180
            else:
                days = 365

        key = generate_license_key(
            client_id=args.client,
            tier=args.tier,
            machine_id=args.machine,
            days_valid=days,
        )
        print("=" * 60)
        print("CHAVE DE LICENÇA GERADA COM SUCESSO:")
        print(f"Cliente:    {args.client}")
        print(f"Plano:      {args.tier.upper()}")
        print(f"Machine ID: {args.machine}")
        print(f"Validade:   {f'{days} dias' if days else 'Vitalícia (Sem Expiração)'}")
        print("-" * 60)
        print(f"Chave: {key}")
        print("=" * 60)

    elif args.command == "verify":
        is_valid, msg, payload = validate_license_key(args.key, enforce_machine=False)
        print("=" * 60)
        print(f"Status:   {'✓ VÁLIDA' if is_valid else '✗ INVÁLIDA'}")
        print(f"Mensagem: {msg}")
        if payload:
            print(f"Cliente:    {payload.get('client')}")
            print(f"Plano:      {payload.get('tier')}")
            print(f"Expira em:  {payload.get('expires_at')}")
            print(f"Machine ID: {payload.get('machine_id')}")
        print("=" * 60)

    elif args.command == "my-machine":
        print(f"Machine ID local: {get_machine_id()}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
