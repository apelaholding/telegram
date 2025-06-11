import asyncio
import os
import csv
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import MessageActionChatAddUser, MessageActionChatJoinedByLink

api_id = 21867835
api_hash = '12350ab8e581ebbb660900679f8ae0ae'
pasta_sessoes = "contas"
pasta_proxys = "proxys.txt"

if not os.path.exists(pasta_sessoes):
    os.makedirs(pasta_sessoes)

def ler_existente(nome_arquivo):
    existentes = set()
    if os.path.exists(nome_arquivo):
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            next(reader)
            for linha in reader:
                existentes.add((linha[2], linha[3]))
    return existentes

def carregar_proxys():
    if not os.path.exists(pasta_proxys):
        open(pasta_proxys, 'w').close()
    with open(pasta_proxys, 'r', encoding='utf-8') as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]
    print("\n📡 Proxys disponíveis:")
    for i, linha in enumerate(linhas):
        print(f"{i + 1}. {linha}")
    return linhas

def configurar_filtros():
    data_inicio = None
    data_fim = None
    limite = None

    while True:
        print("\n⚙️  Filtros configuráveis:")
        if data_inicio:
            print(f"📅 Data de início: {data_inicio.strftime('%d/%m/%Y')}")
        if data_fim:
            print(f"📅 Data de fim: {data_fim.strftime('%d/%m/%Y')}")
        if limite:
            print(f"👥 Limite de pessoas: {limite}")
        print("1. 📅 Configurar datas")
        print("2. 👥 Configurar limite")
        print("3. ✅ Finalizar filtros")

        op = input("\n🔘 Escolha uma opção: ").strip()
        print("────────────────────────────\n")
        if op == "1":
            try:
                ini = input("📥 Data de início (dd/mm/aaaa): ").strip()
                fim = input("📥 Data de fim (dd/mm/aaaa): ").strip()
                data_inicio = datetime.strptime(ini, "%d/%m/%Y")
                data_fim = datetime.strptime(fim, "%d/%m/%Y")
                if data_inicio > data_fim:
                    print("⚠️ Data de início não pode ser maior que a data de fim.")
                    data_inicio = data_fim = None
            except:
                print("❌ Datas inválidas. Tente novamente.")
        elif op == "2":
            try:
                limite = int(input("👤 Digite o limite de pessoas: ").strip())
            except:
                print("❌ Número inválido.")
        elif op == "3":
            break

    return data_inicio, data_fim, limite

async def processar_grupo(client, nome_conta, grupo, data_inicio, data_fim, limite):
    nome_arquivo = f"{grupo.name.replace(' ', '_')}_entradas.csv"
    ja_salvos = ler_existente(nome_arquivo)
    dados = []
    contador = 0

    async for msg in client.iter_messages(grupo, limit=limite):
        if hasattr(msg, "action"):
            if isinstance(msg.action, (MessageActionChatAddUser, MessageActionChatJoinedByLink)):
                data_msg = msg.date.replace(tzinfo=None)
                if data_inicio and data_msg < data_inicio:
                    continue
                if data_fim and data_msg > data_fim:
                    continue

                if isinstance(msg.action, MessageActionChatAddUser):
                    for uid in msg.action.users:
                        try:
                            user = await client.get_entity(uid)
                            if not user.username:
                                continue
                            nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
                            username = user.username
                            user_id = user.id
                            access_hash = user.access_hash
                            link = f"https://t.me/{username}"
                            dados.append([nome, username, link, user_id, access_hash, grupo.name, grupo.id])
                            contador += 1
                        except:
                            continue

                elif isinstance(msg.action, MessageActionChatJoinedByLink):
                    try:
                        uid = msg.from_id.user_id
                        user = await client.get_entity(uid)
                        if not user.username:
                            continue
                        nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
                        username = user.username
                        user_id = user.id
                        access_hash = user.access_hash
                        link = f"https://t.me/{username}"
                        dados.append([nome, username, link, user_id, access_hash, grupo.name, grupo.id])
                        contador += 1
                    except:
                        continue

                print(f"⏳ [{nome_conta}] Extraindo {grupo.name}... ({contador} encontrados)", end="\r")

                if limite and contador >= limite:
                    break

    if dados:
        modo = "a" if os.path.exists(nome_arquivo) else "w"
        with open(nome_arquivo, modo, newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            if modo == "w":
                writer.writerow(["Nome", "Username", "Link", "ID", "AccessHash", "Grupo", "GrupoID"])
            writer.writerows(dados)

    print(f"\n\n✅ [{nome_conta}] Grupo {grupo.name} finalizado. Total: {contador} usuário(s).")
    print(f"📁 [{nome_conta}] Dados salvos em: {nome_arquivo}")


async def extrair_usuarios(nome_conta, proxy=None):
    session_path = os.path.join(pasta_sessoes, nome_conta)
    client = TelegramClient(session_path, api_id, api_hash, proxy=proxy) if proxy else TelegramClient(session_path, api_id, api_hash)
    await client.start()

    dialogs = await client.get_dialogs()
    grupos = [d for d in dialogs if d.is_group]

    print(f"\n🔍 [{nome_conta}] Verificando grupos com membros válidos...")
    grupos_validos = []
    for g in grupos:
        try:
            async for msg in client.iter_messages(g, limit=100):
                if hasattr(msg, "action") and isinstance(msg.action, (MessageActionChatAddUser, MessageActionChatJoinedByLink)):
                    uid = None
                    if isinstance(msg.action, MessageActionChatAddUser) and msg.action.users:
                        uid = msg.action.users[0]
                    elif isinstance(msg.action, MessageActionChatJoinedByLink) and msg.from_id:
                        uid = msg.from_id.user_id
                    if uid:
                        user = await client.get_entity(uid)
                        if user.username:
                            grupos_validos.append(g)
                            break
        except:
            continue

    if not grupos_validos:
        print(f"[{nome_conta}] Nenhum grupo com membros válidos.")
        await client.disconnect()
        return

    for i, g in enumerate(grupos_validos):
        print(f"{i + 1}. {g.name}")

    escolha = input(f"\n[{nome_conta}] Digite os números dos grupos (ex: 1 2 3): ").strip()
    grupos_escolhidos = [grupos_validos[int(i)-1] for i in escolha.split() if i.isdigit() and 0 < int(i) <= len(grupos_validos)]

    usar_filtro = input(f"[{nome_conta}] Deseja configurar filtros? (s/n): ").lower()
    data_inicio, data_fim, limite = (None, None, None)

    if usar_filtro == "s":
        data_inicio, data_fim, limite = configurar_filtros()

    for grupo in grupos_escolhidos:
        await processar_grupo(client, nome_conta, grupo, data_inicio, data_fim, limite)

    await client.disconnect()

async def main():
    arquivos = [f.replace('.session', '') for f in os.listdir(pasta_sessoes) if f.endswith(".session")]

    if not arquivos:
        print("❌ Nenhuma conta disponível na pasta de sessões.")
        numero = input("📱 Digite o número com DDD (ex: +5511999999999): ").strip()
        nova_session = os.path.join(pasta_sessoes, numero)
        client = TelegramClient(nova_session, api_id, api_hash)
        await client.start(phone=numero)
        await client.disconnect()
        print("✅ Nova conta criada com sucesso.")
        return

    if len(arquivos) == 1:
        conta_unica = arquivos[0]
        print(f"\n🧾 Apenas uma conta encontrada: {conta_unica}")
        print("0. Criar nova conta")
        print(f"1. Usar {conta_unica}")
        escolha = input("Escolha uma opção: ").strip()

        if escolha == "0":
            numero = input("📱 Digite o número com DDD (ex: +5511999999999): ").strip()
            nova_session = os.path.join(pasta_sessoes, numero)
            client = TelegramClient(nova_session, api_id, api_hash)
            await client.start(phone=numero)
            await client.disconnect()
            print("✅ Nova conta criada com sucesso.")
            return

        usar_proxy = input("🔐 Deseja usar proxy? (s/n): ").lower()
        proxy = None
        if usar_proxy == 's':
            proxies = carregar_proxys()
            print("0. ➕ Adicionar novo proxy")
            for i, p in enumerate(proxies):
                print(f"{i + 1}. {p}")
            escolha_proxy = input("Escolha o número do proxy: ").strip()
            if escolha_proxy == "0":
                novo = input("Digite o novo proxy (host:porta:user:senha): ").strip()
                if novo and len(novo.split(":")) == 4:
                    with open(pasta_proxys, 'a', encoding='utf-8') as f:
                        f.write(novo + "\n")
                    linha = novo.split(":")
                    proxy = ('socks5', linha[0], int(linha[1]), True, linha[2], linha[3])
            elif escolha_proxy.isdigit() and 1 <= int(escolha_proxy) <= len(proxies):
                linha = proxies[int(escolha_proxy) - 1].split(":")
                proxy = ('socks5', linha[0], int(linha[1]), True, linha[2], linha[3])

        await extrair_usuarios(conta_unica, proxy)
        return


        usar_proxy = input("🔐 Deseja usar proxy? (s/n): ").lower()
        proxy = None
        if usar_proxy == 's':
            proxies = carregar_proxys()
            print("0. Adicionar novo proxy")
            for i, p in enumerate(proxies):
                print(f"{i + 1}. {p}")

            escolha = int(input("Escolha o número do proxy: ").strip())
            if escolha == 0:
                novo = input("Digite o novo proxy (host:porta:user:senha): ").strip()
                if novo and len(novo.split(":")) == 4:
                    with open(pasta_proxys, 'a', encoding='utf-8') as f:
                        f.write(novo + "\n")
                    linha = novo.split(":")
                    proxy = ('socks5', linha[0], int(linha[1]), True, linha[2], linha[3])
            elif 1 <= escolha <= len(proxies):
                linha = proxies[escolha - 1].split(':')
                if len(linha) == 4:
                    proxy = ('socks5', linha[0], int(linha[1]), True, linha[2], linha[3])

        await extrair_usuarios(arquivos[0], proxy)
        return


    print("\n🧾 Contas disponíveis:")
    for i, nome in enumerate(arquivos, start=1):
        print(f"{i}. {nome}")
    print("0. ➕ Criar nova conta")

    opcao = input("🔘 Digite o número da conta ou 0 para criar uma nova: ").strip()

    if opcao == "0":
        numero = input("📱 Digite o número com DDD (ex: +5511999999999): ").strip()
        nova_session = os.path.join(pasta_sessoes, numero)
        client = TelegramClient(nova_session, api_id, api_hash)
        await client.start(phone=numero)
        await client.disconnect()
        print("✅ Nova conta criada com sucesso.")
        return

    modo_multi = input("🔄 Deseja rodar múltiplas contas? (s/n): ").lower()


    if modo_multi == 's':
        total = int(input(f"Quantas contas deseja rodar? (1 até {len(arquivos)}): ").strip())
        if total < 1 or total > len(arquivos):
            print("❌ Número de contas inválido.")
            return

        usar_proxy = input("🔐 Usar proxy? (s/n): ").lower()
        proxies = carregar_proxys() if usar_proxy == 's' else []

        tarefas = []
        for i in range(total):
            conta = arquivos[i]
            proxy = None
            if usar_proxy == 's' and proxies:
                linha = proxies[i % len(proxies)].split(":")
                proxy = ('socks5', linha[0], int(linha[1]), True, linha[2], linha[3])
            tarefas.append(extrair_usuarios(conta, proxy))

        await asyncio.gather(*tarefas)
    else:
        escolha = int(input("\n🔢 Escolha o número da conta: ")) - 1
        if escolha < 0 or escolha >= len(arquivos):
            print("❌ Escolha inválida.")
            return
        conta = arquivos[escolha]
        await extrair_usuarios(conta)

asyncio.run(main())
