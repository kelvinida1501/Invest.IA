
### Título do Projeto: InvestIA – Assistente Inteligente para Acompanhamento de Investimentos

### Nome do Estudante: Kelvin Katsuo Alves Ida

### Curso: Engenharia de Software

### Data de Entrega: 2025

## Resumo

Este documento apresenta a proposta de desenvolvimento do InvestIA, um sistema para acompanhamento de investimentos com o auxílio de uma Inteligência Artificial com LangChain. O InvestIA busca oferecer ao usuário uma interface interativa para o controle de sua carteira de investimentos, além de fornecer dicas e orientações baseadas em seus dados e no mercado atual. O documento abrange desde o contexto e motivação, até as especificações técnicas, arquitetura da solução e cronograma de desenvolvimento.

## 1. Introdução - 

### 1.1. Contexto
O mercado financeiro brasileiro vivencia uma expansão sem precedentes no número de investidores individuais. Dados da B3 indicam que o número de pessoas físicas na bolsa ultrapassou a marca de 5 milhões, um público que, em grande parte, está em fase inicial de aprendizado. Este cenário de democratização expõe uma lacuna crítica: a carência de ferramentas que traduzam a complexidade do mercado para uma linguagem acessível. Investidores iniciantes frequentemente se deparam com o fenômeno da "infobesidade" (excesso de informação), sentindo-se inseguros com plataformas convencionais que, apesar de repletas de dados, carecem de orientação clara e suporte interpretativo sobre o desempenho de seus próprios ativos.

### 1.2. Justificativa
O desenvolvimento do InvestIA é relevante sob duas óticas principais: acadêmica e de engenharia de software.

#### Relevância para a Engenharia de Software: O projeto integra desenvolvimento web full-stack (FastAPI no back-end e React no front-end), autenticação JWT, arquitetura em N camadas, uso de contêineres Docker e integração com APIs externas, permitindo exercitar práticas modernas de engenharia de software em um cenário realista. 

#### Relevância Acadêmica e Inovação: A proposta inova ao aplicar conceitos de IA generativa e análise de texto ao domínio financeiro, ainda que, no MVP, isso seja feito por meio de um LLM geral (GPT-4o) e de uma análise de sentimento baseada em heurísticas léxicas simples. O uso de frameworks como LangChain e de modelos especializados, como FinBERT, é tratado como possibilidade de evolução futura, e não como parte da implementação atual.

### 1.3. Objetivos

#### 1.3.1. Objetivo Principal
Desenvolver uma aplicação web protótipo (MVP) com suporte de Inteligência Artificial para auxiliar usuários no acompanhamento de seus investimentos, fornecendo análises contextuais e simplificadas para apoiar a tomada de decisões financeiras.

#### 1.3.2. Objetivos Secundários
OE1: Projetar e implementar um agente conversacional baseado em modelos de linguagem via API (por exemplo, GPT-4o), capaz de responder perguntas sobre o desempenho e a composição da carteira do usuário.

OE2: Desenvolver um módulo de registro e visualização de ativos, permitindo que o usuário construa e acompanhe sua carteira de investimentos.

OE3: Criar um sistema de análise de notícias que utilize técnicas de PLN e regras léxicas para estimar o sentimento de informações relevantes aos ativos do usuário (positivo, neutro ou negativo).

OE4: Integrar a aplicação com APIs de dados de mercado (ex: Yahoo Finance) para obter cotações e informações financeiras atualizadas.

OE5: Estruturar a aplicação em uma arquitetura em N camadas, com back-end monolítico em FastAPI, front-end em React e banco PostgreSQL, conteinerizados com Docker, prevendo possibilidade de evolução futura para uma arquitetura de serviços mais distribuída.

## 2. Descrição do Projeto

### 2.1. Tema do Projeto
Sistema inteligente de acompanhamento de investimentos, com painel visual e assistente virtual baseado em IA. O núcleo do sistema é seu módulo de análise automática de notícias, que utiliza processamento de linguagem natural para detectar e classificar o sentimento de notícias relacionadas aos ativos da carteira do usuário. Esse recurso visa simplificar a interpretação do noticiário financeiro e fornecer contexto adicional para auxiliar nas decisões do investidor. A IA será responsável por identificar palavras-chave, extrair entidades relevantes e indicar o possível impacto das notícias.

### 2.2. Problemas a Resolver
- Dificuldade dos usuários em interpretar os dados brutos de sua carteira.

- Falta de orientação personalizada e contextual em plataformas de investimento.

- Excesso de informações técnicas não traduzidas para o usuário final.

### 2.3. Limitações (Escopo Negativo)
- O sistema não fará recomendações de compra/venda de ativos.

- Não será implementada integração com corretoras para execução de ordens.

- O escopo se limita ao acompanhamento e análise de dados, sem movimentações financeiras reais.

- As cotações e notícias dependem de provedores externos (como Yahoo Finance), sujeitos a limites de requisição, instabilidades e variações de latência.

- O cálculo de P/L utiliza o último preço disponível combinado ao preço médio de compra, podendo divergir de extratos oficiais que considerem impostos, proventos e outros ajustes.

- O motor de rebalanceamento é heurístico e pode não gerar sugestões de ordens quando os desvios estiverem abaixo dos limites mínimos configurados.

- Quando não há `OPENAI_API_KEY` configurada, o chat funciona apenas com um resumo local simplificado, sem acesso a modelos de linguagem externos.
  
## 3. Especificação Técnica

### 3.1. Requisitos de Software

#### 3.1.1. Requisitos Funcionais (RF)

- **RF01** :  O sistema deve ser acessado por meio de um navegador web, em uma URL definida pelo projeto. Usuários não autenticados podem apenas visualizar a tela inicial com o fluxo de cadastro/login.
- **RF02**: Permitir cadastro e remoção de ativos na carteira.
- **RF03**: Exibir painel com gráficos de desempenho e alocação.
- **RF04**: Integrar com API de dados financeiros para cotações atualizadas.
- **RF05**: Implementar chat com IA para análise da carteira.
- **RF06**: Gerar dicas e sugestões com base nos dados do usuário.
- **RF07**: Analisar automaticamente notícias relacionadas aos ativos da carteira e classificar seu impacto (positivo, negativo ou neutro) com uso de IA.


#### 3.1.2. Requisitos Não-Funcionais (RNF)
- **RNF01**: A interface deve ser responsiva.
- **RNF02**: O sistema deve buscar manter o tempo de resposta das principais operações (incluindo análises de IA) abaixo de 5 segundos na maior parte dos casos, reconhecendo que chamadas a serviços externos (como Yahoo Finance e API da OpenAI) podem introduzir variações de latência.
- **RNF03**: Os dados do usuário e de sua carteira devem ser armazenados de forma segura no banco de dados.
- **RNF04**: O sistema deve suportar escalabilidade horizontal.
- **RNF05**: IA generativa baseada em modelos de linguagem de grande porte (LLMs), consumidos via API externa (por exemplo, modelo GPT-4o da OpenAI), para o módulo de chat e suporte conversacional ao usuário.  

### 3.2. Considerações de Design

#### 3.2.1. Visão Geral e Padrões de Arquitetura

A solução será estruturada seguindo o padrão Arquitetura em N Camadas, com um back-end monolítico em FastAPI, um banco de dados PostgreSQL acessado por essa API e um front-end SPA em React servido por Nginx, todos empacotados em contêineres Docker via docker-compose, garantindo baixo acoplamento lógico entre camadas e alta coesão dos componentes.

#### 3.2.2. Modelagem C4

Para detalhar a arquitetura, foi utilizado o Modelo C4, que permite a visualização do sistema em diferentes níveis de abstração.

- Nível 1: Contexto
Este diagrama ilustra como o Sistema InvestIA interage com seus usuários e com outros sistemas no ambiente. Ele define os limites e as principais relações do sistema.

![C1](https://github.com/user-attachments/assets/db194816-1065-4c18-bd56-6665955fe833)


- Nível 2: Contêineres
Este diagrama detalha a estrutura interna do Sistema InvestIA, mostrando os principais blocos de construção tecnológicos (contêineres), como a aplicação front-end, a API back-end e o banco de dados.

![C2](https://github.com/user-attachments/assets/f17ff4ae-5564-4c00-90c2-a0a26d7afb9e)


- Nível 3: Componentes
Este diagrama foca no contêiner "API Back-end", detalhando seus componentes internos e como eles colaboram para realizar as funcionalidades do sistema, como autenticação, gerenciamento da carteira e orquestração das análises de IA.

![C3](https://github.com/user-attachments/assets/725a0a64-aacf-4752-abf9-800f05ef1a90)

#### 3.2.3. Diagrama de Casos de Uso

![Casos de Uso](https://github.com/user-attachments/assets/e22d9c3e-edcd-4618-87ba-f7840ef7ec9a)

### 3.3. Tecnologias Utilizadas

#### Linguagem de Programação (Back-end): Python
  
- Justificativa: Escolhido por ser a linguagem padrão da indústria para ciência de dados e IA, com forte ecossistema de bibliotecas (FastAPI, httpx, yfinance, entre outras). Sua sintaxe clara acelera o desenvolvimento e a integração com serviços externos.
- Alternativas: Node.js foi considerado, mas o ecossistema de IA em Python é mais maduro e alinhado aos objetivos do projeto.

#### Framework (Back-end): FastAPI

- Justificativa: Selecionado por sua altíssima performance (comparável a Node.js e Go), suporte nativo a operações assíncronas (essencial para lidar com chamadas de API externas), e geração automática de documentação interativa (Swagger UI), o que otimiza o desenvolvimento e teste da API.
- Alternativas: Django e Flask. FastAPI foi preferido sobre Django por ser mais leve e menos opinativo para a criação de APIs, e sobre Flask por oferecer validação de dados e suporte assíncrono de forma nativa.

#### Framework (Front-end): React.js

- Justificativa: Biblioteca líder para criação de interfaces de usuário ricas e dinâmicas (Single Page Applications). Sua arquitetura baseada em componentes facilita a manutenção e a escalabilidade da UI. Possui uma comunidade vasta e um ecossistema robusto.
- Alternativas: Streamlit, Vue.js. React foi escolhido sobre Streamlit para permitir um maior controle sobre a personalização e a complexidade da UI.

#### Integração com IA: OpenAI API (GPT-4o)

- Justificativa: A integração direta com a API da OpenAI via `httpx` permite consumir modelos de linguagem (como GPT-4o) de forma simples, controlando explicitamente prompts, timeouts e oferecendo fallback local quando não há chave configurada.
- Alternativas: Frameworks de orquestração como LangChain foram estudados para cenários mais complexos (cadeias de ferramentas, múltiplos agentes), mas, no MVP, optou-se por uma implementação direta para reduzir complexidade e dependências.
- 
#### Outras Ferramentas e Bibliotecas:

- Banco de Dados: PostgreSQL, por sua robustez, confiabilidade (ACID) e escalabilidade.

- Containerização: Docker, para garantir a consistência dos ambientes de desenvolvimento e produção e simplificar o deploy.

- Controle de Versão: GitHub, selecionado por conta de sua vasta utilização em âmbito profissional.

- Gestão de Projeto: Trello, para gestão ágil das tarefas, uma vez que sua interface gráfica e simplicidade auxiliam no desenvolvimento.

- APIs Externas: Yahoo Finance, B3 ou similar, pela disponibilidade de um plano gratuito robusto para dados de mercado.

### 3.4. Considerações de Segurança

- **Proteção dos dados sensíveis do usuário com autenticação JWT**
- **Implementação de HTTPS para tráfego seguro.**
- **Evitar injeção de código na interação com LLMs.**
- **Validação de dados e sanitização de entradas.**

### 3.5. – Funcionalidades Implementadas no MVP

- Autenticação e autorização de usuários utilizando JWT para proteger as rotas da API.
- CRUD de ativos, posições e transações, permitindo registrar compras, vendas e ajustes na carteira.
- Importação de posições para facilitar o cadastro inicial da carteira do usuário.
- Resumo da carteira com cálculo de P/L (lucro/prejuízo) e distribuição da alocação por classe de ativo.
- Consulta de histórico de preços e último preço disponível por meio da integração com o Yahoo Finance via biblioteca `yfinance`.
- Questionário de perfil de risco que classifica o investidor (por exemplo, conservador, moderado ou arrojado) e influencia a alocação alvo.
- Motor de rebalanceamento com bandas de tolerância e geração de um plano de ação sugerido (compras/vendas) com base na carteira atual e nas metas de alocação.
- Agregador de notícias relacionadas aos ativos da carteira, com classificação de sentimento heurística (positiva, neutra ou negativa) implementada em `app/services/news.py`.
- Chat integrado a um modelo de linguagem (GPT-4o) chamado via API da OpenAI, com fallback local simplificado quando não há `OPENAI_API_KEY` configurada.

## 4. Próximos Passos

### 4.1 Portfólio I

- **Finalizar definição do escopo e requisitos.**

### 4.2 Portfólio II

- **Entrega projeto.**

## 5. Referências 

- [LangChain](https://docs.langchain.com)  
- [React.js](https://reactjs.org/)  
- [Python](https://www.python.org/)  
- [PostgreSQL](https://www.postgresql.org/docs/)  
- [FastAPI](https://fastapi.tiangolo.com/)  
- [OpenAI API](https://platform.openai.com/docs/overview)

## 6. Apêndices 

## 7. Avaliações de Professores



