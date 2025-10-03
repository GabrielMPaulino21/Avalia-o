import streamlit as st
import pandas as pd
import os
import plotly.express as px
from PIL import Image
import base64
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
import pytz

# --- FUNÇÃO PARA CODIFICAR IMAGEM (PARA O PLANO DE FUNDO) ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str is None:
        return
        
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: scroll;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)

# --- FUNÇÃO DE VERIFICAÇÃO DE SENHA (VERSÃO MELHORADA) ---
def check_password():
    """Retorna True se o login for bem-sucedido, senão mostra o formulário de login."""

    # Se o usuário já estiver logado, não faz mais nada.
    if st.session_state.get("password_correct", False):
        return True

    # 1. Centralizar o formulário na tela
    _, mid_col, _ = st.columns([1, 2, 1])

    with mid_col:
        # 2. Usar um container para um visual de "card"
        with st.container(border=True):

            # Adiciona a imagem do logo (ajuste o caminho se necessário)
            try:
                st.image("assets/logo_sidebar.png", width=150)
            except Exception as e:
                st.write("") # Não mostra nada se a imagem não for encontrada

            st.subheader("Acesso ao Sistema de Avaliação")

            # 3. Criar o formulário com o botão
            with st.form(key="login_form"):
                password_input = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="••••••••",
                    label_visibility="collapsed" # Esconde o label "Senha"
                )
                login_button = st.form_submit_button(
                    label="Entrar", use_container_width=True, type="primary"
                )

                # 4. Lógica de verificação APÓS o clique no botão
                if login_button:
                    if password_input == st.secrets["APP_PASSWORD"]:
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("Senha incorreta. Tente novamente.")

    # Se o código chegar até aqui, significa que o usuário não está logado.
    return False

# --- CONFIGURAÇÕES DA PÁGINA ---
try:
    page_icon = Image.open("assets/logo_sidebar.png")
except FileNotFoundError:
    page_icon = "📊"

st.set_page_config(
    page_title="AVALIAÇÃO DE FORNECEDORES",
    page_icon=page_icon,
    layout="wide"
)

# --- INÍCIO DA PROTEÇÃO POR SENHA ---
if check_password():

    # --- DADOS E CONSTANTES ---
    ADMIN_KEYS = [('gabriel', 'paulino'), ('rodrigo', 'saito')]
    EMPRESAS = sorted([
        "ABSAFE ENGENHARIA E SEGURANCA", "ASSESSORIA TECNICA ATENE LTDA", "ATUS ENGENHARIA LDA", "BECOMEX CONSULTORIA LTDA",
        "BONA - TERCEIRIZACAO DE MAO-DE-OBRA PARA LOGISTICA LTDA", "CASTELL COMERCIAL DE EQUIPAMENTOS", "CAVE ENGENHARIA E OBRAS LTDA",
        "CHARLES ELBLINK ME", "CLIMAVENT COMERCIO", "CONDUTIVA ENGENHARIA ELETRICA LTDA", "COPE E CIA LTDA",
        "ENGECOMP MANUTENCAO INDUSTRIAL LTDA", "ESTRUTEZZA INDUSTRIA E COMERCIO LTDA", "FRM ENGENHARIA LTDA",
        "GIISAPTEC SOLUCOES INDUSTRIAIS LTDA", "JOSE FERNANDO ALVES JUNIOR EPP", "LOCALLTAINER LOCACOES DE CONTAINERS LTDA.",
        "M GARCIA SERRALHERia E CALDEIRARIA LTDA", "MAMUTH TRANSPORTE DE MAQUINAS LTDA", "MANTEST ENGENHARIA ELETRICA LTDA",
        "MARCATO GESTAO EMPRESarial E TERCEIRIZACAO DE SERVICOS EIRELLI", "MENSURA ENGENHARIA LTDA", "MP ENGENHARIA ELETRICA LTDA.",
        "NOVAC CONSTRUCOES EMPREENDIMENTOS LTDA", "ODOURNET BRASIL LTDA.", "PEOPLE TEAM LTDA",
        "PROENG MONTAGENS E MANUTENCAO INDUSTRIAL LTDA", "RICAMIL ENGENHARIA E SERVICOS LTDA", "RIDARP CONSTRUCOES LTDA",
        "ROCKWELL AUTOMATION DO BRASIL LTDA", "RYCE ENGENHARIA & CONSTRUCAO LTDA.",
        "SGS INDUSTRIAL - INSTALACOES, TESTES E COMISSIONAMENTOS LTDA", "SICK SOLUCAO EM SENSORES LTDA",
        "SIEMENS INFRAESTRUTURA E INDUSTRIA LTDA", "SOS SERVICE COMERCIO E ENGENHARIA LTDA", "SPI INTEGRACAO DE SISTEMAS LTDA",
        "TEC AND TEC LATAM AMERICA LTDA", "TITAN INDUSTRIA E COMERCIO DE FERRAMENTAS E PERIFERICOS LTDA",
        "TOPICO LOCACOES DE GALPOES E EQUIPAMENTOS PARA INDUSTRIAS S.A", "VENDART SOLUCOES INDUSTRIAIS LTDA",
        "VENDOR TRADUCOES TECNICAS E COMERCIO LTDA", "VIVA EQUIPAMENTOS INDUSTRIAIS E COMERCIO LTDA",
        "WORK'S ENGENHARIA E MONTAGENS INDUSTRIAIS LTDA"
    ])
    PERGUNTAS = {
        "SAFETY": { "1.1": "Accidents / near miss", "1.2": "Work Permit (LTR, PPT) performance", "1.3": "EHS documentation (like training certifications and clinic exams (ASO).", "1.4": "Leadership - Safety technician is on work execution", "1.5": "Safety audit" },
        "QUALITY": { "2.1": "Delivering jobs on time", "2.2": "Executions comply with designs", "2.3": "Housekeeping during work execution and after", "2.4": "Work tools condition (personal and equipments)", "2.5": "Delivery jobs on cost" },
        "PEOPLE": { "3.1": "Crew sizing according to approved contracts", "3.2": "Workteam knowledge meet the minimum technical requirements", "3.3": "Leadership - Supervisors is on work execution" },
        "DOCUMENTATION": { "4.1": "Supplier is following accordinly with SAM system requirements (evidences like schedules, measurements, pictures, reports, ART)", "4.2": "Suppliers delivery all the documentation (Company and employees) on time, according to the plan.", "4.3": "Suppliers deliver all the project documentation required (Ex: As Built, Drawings, Data sheets, Manuals, etc)." }
    }
    OPCOES_VOTO = ['1', '2', '3', '4', '5', 'N/A']
    ANOS_AVALIACAO = list(range(2020, 2031))
    RUBRICA = {
        "SAFETY" : {
            "1.1": ["1 OSHA Accident", "1 Serious Accident and 0 OSHA Accident", "0 Accident and 2 or more near miss", "0 Accident and 1 near miss", "0 near miss / accidents"],
            "1.2": ["rarely shows commitment with LTR and PPTs, needs constants improvements and guidances", "sometimes shows commitment with LTR and PPTs, but still needs improvements and guidances.", "shows commitment with LTR and PPTs, requiring punctual orientations.", "Often shows commitment with LTR and PPTs, sharing best practices and process improvements to contributes with safety.", "shows fully commitment with LTR and PPTs, being a partner to the safety and a benchmarking for other companies."],
            "1.3": ["rarely delivery to the EHS on time, needs constants improvements and guidances", "sometimes delivery to the EHS on time, but still needs improvements and guidances.", "delivery to the EHS on time, requiring punctual orientations.", "Often delivery to the EHS on time, sharing best practices and process improvements to contributes with safety.", "shows fully commitment to delivery on time, being a partner to the safety and a benchmarking for other companies."],
            "1.4": ["rarely leadership is present on the job", "sometimes leadership is present on the job, but still needs improvements and guidances.", "leadership is present on the job, requiring punctual orientations.", "Often leadership is present on the job, providing technical support and safety conditions to their associates.", "shows fully commitment to provide leadership full time by service, being a benchmarking for other companies."],
            "1.5": ["rarely shows commitment with objectives and procedures, needs constants improvements and guidances", "sometimes shows commitment with objectives and procedures, but still needs improvements and guidances.", "shows commitment with objectives and procedures, requiring punctual orientations.", "Often shows commitment with objectives and procedures, sharing best practices and process improvements to contributes with business success.", "shows fully commitment with objectives and procedures, being a partner to the business and a benchmarking for other companies."]
        },
        "QUALITY": {
            "2.1": ["rarely shows commitment to delivery on time, needs constants improvements and guidances", "sometimes shows commitment to delivery on time, but still needs improvements and guidances.", "shows commitment to delivery on time, requiring punctual orientations.", "Often shows commitment to delivery on time, applying proactive actions to mitigate delays.", "shows fully commitment to delivery on time, being a partner to the business and a benchmarking for other companies."],
            "2.2": ["rarely shows commitment to execute services according to design, needs constants improvements and guidances", "sometimes shows commitment to execute services according to design, but still needs improvements and guidances.", "shows commitment to execute services according to design, requiring punctual orientations.", "Often shows commitment to execute services according to design, avoiding reworks.", "shows fully commitment to execute services according to design, avoiding reworks and being a benchmarking for other companies."],
            "2.3": ["rarely shows commitment with housekeeping, needs constants improvements and guidances", "sometimes shows commitment with housekeeping, but still needs improvements and guidances.", "shows commitment with housekeeping, requiring punctual orientations.", "Often shows commitment with housekeeping, sharing best practices to contributes with safety.", "shows fully commitment with housekeeping, being a partner to the safety and a benchmarking for other companies."],
            "2.4": ["rarely shows commitment to provide tools and personal protection according to standards, needs constants improvements and guidances", "sometimes shows commitment to provide tools and personal protection according to standards, but still needs improvements and guidances.", "shows commitment to provide tools and personal protection according to standards, requiring punctual orientations.", "Often shows commitment to provide tools and personal protection according to standards, providing safety conditions to their associates.", "shows fully commitment to provide tools and personal protection according to standards, providing safety conditions to their associates and being a benchmarking for other companies."],
            "2.5": ["Overcost > 21%", "15% < Overcost < 20%", "10% < Overcost < 0%", "0%", "Deliver the project with saving"]
        },
        "PEOPLE": {
            "3.1": ["rarely shows commitment to provide resources according to service complexity, needs constants improvements and guidances", "sometimes shows commitment to provide resources according to service complexity, but still needs improvements and guidances.", "shows commitment to provide resources according to service complexity, requiring punctual orientations.", "Often shows commitment to provide resources according to service complexity, with flexibility to mobilize resources quickly in order to avoid any impacts for the business.", "shows fully commitment with objectives and procedures, providing resources according to service complexity, with flexibility to mobilize resources quickly in order to avoid any impacts for the business, being a partner to the business and a benchmarking for other companies."],
            "3.2": ["Full team (leadership and operational) shows low level of qualification, needs replacement.", "operational team are fully dependent of leadership to execute the service, needs improvements.", "shows commitment to provide resources according to service complexity, requiring punctual orientations.", "Often shows commitment to provide resources according to service complexity and requested qualification, presenting plans of development in order to avoid any impacts for the business.", "shows fully commitment with objectives and procedures, providing resources according to service complexity and high qualification of resources required."],
            "3.3": ["rarely leadership is present on the job", "sometimes leadership is present on the job, but still needs improvements and guidances.", "leadership is present on the job, requiring punctual orientations.", "Often leadership is present on the job, providing technical support and safety conditions to their associates.", "shows fully commitment to provide leadership full time by service, being a benchmarking for other companies."]
        },
        "DOCUMENTATION": {
            "4.1": ["rarely shows commitment to provide adequate evidences, needs constants improvements and guidances", "sometimes shows commitment to provide adequate evidences, but still needs improvements and guidances.", "shows commitment to provide to provide adequate evidences, requiring punctual orientations.", "Often shows commitment to provide adequate evidences, sharing best practices and process improvements to contributes with business success.", "shows fully commitment to provide adequate evidences, being a partner to the business and a benchmarking for other companies."],
            "4.2": ["More than 30 days of delay comparing to the plan, to deliver all the documentation", "More than 15 days of delay comparing to the plan, to deliver all the documentation", "Maximum of 5 days of delay comparing to the plan, to deliver all the documentation", "Deliver all the documentation on time, comparing to the plan.", "Deliver all the documentation anticipated"],
            "4.3": ["do not deliver the project documentation according to the contract / scope of work.", "missing no critical project documentation", "deliver all the project documentation according to the contract / scope of work", "deliver more project documentation than requested", "exceed the deliver expectatives"]
        }
    }

    # --- FUNÇÕES DE DADOS (PARA GOOGLE SHEETS) ---
    @st.cache_resource
    def connect_to_gsheet():
        """Conecta ao Google Sheets usando as credenciais do Streamlit Secrets."""
        try:
            creds = st.secrets["gcp_service_account"]
            sa = gspread.service_account_from_dict(creds)
            sh = sa.open(creds["sheet_name"])
            return sh
        except Exception as e:
            st.error(f"Erro ao conectar com o Google Sheets: {e}")
            st.error("Verifique se o arquivo secrets.toml está configurado corretamente.")
            return None

    @st.cache_data(ttl=60)
    def carregar_votos(_spreadsheet):
        """Carrega os votos da primeira aba da planilha do Google."""
        try:
            if _spreadsheet is None:
                return pd.DataFrame() 

            worksheet = _spreadsheet.get_worksheet(0)
            df = pd.DataFrame(worksheet.get_all_records())
            
            colunas_necessarias = ["user_name", "id_avaliacao", "ano_avaliacao", "projeto", "empresa", "categoria", "pergunta_id", "pergunta_texto", "voto", "comentario"]
            if df.empty:
                return pd.DataFrame(columns=colunas_necessarias)
            
            for col in colunas_necessarias:
                if col not in df.columns:
                    df[col] = pd.NA
                    
            df['id_avaliacao'] = pd.to_datetime(df['id_avaliacao'], errors='coerce')
            
            if 'ano_avaliacao' in df.columns:
                df['ano_avaliacao'] = pd.to_numeric(df['ano_avaliacao'], errors='coerce')
                df.dropna(subset=['ano_avaliacao'], inplace=True)
                df['ano_avaliacao'] = df['ano_avaliacao'].astype(int).astype(str)
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar os dados da planilha: {e}")
            return pd.DataFrame()

    def salvar_votos(spreadsheet, df_to_save):
        """Salva o DataFrame completo na primeira aba da planilha."""
        try:
            worksheet = spreadsheet.get_worksheet(0)
            worksheet.clear()
            df_to_save['id_avaliacao'] = df_to_save['id_avaliacao'].astype(str)
            set_with_dataframe(worksheet, df_to_save, include_index=False, allow_formulas=False)
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception as e:
            st.error(f"Erro ao salvar os dados na planilha: {e}")

    @st.cache_data(ttl=600)
    def carregar_projetos(_spreadsheet):
        """Carrega a lista de projetos das abas 'Capex' e 'AME - Quarterly' da Planilha Google."""
        try:
            # Carrega a aba Capex, informando que o cabeçalho está na linha 4
            worksheet_capex = _spreadsheet.worksheet("Capex")
            data_capex = worksheet_capex.get_all_values()
            headers_capex = data_capex[3]
            df_capex = pd.DataFrame(data_capex[4:], columns=headers_capex)
            
            # Carrega a aba AME - Quarterly, informando que o cabeçalho está na linha 4
            worksheet_ame = _spreadsheet.worksheet("AME - Quarterly")
            data_ame = worksheet_ame.get_all_values()
            headers_ame = data_ame[3]
            df_ame = pd.DataFrame(data_ame[4:], columns=headers_ame)

            projetos_capex = []
            if 'WBS' in df_capex.columns and 'PROJECT NAME' in df_capex.columns:
                df_capex.dropna(subset=['WBS', 'PROJECT NAME'], inplace=True)
                df_capex = df_capex[df_capex['WBS'].astype(str).str.strip() != '']
                projetos_capex = (df_capex['WBS'].astype(str) + " - " + df_capex['PROJECT NAME'].astype(str)).tolist()
            
            projetos_ame = []
            if 'WBS' in df_ame.columns and 'PROJECT NAME' in df_ame.columns:
                df_ame.dropna(subset=['WBS', 'PROJECT NAME'], inplace=True)
                df_ame = df_ame[df_ame['WBS'].astype(str).str.strip() != '']
                projetos_ame = (df_ame['WBS'].astype(str) + " - " + df_ame['PROJECT NAME'].astype(str)).tolist()

            todos_projetos = projetos_capex + projetos_ame
            projetos_lcp = [proj for proj in todos_projetos if proj.strip().startswith("LCP")]
            projetos_finais = sorted(list(set(projetos_lcp)))
            
            if not projetos_finais:
                return ["Nenhum projeto LCP encontrado na planilha."]
                
            return projetos_finais
            
        except gspread.exceptions.WorksheetNotFound:
            st.error("ERRO: Abas 'Capex' ou 'AME - Quarterly' não encontradas na Planilha Google.")
            return ["ERRO: Verifique as abas na Planilha Google."]
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar os projetos da planilha: {e}")
            return [f"ERRO: {e}"]

    # --- GERENCIAMENTO DE ESTADO ---
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None
        st.session_state.is_admin = False

    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "📝 NOVA AVALIAÇÃO"

    # --- LÓGICA DE EXIBIÇÃO ---
    if not st.session_state.user_name:
        set_png_as_page_bg('assets/login_fundo.jpg')
        st.markdown("""<style> h1, label { color: black !important; background-color: rgba(255, 255, 255, 0.7); padding: 10px; border-radius: 10px; font-weight: bold !important; } </style>""", unsafe_allow_html=True)
        st.title("Bem-vindo ao Sistema de Avaliação de Fornecedores")
        with st.form("login_form"):
            nome = st.text_input("Digite seu nome completo:", key="login_name")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                if nome:
                    st.session_state.user_name = nome.strip().upper()
                    nome_digitado_lower = st.session_state.user_name.lower()
                    st.session_state.is_admin = any(all(key in nome_digitado_lower for key in key_tuple) for key_tuple in ADMIN_KEYS)
                    st.rerun() 
                else:
                    st.error("Por favor, insira seu nome para continuar.")
    else:
        spreadsheet = connect_to_gsheet()
        df_votos_geral = carregar_votos(spreadsheet)
        
        lista_projetos_lcp = carregar_projetos(spreadsheet)
        set_png_as_page_bg('assets/main_background.png')

        col1, col2 = st.columns([3, 1])
        with col1:
            st.title("RELATÓRIO DE AVALIAÇÃO DE FORNECEDORES")
            st.info("ENGENHARIA DE PROJETOS")
        with col2:
            if os.path.exists("assets/banner_votacao.jpg"):
                st.image("assets/banner_votacao.jpg", width=250) 
                
        st.sidebar.image("assets/logo_sidebar.png")
        st.sidebar.success(f"Logado como:\n**{st.session_state.user_name}**")
        if st.session_state.is_admin:
            st.sidebar.warning("👑 **Nível de Acesso:** Administrador")
        if st.sidebar.button("Sair (Logout)"):
            st.session_state.user_name = None
            st.session_state.is_admin = False
            st.rerun()

        st.sidebar.markdown("---") 
        st.sidebar.markdown(
            """
            <div style="text-align: center; font-size: 0.9em; color: #CCC;">
                Desenvolvido por<br>
                <strong>GABRIEL PAULINO</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        tab_names = [
            "📝 NOVA AVALIAÇÃO", 
            "📂 PROJETOS AVALIADOS",
            "📊 RELATÓRIO DE MÉDIAS",
            "🏆 RANKING",
            "⚙️ DADOS E ADMINISTRAÇÃO"
        ]

        st.session_state.active_tab = st.radio(
            "Navegação", 
            options=tab_names, 
            horizontal=True, 
            label_visibility="collapsed",
            key="tabs_radio" 
        )

        if st.session_state.active_tab == "📝 NOVA AVALIAÇÃO":
            st.header(f"Registrar Nova Avaliação de Projeto")
            st.info("Passo 1: Selecione o contexto da avaliação (Ano, Projeto e Fornecedor).")

            col_ano, col_proj, col_emp = st.columns(3)
            with col_ano:
                ano_atual = datetime.now().year
                default_index = ANOS_AVALIACAO.index(ano_atual) if ano_atual in ANOS_AVALIACAO else 0
                ano_selecionado = st.selectbox("Ano da Avaliação*", options=ANOS_AVALIACAO, index=default_index)
            with col_proj:
                projeto = st.selectbox("Projeto*", options=lista_projetos_lcp, index=None, placeholder="Selecione um projeto...")
            with col_emp:
                empresa_selecionada = st.selectbox("Fornecedor*", options=EMPRESAS, index=None, placeholder="Escolha uma empresa...")
            
            st.markdown("---")

            if projeto and empresa_selecionada and ano_selecionado:
                st.info("Passo 2: Preencha as notas e comentários para a avaliação.")
                
                with st.form(key="form_nova_avaliacao", clear_on_submit=True):
                    st.subheader(f"Avaliação para: {empresa_selecionada} (Projeto: {projeto} / Ano: {ano_selecionado})")
                    
                    for categoria, perguntas_categoria in PERGUNTAS.items():
                        col_titulo, col_botao_criterios = st.columns([4, 1])
                        with col_titulo:
                            st.markdown(f"#### {categoria}")
                        with col_botao_criterios:
                            with st.popover(f"📘 Ver Critérios de {categoria}"):
                                st.markdown(f"### Critérios para: **{categoria}**")
                                legenda_geral = {"Nota": ["1", "2", "3", "4", "5"], "Significado": ["Needs improvement", "Meets partially the expectations", "Meets the expectations", "Exceed partially the expectations", "Exceed the expectations"]}
                                st.table(pd.DataFrame(legenda_geral).set_index('Nota'))
                                st.markdown("---")
                                for pid, ptexto in perguntas_categoria.items():
                                    st.markdown(f"##### Pergunta {pid}: {ptexto}")
                                    if categoria in RUBRICA and pid in RUBRICA[categoria]:
                                        st.table(pd.DataFrame({'Nota': range(1, 6), 'Descrição do Critério': RUBRICA[categoria][pid]}).set_index('Nota'))
                                    else:
                                        st.warning("Critérios para esta pergunta não definidos.")

                        for pid, ptexto in perguntas_categoria.items():
                            st.radio(f"**{pid}** - {ptexto}", OPCOES_VOTO, horizontal=True, key=f"vote_{categoria}_{pid}", index=5)
                        st.text_area("Comentários sobre esta categoria (opcional):", key=f"comment_{categoria}", height=100)
                        st.divider()
                    
                    submitted = st.form_submit_button("Registrar Avaliação")
                    
                    if submitted:
                        fuso_horario_sp = pytz.timezone("America/Sao_Paulo")
                        id_da_avaliacao = datetime.now(fuso_horario_sp)
                        novos_votos = []
                        
                        for categoria, perguntas_categoria in PERGUNTAS.items():
                            comentario_categoria = st.session_state[f"comment_{categoria}"]
                            for pid, ptexto in perguntas_categoria.items():
                                widget_key = f"vote_{categoria}_{pid}"
                                voto_selecionado = st.session_state[widget_key]
                                
                                novos_votos.append({
                                    'user_name': st.session_state.user_name,
                                    'id_avaliacao': id_da_avaliacao,
                                    'ano_avaliacao': ano_selecionado,
                                    'projeto': projeto,
                                    'empresa': empresa_selecionada,
                                    'categoria': categoria,
                                    'pergunta_id': pid,
                                    'pergunta_texto': ptexto,
                                    'voto': voto_selecionado,
                                    'comentario': comentario_categoria
                                })
                        
                        df_novos_votos = pd.DataFrame(novos_votos)
                        df_votos_atualizado = pd.concat([df_votos_geral, df_novos_votos], ignore_index=True)
                        
                        salvar_votos(spreadsheet, df_votos_atualizado)

                        st.success(f"Avaliação para '{empresa_selecionada}' registrada com sucesso!")
                        st.balloons()
                        st.rerun()
            else:
                st.warning("Por favor, selecione o Ano, o Projeto e o Fornecedor para iniciar a avaliação.")

        elif st.session_state.active_tab == "📂 PROJETOS AVALIADOS":
            st.header("Visão Geral de Projetos Avaliados")
            st.info("Esta aba mostra um resumo das avaliações realizadas, sem exibir as notas ou comentários.")
            if df_votos_geral.empty:
                st.info("Nenhuma avaliação de projeto foi registrada ainda.")
            else:
                df_resumo_publico = df_votos_geral[['id_avaliacao', 'ano_avaliacao', 'projeto', 'empresa', 'user_name']].drop_duplicates().sort_values(by='id_avaliacao', ascending=False)
                for index, row in df_resumo_publico.iterrows():
                    with st.expander(f"**Projeto:** {row['projeto']} | **Empresa:** {row['empresa']}"):
                        st.markdown(f"- **Avaliador:** {row['user_name']}")
                        st.markdown(f"- **Ano da Avaliação:** {row['ano_avaliacao']}")
                        if pd.notnull(row['id_avaliacao']):
                            st.markdown(f"- **Data de Registro:** {row['id_avaliacao'].strftime('%d/%m/%Y %H:%M')}")


        elif st.session_state.active_tab == "📊 RELATÓRIO DE MÉDIAS":
            st.header("Análise de Desempenho dos Fornecedores")
            if df_votos_geral.empty:
                st.info("Ainda não há votos registrados.")
            else:
                st.info("Filtre os dados para analisar o desempenho em cenários específicos.")
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    anos_disponiveis = sorted(df_votos_geral['ano_avaliacao'].unique().tolist())
                    anos_filtrados = st.multiselect("Filtrar por Ano(s):", anos_disponiveis)
                with col_f2:
                    projetos_disponiveis = sorted(df_votos_geral['projeto'].unique().tolist())
                    projetos_filtrados = st.multiselect("Filtrar por Projeto(s):", projetos_disponiveis)
                with col_f3:
                    empresas_disponiveis = sorted(df_votos_geral['empresa'].unique().tolist())
                    empresas_filtradas = st.multiselect("Filtrar por Fornecedor(es):", empresas_disponiveis)

                df_filtrado = df_votos_geral.copy()
                if anos_filtrados:
                    df_filtrado = df_filtrado[df_filtrado['ano_avaliacao'].isin(anos_filtrados)]
                if projetos_filtrados:
                    df_filtrado = df_filtrado[df_filtrado['projeto'].isin(projetos_filtrados)]
                if empresas_filtradas:
                    df_filtrado = df_filtrado[df_filtrado['empresa'].isin(empresas_filtradas)]

                df_calculo = df_filtrado[df_filtrado['voto'] != 'N/A'].copy()
                
                if df_calculo.empty:
                    st.warning("Nenhum dado encontrado para os filtros selecionados.")
                else:
                    df_calculo['voto'] = pd.to_numeric(df_calculo['voto'])
                    media_por_categoria = df_calculo.groupby(['empresa', 'categoria'])['voto'].mean().reset_index()
                    media_por_categoria.rename(columns={'voto': 'media_avaliacao'}, inplace=True)
                    
                    st.subheader("Gráficos Individuais por Fornecedor")
                    empresas_avaliadas = sorted(media_por_categoria['empresa'].unique())
                    
                    num_cols = len(empresas_avaliadas)
                    cols = st.columns(min(num_cols, 3) if num_cols > 0 else 1)
                    
                    for i, empresa in enumerate(empresas_avaliadas):
                        df_empresa = media_por_categoria[media_por_categoria['empresa'] == empresa]
                        fig = px.bar(df_empresa, x='categoria', y='media_avaliacao', color='categoria', title=empresa, text_auto='.2f')
                        fig.update_layout(yaxis_range=[0, 5], xaxis_title=None, yaxis_title="Média", showlegend=False, title_font_size=14, title_x=0.05)
                        with cols[i % 3]:
                            st.plotly_chart(fig, use_container_width=True)
                            
                    if len(empresas_avaliadas) > 0:
                        st.markdown("---")
                        st.subheader("Tabela Geral de Médias")
                        tabela_pivot = media_por_categoria.pivot_table(index='empresa', columns='categoria', values='media_avaliacao').round(2)
                        st.dataframe(tabela_pivot, use_container_width=True)
        
        elif st.session_state.active_tab == "🏆 RANKING":
            st.header("🏆 Ranking Geral de Fornecedores")
            if df_votos_geral.empty:
                st.info("Nenhuma avaliação registrada para gerar o ranking.")
            else:
                st.info("Este ranking considera a média de todas as avaliações e o número de avaliações únicas recebidas.")
                df_calculo_ranking = df_votos_geral[df_votos_geral['voto'] != 'N/A'].copy()
                df_calculo_ranking['voto'] = pd.to_numeric(df_calculo_ranking['voto'])
                df_media = df_calculo_ranking.groupby('empresa')['voto'].mean().reset_index()
                df_media.rename(columns={'voto': 'Média Geral'}, inplace=True)
                df_contagem = df_votos_geral.groupby('empresa')['id_avaliacao'].nunique().reset_index()
                df_contagem.rename(columns={'id_avaliacao': 'Nº de Avaliações'}, inplace=True)
                ranking = pd.merge(df_media, df_contagem, on='empresa')
                ranking_ordenado = ranking.sort_values(by='Média Geral', ascending=False).reset_index(drop=True)
                ranking_ordenado.index += 1
                ranking_ordenado['Média Geral'] = ranking_ordenado['Média Geral'].map('{:.2f}'.format)
                st.dataframe(ranking_ordenado, use_container_width=True)

        elif st.session_state.active_tab == "⚙️ DADOS E ADMINISTRAÇÃO":
            st.header("Painel de Administração e Dados")
            if not st.session_state.is_admin:
                st.warning("🔒 Acesso Restrito. Apenas administradores podem visualizar esta aba.")
                st.stop()
            
            st.subheader("Resumo Detalhado das Avaliações")
            if df_votos_geral.empty:
                st.info("Nenhuma participação registrada ainda.")
            else:
                df_votos_geral_sorted = df_votos_geral.dropna(subset=['id_avaliacao']).sort_values(by='id_avaliacao', ascending=False)
                
                for group_keys, df_grupo in df_votos_geral_sorted.groupby(['id_avaliacao', 'ano_avaliacao', 'projeto', 'empresa', 'user_name']):
                    id_aval, ano, proj, emp, user_name = group_keys
                    with st.expander(f"**Data:** {id_aval.strftime('%d/%m/%Y %H:%M')} | **Avaliador:** {user_name} | **Projeto:** {proj}"):
                        st.markdown(f"**Empresa Avaliada:** {emp} | **Ano da Avaliação:** {ano}")
                        st.markdown("**Notas:**")
                        st.dataframe(df_grupo[['categoria', 'pergunta_texto', 'voto']].drop_duplicates().set_index('categoria'))
                        comentarios = df_grupo[['categoria', 'comentario']].drop_duplicates()
                        comentarios = comentarios[comentarios['comentario'].notna() & (comentarios['comentario'] != '')]
                        if not comentarios.empty:
                            st.markdown("**Comentários:**")
                            for _, row in comentarios.iterrows():
                                st.markdown(f"- **{row['categoria']}:** *{row['comentario']}*")
            st.markdown("---")
            
            st.subheader("Administração de Avaliações")
            if not df_votos_geral.empty:
                df_admin_view = df_votos_geral.dropna(subset=['id_avaliacao', 'user_name']).copy()
                usuarios_com_voto = sorted(df_admin_view['user_name'].unique())
                user_selecionado_admin = st.selectbox("1. Selecione o Engenheiro:", usuarios_com_voto, index=None, placeholder="Escolha um usuário...")
                
                if user_selecionado_admin:
                    df_usuario = df_admin_view[df_admin_view['user_name'] == user_selecionado_admin]
                    avaliacoes_unicas = df_usuario[['projeto', 'empresa', 'ano_avaliacao', 'id_avaliacao']].drop_duplicates().sort_values(by='id_avaliacao', ascending=False)
                    
                    mapa_exclusao = {
                        f"Data: {row['id_avaliacao'].strftime('%d/%m/%y %H:%M')} | Ano: {row['ano_avaliacao']} | Projeto: {row['projeto']} | Empresa: {row['empresa']}": row['id_avaliacao']
                        for index, row in avaliacoes_unicas.iterrows()
                    }
                    
                    if not mapa_exclusao:
                        st.info(f"Nenhuma avaliação encontrada para o usuário {user_selecionado_admin}.")
                    else:
                        avaliacao_para_apagar_str = st.selectbox("2. Selecione a avaliação específica para apagar:", list(mapa_exclusao.keys()), index=None, placeholder="Escolha uma avaliação para apagar...")
                        if avaliacao_para_apagar_str:
                            id_para_apagar = mapa_exclusao[avaliacao_para_apagar_str]
                            st.warning(f"Você está prestes a apagar a avaliação de '{user_selecionado_admin}' registrada em {avaliacao_para_apagar_str.split(' | ')[0].replace('Data: ', '')}.")
                            if st.button("Confirmar Exclusão Definitiva", type="primary"):
                                df_final = df_votos_geral[df_votos_geral['id_avaliacao'] != id_para_apagar]
                                salvar_votos(spreadsheet, df_final)
                                st.rerun()

            st.markdown("---")
            st.subheader("Visualizar Todos os Dados Brutos")
            st.dataframe(df_votos_geral, use_container_width=True)
            st.markdown("---")
            
            st.subheader("Zona de Perigo: Apagar Todo o Histórico")
            st.warning("🚨 CUIDADO: Esta ação apagará **TODAS AS AVALIAÇÕES** permanentemente.")
            if st.checkbox("Eu entendo e quero apagar todos os dados."):
                if st.button("APAGAR TUDO", type="primary"):
                    colunas = ['user_name', 'id_avaliacao', 'ano_avaliacao', 'projeto', 'empresa', 'categoria', 'pergunta_id', 'pergunta_texto', 'voto', 'comentario']
                    df_vazio = pd.DataFrame(columns=colunas)
                    salvar_votos(spreadsheet, df_vazio)
                    st.success("Todo o histórico de votos foi apagado da planilha.")
                    st.rerun()