import streamlit as st
import pandas as pd
import os
import plotly.express as px
from PIL import Image
import base64
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe

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

# --- DADOS E CONSTANTES ---
ARQUIVO_PROJETOS = "BUSCAR_LCP.xlsx" 
ADMIN_KEYS = [('gabriel', 'paulino'), ('rodrigo', 'saito')]
EMPRESAS = sorted([
    "ABSAFE ENGENHARIA E SEGURANCA", "ASSESSORIA TECNICA ATENE LTDA", "ATUS ENGENHARIA LDA", "BECOMEX CONSULTORIA LTDA",
    "BONA - TERCEIRIZACAO DE MAO-DE-OBRA PARA LOGISTICA LTDA", "CASTELL COMERCIAL DE EQUIPAMENTOS", "CAVE ENGENHARIA E OBRAS LTDA",
    "CHARLES ELBLINK ME", "CLIMAVENT COMERCIO", "CONDUTIVA ENGENHARIA ELETRICA LTDA", "COPE E CIA LTDA",
    "ENGECOMP MANUTENCAO INDUSTRIAL LTDA", "ESTRUTEZZA INDUSTRIA E COMERCIO LTDA", "FRM ENGENHARIA LTDA",
    "GIISAPTEC SOLUCOES INDUSTRIAIS LTDA", "JOSE FERNANDO ALVES JUNIOR EPP", "LOCALLTAINER LOCACOES DE CONTAINERS LTDA.",
    "M GARCIA SERRALHERIA E CALDEIRARIA LTDA", "MAMUTH TRANSPORTE DE MAQUINAS LTDA", "MANTEST ENGENHARIA ELETRICA LTDA",
    "MARCATO GESTAO EMPRESARIAL E TERCEIRIZACAO DE SERVICOS EIRELLI", "MENSURA ENGENHARIA LTDA", "MP ENGENHARIA ELETRICA LTDA.",
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

# --- FUNÇÕES DE DADOS ---
@st.cache_resource
def connect_to_gsheet():
    try:
        creds = st.secrets["gcp_service_account"]
        sa = gspread.service_account_from_dict(creds)
        sh = sa.open(st.secrets["gcp_service_account"]["sheet_name"])
        return sh
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        st.error("Verifique se o arquivo secrets.toml está configurado corretamente e se você compartilhou a planilha com o client_email.")
        return None

@st.cache_data(ttl=60)
def carregar_votos(_spreadsheet):
    """Carrega os votos da primeira aba da planilha do Google."""
    try:
        if spreadsheet is None:
            return pd.DataFrame() 

        worksheet = spreadsheet.get_worksheet(0)
        df = pd.DataFrame(worksheet.get_all_records())
        
        colunas_necessarias = ["user_name", "id_avaliacao", "ano_avaliacao", "projeto", "empresa", "categoria", "pergunta_id", "pergunta_texto", "voto", "comentario"]
        if df.empty:
            return pd.DataFrame(columns=colunas_necessarias)
        
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = pd.NA
                
        df['id_avaliacao'] = pd.to_datetime(df['id_avaliacao'])
        df['ano_avaliacao'] = df['ano_avaliacao'].astype(str)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados da planilha: {e}")
        return pd.DataFrame()

def salvar_votos(spreadsheet, df_to_save):
    """Salva o DataFrame completo na primeira aba da planilha."""
    try:
        worksheet = spreadsheet.get_worksheet(0)
        worksheet.clear()
        set_with_dataframe(worksheet, df_to_save, include_index=False, allow_formulas=False)
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception as e:
        st.error(f"Erro ao salvar os dados na planilha: {e}")


@st.cache_data
def carregar_projetos(caminho_arquivo):
    try:
        df_capex = pd.read_excel(caminho_arquivo, sheet_name="Capex", header=3)
        df_ame = pd.read_excel(caminho_arquivo, sheet_name="AME - Quarterly", header=3)
        projetos_capex = []
        if 'WBS' in df_capex.columns and 'PROJECT NAME' in df_capex.columns:
            df_capex.dropna(subset=['WBS', 'PROJECT NAME'], inplace=True)
            projetos_capex = (df_capex['WBS'].astype(str) + " - " + df_capex['PROJECT NAME'].astype(str)).tolist()
        projetos_ame = []
        if 'WBS' in df_ame.columns and 'PROJECT NAME' in df_ame.columns:
            df_ame.dropna(subset=['WBS', 'PROJECT NAME'], inplace=True)
            projetos_ame = (df_ame['WBS'].astype(str) + " - " + df_ame['PROJECT NAME'].astype(str)).tolist()
        todos_projetos = projetos_capex + projetos_ame
        projetos_lcp = [proj for proj in todos_projetos if proj.strip().startswith("LCP")]
        projetos_finais = sorted(list(set(projetos_lcp)))
        return projetos_finais
    except FileNotFoundError:
        st.error(f"ERRO: O arquivo de projetos não foi encontrado em '{caminho_arquivo}'.")
        return ["ERRO: Arquivo de projetos não encontrado"]
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo de projetos: {e}")
        return [f"ERRO: {e}"]

# --- GERENCIAMENTO DE ESTADO ---
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
    st.session_state.is_admin = False

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
    lista_projetos_lcp = carregar_projetos(ARQUIVO_PROJETOS)
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

    tab_votacao, tab_projetos, tab_relatorio, tab_ranking, tab_dados = st.tabs([
        "📝 NOVA AVALIAÇÃO", 
        "📂 PROJETOS AVALIADOS",
        "📊 RELATÓRIO DE MÉDIAS",
        "🏆 RANKING",
        "⚙️ DADOS E ADMINISTRAÇÃO"
    ])
    
    with tab_votacao:
        st.header("Registrar Nova Avaliação de Projeto")
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
                    st.markdown(f"#### {categoria}")
                    for pid, ptexto in perguntas_categoria.items():
                        st.radio(f"**{pid}** - {ptexto}", OPCOES_VOTO, horizontal=True, key=f"vote_{categoria}_{pid}", index=5)
                    st.text_area("Comentários sobre esta categoria (opcional):", key=f"comment_{categoria}", height=100)
                    st.divider()
                
                submitted = st.form_submit_button("Registrar Avaliação")
                
                if submitted:
                    id_da_avaliacao = datetime.now()
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


    with tab_projetos:
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
                    st.markdown(f"- **Data de Registro:** {row['id_avaliacao'].strftime('%d/%m/%Y %H:%M')}")

    with tab_relatorio:
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
                    fig.update_layout(yaxis_range=[0, 5], xaxis_title=None, yaxis_title="Média", showlegend=False, title_font_size=14, title_x=0.5)
                    with cols[i % 3]:
                        st.plotly_chart(fig, use_container_width=True)
                        
                if len(empresas_avaliadas) > 0:
                    st.markdown("---")
                    st.subheader("Tabela Geral de Médias")
                    tabela_pivot = media_por_categoria.pivot_table(index='empresa', columns='categoria', values='media_avaliacao').round(2)
                    st.dataframe(tabela_pivot, use_container_width=True)
    
    with tab_ranking:
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

    with tab_dados:
        st.header("Painel de Administração e Dados")
        if not st.session_state.is_admin:
            st.warning("🔒 Acesso Restrito. Apenas administradores podem visualizar esta aba.")
            st.stop()
        
        st.subheader("Resumo Detalhado das Avaliações")
        if df_votos_geral.empty:
            st.info("Nenhuma participação registrada ainda.")
        else:
            if not pd.api.types.is_datetime64_any_dtype(df_votos_geral['id_avaliacao']):
                df_votos_geral['id_avaliacao'] = pd.to_datetime(df_votos_geral['id_avaliacao'])
            
            for (id_aval, ano, proj, emp, user_name), df_grupo in df_votos_geral.groupby(['id_avaliacao', 'ano_avaliacao', 'projeto', 'empresa', 'user_name']):
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
            usuarios_com_voto = sorted(df_votos_geral['user_name'].unique())
            user_selecionado_admin = st.selectbox("1. Selecione o Engenheiro:", usuarios_com_voto, index=None, placeholder="Escolha um usuário...")
            if user_selecionado_admin:
                df_usuario = df_votos_geral[df_votos_geral['user_name'] == user_selecionado_admin]
                avaliacoes_unicas = df_usuario[['projeto', 'empresa', 'ano_avaliacao', 'id_avaliacao']].drop_duplicates().sort_values(by='id_avaliacao', ascending=False)
                opcoes_exclusao = [f"Data: {row['id_avaliacao'].strftime('%d/%m/%y %H:%M')} | Ano: {row['ano_avaliacao']} | Projeto: {row['projeto']} | Empresa: {row['empresa']}" for index, row in avaliacoes_unicas.iterrows()]
                if not opcoes_exclusao:
                    st.info(f"Nenhuma avaliação encontrada para o usuário {user_selecionado_admin}.")
                else:
                    avaliacao_para_apagar_str = st.selectbox("2. Selecione a avaliação específica para apagar:", opcoes_exclusao, index=None, placeholder="Escolha uma avaliação para apagar...")
                    if avaliacao_para_apagar_str:
                        data_str = avaliacao_para_apagar_str.split(' | ')[0].replace('Data: ', '')
                        id_para_apagar = datetime.strptime(data_str, '%d/%m/%y %H:%M')
                        st.warning(f"Você está prestes a apagar a avaliação de '{user_selecionado_admin}' registrada em {data_str}.")
                        if st.button("Confirmar Exclusão Definitiva", type="primary"):
                            df_final = df_votos_geral[df_votos_geral['id_avaliacao'] != id_para_apagar]
                            salvar_votos(spreadsheet, df_final)
                            st.success("Avaliação apagada com sucesso.")
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