#%% 

# from sentence_transformers import SentenceTransformer
from prompt_templates import question_answering_prompt_series, question_answering_system
# from openai_interface import GPT_Turbo

from openai import BadRequestError

import logging
import streamlit as st
# from streamlit_option_menu import option_menu
import hydralit_components as hc
import json
import os, requests, re
from datetime import timedelta
import pathlib
import base64
import shutil


def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as file:
        data = file.read()
    return base64.b64encode(data).decode()

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv('env'), override=True)

# I use a key that I increment each time I want to change a text_input
if 'key' not in st.session_state:
    st.session_state.key = 0
# key = st.session_state['key']

if not pathlib.Path('models').exists():
    os.mkdir('models')


# golden_dataset = EmbeddingQAFinetuneDataset.from_json("data/golden_100.json")

## PAGE CONFIGURATION
st.set_page_config(page_title="Ask Impact Theory", 
                #    page_icon="assets/impact-theory-logo-only.png", 
                   page_icon="assets/logos/great_logos.png", 
                   layout="wide", 
                   initial_sidebar_state="collapsed", 
                   menu_items={'Report a bug': "https://www.extremelycoolapp.com/bug"})


# image = "https://is2-ssl.mzstatic.com/image/thumb/Music122/v4/bd/34/82/bd348260-314c-5898-26c0-bef2e0388ebe/source/1200x1200bb.png"
image = "assets/logos/great_logos.png"


def add_bg_from_local(image_file):
    bin_str = get_base64_of_bin_file(image_file)
    page_bg_img = f'''
    <style>
    .stApp {{
      background-image: url("data:image/png;base64,{bin_str}");
      background-size: 100% auto;
      background-repeat: no-repeat;
      background-attachment: fixed;
    }}
    </style>
    ''' 
    
    st.markdown(page_bg_img, unsafe_allow_html=True)

## RERANKER
# reranker = ReRanker('cross-encoder/ms-marco-MiniLM-L-6-v2')
## ENCODING  --> tiktoken library
model_ids = ['gpt-3.5-turbo-16k', 'gpt-3.5-turbo-0613']
# model_nameGPT = model_ids[1]
# encoding = encoding_for_model(model_nameGPT)

## DATA
data_path = './data/impact_theory_data.json'
cache_path = 'data/impact_theory_cache.parquet'
# data = load_data(data_path)
cache = None  # load_content_cache(cache_path) 
# guest_list = sorted(list(set([d['guest'] for d in data])))

if 'secrets' in st.secrets:
#     # st.write("Loading secrets from [secrets] section")
#     # for streamlit online or local, which uses a [secrets] section
    openai_api_key = st.secrets['secrets']['OPENAI_API_KEY']

#     # hf_token = st.secrets['secrets']['LLAMA2_ENDPOINT_HF_TOKEN']
#     # hf_endpoint = st.secrets['secrets']['LLAMA2_ENDPOINT']
    we_are_online = st.secrets['secrets']['ENV'] == 'local'

else :
#     # st.write("Loading secrets for Huggingface")
#     # for Huggingface (no [secrets] section)

    openai_api_key = st.secrets['OPENAI_API_KEY']
    we_are_online = st.secrets['ENV'] == 'local'

    # hf_token = st.secrets['LLAMA2_ENDPOINT_HF_TOKEN']
    # hf_endpoint = st.secrets['LLAMA2_ENDPOINT']
we_are_not_online = not we_are_online

##############

def main():

    with st.sidebar:
        _, center, _ = st.columns([3, 5, 3])
        with center:
            st.text("Search Lab")
            
        _, center, _ = st.columns([2, 5, 3])
        with center:
            if we_are_online:
                st.text("Running ONLINE")
                # st.text("(UNSTABLE)")
            else:
                st.text("Running OFFLINE")
        st.write("----------")

        hybrid_search = st.toggle('Hybrid Search', True)
        if hybrid_search:
            alpha_input = st.slider(label='Alpha',min_value=0.00, 
                                    max_value=1.00, value=0.40, step=0.05, key=1)
            retrieval_limit = st.slider(label='Hybrid Search Results', 
                                        min_value=10, max_value=300, value=10, step=10)

            hybrid_filter = st.toggle('Filter Search using Guest name', True) # i.e. look only at guests' data
            
            rerank = st.toggle('Rerank', True)
            if rerank:
                reranker_topk = st.slider(label='Reranker Top K',min_value=1, max_value=5, value=3, step=1)
            else:
                # needed to not fill the LLM with too many responses (> context size)
                # we could make it dependent on the model
                reranker_topk = 3
            
            rag_it = st.toggle(f"RAG it with SOME MODEL", True)
            if rag_it:
                # st.write(f"Using LLM '{model_nameGPT}'")
                llm_temperature = st.slider(label='LLM T˚', min_value=0.0, 
                                            max_value=2.0, value=0.01, step=0.10 )
        available_models = ['no_model']
        model_name_or_path = st.selectbox(label='Model Name:', 
                                          options=available_models, 
                                          index=available_models.index('no_model'),
                                          placeholder='Select Model')
        
        delete_models = st.button('Delete models')
        if delete_models:
            # model_path = os.path.join("models", model_name_or_path.split('/')[-1])
            # if os.path.isdir(model_path):
            #     shutil.rmtree(model_path) 
            for model in os.listdir("models"):
                model_path = os.path.join("models", model)
                if os.path.isdir(model_path) and 'finetuned-all-mpnet-base-v2-300' not in model_path:
                    shutil.rmtree(model_path)
            st.write("Models deleted")
            
        if we_are_not_online:
            st.write("Experimental and time limited 2'")
            c1,c2 = st.columns([8,1])
            with c1: 
                st.write("Finetuning not available")
        
        # check_model(model_name_or_path)
        # client, available_classes = get_weaviate_client(Wapi_key, url, model_name_or_path, openai_api_key)       
        print("Available classes:", "NONE")
        
        # maybe the free sandbox has expired, or the api key is wrong
        st.sidebar.write(f"Weaviate sandbox not accessible or expired")
        # st.stop()
            
    st.title("Chat with our crypto agents on Discord!")
    # st.image('./assets/impact-theory-logo.png', width=400)
    # st.image('assets/it_tom_bilyeu.png', use_column_width=True)
    st.image('data/logos/great_logo.png', use_column_width=True)
    # st.subheader(f"Chat with the Impact Theory podcast: ")
    st.write('\n')
    # st.stop()
    
    st.write("\u21D0 Open the sidebar to change Search settings \n ")  # https://home.unicode.org also 21E0, 21B0  B2 D0

    if not hybrid_search:
        st.stop()
        
    col1, _ = st.columns([3,7])
    with col1:
        guest = st.selectbox('Select A Guest', 
                             options=["1","2"], 
                             index=None, 
                             placeholder='Select Guest')

    col1, col2 = st.columns([7,3])
    with col1:
        if guest is None:
            msg = f'Select a guest before asking your question:'
        else:
            msg = f'Enter your question about {guest}:'
        
        textbox = st.empty()
        # best solution I found to be able to change the text inside a text_input box afterwards, using a key
        query = textbox.text_input(msg, 
                                  value="", 
                                  placeholder="You can refer to the guest with PRONOUNS",
                                  key=st.session_state.key)
        
        # st.write(f"Guest = {guest}")
        # st.write(f"key = {st.session_state.key}")
                
        st.write('\n\n\n\n\n')

        reworded_query = {'changed': False, 'status': 'error'} # at start, the query is empty
        valid_response = [] # at start, the query is empty, so prevent the search
        
        if query:
                            
            if guest is None:
                st.session_state.key += 1
                query = textbox.text_input(msg, 
                                        value="", 
                                        placeholder="YOU MUST SELECT A GUEST BEFORE ASKING A QUESTION",
                                        key=st.session_state.key)
                # st.write(f"key = {st.session_state.key}")
                st.stop()
            else:
                # st.write(f'It looks like you selected {guest} as a filter (It is ignored for now).')
                
                with col2:
                    # let's add a nice pulse bar while generating the response
                    with hc.HyLoader('', hc.Loaders.pulse_bars, primary_color= 'red', height=50):  #"#0e404d" for image green

                        with col1:
                            
                            if st.toggle('Rewrite query with LLM', True):
                
                                # let's use Llama2, and fall back on GPT3.5 if it fails
                                # reworded_query = reword_query(query, guest, 
                                #                             model_name='gpt-3.5-turbo-0125')
                                new_query = query
                                
                                guest_lastname = 'john'
                                    
                                query = new_query
                                st.write(f"New query: {query}")
                            
                       
                            # hybrid_response = client.hybrid_search(query, 
                            #                                     class_name, 
                            #                                     # properties=['content'], #['title', 'summary', 'content'],
                            #                                     alpha=alpha_input,
                            #                                     display_properties=client.display_properties,
                            #                                     where_filter=where_filter,
                            #                                     limit=retrieval_limit)
                            hybrid_response = 'a response'
                            response = hybrid_response

                            if rerank:
                                # rerank results with cross encoder
                                # ranked_response = reranker.rerank(response, query,
                                #                                 apply_sigmoid=True, # score between 0 and 1
                                #                                 top_k=reranker_topk)
                                # logger.info(ranked_response)
                                # expanded_response = expand_content(ranked_response, cache, 
                                #                                 content_key='doc_id', 
                                #                                 create_new_list=True)

                                response = expanded_response

                        # make sure token count < threshold
                        # token_threshold = 8000 if model_nameGPT == model_ids[0] else 3500
                        valid_response = response
                        # st.write(f"Number of results: {len(valid_response)}")
                        
    # I jumped out of col1 to get all page width, so need to retest query
    if query:     

        # creates container for LLM response to position it above search results
        chat_container, response_box = [], st.empty()                        
        # # RAG time !! execute chat call to LLM
        if rag_it:
            # st.subheader("Response from Impact Theory (context)") 
            # will appear under the answer, moved it into the response box

            # generate LLM prompt
            prompt = "some prompt"  #generate_prompt_series(query=query, results=valid_response)

            
            # GPTllm = GPT_Turbo(model=model_nameGPT, 
            #                 api_key=openai_api_key)
            # try:
            #     #   inserts chat stream from LLM
            #     for resp in GPTllm.get_chat_completion(prompt=prompt,
            #                                             temperature=llm_temperature,
            #                                             max_tokens=350,
            #                                             show_response=True,
            #                                             stream=True):
                    
            #         with response_box:
            #             content = resp.choices[0].delta.content
            #             if content:
            #                 chat_container.append(content)
            #                 result = "".join(chat_container).strip()
            #                 response_box.markdown(f"### Response from Impact Theory (RAG):\n\n{result}")
            # except BadRequestError as e:
            #     logger.info('Making request with smaller context')

            #     valid_response = validate_token_threshold(response,
            #                                             question_answering_prompt_series,
            #                                             query=query,
            #                                             tokenizer=encoding,
            #                                             token_threshold=3500,
            #                                             verbose=True)
            #     # if reranker is off, we may receive a LOT of responses
            #     # so we must reduce the context size manually
            #     if not rerank:
            #         valid_response = valid_response[:reranker_topk]
                                    
            #     prompt = generate_prompt_series(query=query, results=valid_response)
            #     for resp in GPTllm.get_chat_completion(prompt=prompt,
            #                                         temperature=llm_temperature,
            #                                         max_tokens=350,  # expand for more verbose answers
            #                                         show_response=True,
            #                                         stream=True):
            #         try:
            #             # inserts chat stream from LLM
            #             with response_box:
            #                 content = resp.choice[0].delta.content
            #                 if content:
            #                     chat_container.append(content)
            #                     result = "".join(chat_container).strip()
            #                     response_box.markdown(f"### Response from Impact Theory (RAG):\n\n{result}")
            #         except Exception as e:
            #             print(e)
                    
        st.markdown("----")
        st.subheader("Search Results")

        for i, hit in enumerate(valid_response):
            col1, col2 = st.columns([7, 3], gap='large')
            # image = hit['thumbnail_url'] # get thumbnail_url
            # episode_url = hit['episode_url'] # get episode_url
            # title = hit["title"] # get title
            show_length = 300 #hit["length"] # get length
            time_string = str(timedelta(seconds=show_length)) # convert show_length to readable time string

            with col1:
                st.write("col 1")
                # st.write(search_result(i=i,
                #                         url=episode_url,
                #                         guest=hit['guest'],
                #                         title=title,
                #                         content='',
                #                         length=time_string),
                #                         unsafe_allow_html=True)
                st.write('\n\n')
            
            with col2:
                #st.write(f"<a href={episode_url} <img src={image} width='200'></a>",
                #         unsafe_allow_html=True)
                #st.markdown(f"[![{title}]({image})]({episode_url})")
                # st.markdown(f'<a href="{episode_url}">'
                #            f'<img src={image} '
                #            f'caption={title.split("|")[0]} width=200, use_column_width=False />'
                #            f'</a>',
                #            unsafe_allow_html=True)
                st.image('assets/download.jpg')
                # st.image(image, caption=title.split('|')[0], width=200, use_column_width=False)
            # let's use all width for the content
            st.write("something something")


def get_answer(query, valid_response, GPTllm):

    # generate LLM prompt
    return 'from get_answer'
    # prompt = generate_prompt_series(query=query,
    #                                 results=valid_response)

    # return GPTllm.get_chat_completion(prompt=prompt,
    #                                system_message='answer this question based on the podcast material',
    #                                temperature=0,
    #                                max_tokens=500,
    #                                stream=False,
    #                                show_response=False)

# def reword_query(query, guest, model_name='llama2-13b-chat', response_processing=True):
#     """ Asks LLM to rewrite the query when the guest name is missing.

#     Args:
#         query (str): user query
#         guest (str): guest name
#         model_name (str, optional): name of a LLM model to be used
#     """
    
#     # tags = {'llama2-13b-chat': {'start': '<s>', 'end': '</s>', 'instruction': '[INST]', 'system': '[SYS]'},
#     #         'gpt-3.5-turbo-0613': {'start': '<|startoftext|>', 'end': '', 'instruction': "```", 'system': ```}}
    
#     prompt_fields = {
#         "you_are":f"You are an expert in linguistics and semantics, analyzing the question asked by a user to a vector search system, \
#                     and making sure that the question is well formulated and understandable by any average reader.",

#         "your_task":f"Your task is to detect if the name of the guest ({guest}) is mentioned in the question '{query}', \
#                     If that is not the case, rewrite the question using the guest name, \
#                     without changing the meaning of the question. \
#                     Most of the time, the user will have used a pronoun to designate the guest, in which case, \
#                     simply replace the pronoun with the guest name. \
#                     If the guest name is already present in the question, return the original question as is.",

#         "final_instruction":f"Only regenerate the requested rewritten question or the original, WITHOUT ANY COMMENT OR REPHRASING. \
#                     Your answer must be as close as possible to the original question, \
#                     and exactly identical, word for word, if the user mentions the guest name, i.e. {guest}.",
                    
#         "question":f"{query}"
#     }

#     # prompt created by chatGPT :-) 
#     # and Llama still outputs the original question and precedes the answer with 'rewritten question' 
#     prompt_fields2 = {
#     "you_are": (
#         "You are an expert in linguistics and semantics. Your role is to analyze questions asked to a vector search system."
#     ),
#     "your_task": (
#         f"Detect if the guest's FULL name, {guest}, is mentioned in the user's question. "
#         "If not, rewrite the question by replacing pronouns or indirect references with the guest's name." \
#         "If yes, return the original question as is, without any change at all, not even punctuation,"
#         "except a question mark that you MUST add if it's missing."
#     ),
#     "question": (
#         f"Original question: '{query}'. "
#         "Rewrite this question to include the guest's FULL name if it's not already mentioned."
#         "Add a question mark if it's missing, nothing else."
#     ),
#     "final_instruction": (
#         "Create a rewritten question or keep the original question as is. "
#         "Do not include any labels, titles, or additional text before or after the question."
#         "The Only thing you can and MUST add is a question mark if it's missing."
#         "Return a json object, with the key 'original_question' for the original question, \
#         and 'rewritten_question' for the rewritten question \
#         and 'changed' being True if you changed the answer, otherwise False."
#     ),
#     }
    

#     if model_name == 'llama2-13b-chat':
#         # special tags are used:
#         # `<s>` - start prompt tag
#         # `[INST], [/INST]` - Opening and closing model instruction tags
#         # `<<<SYS>>>, <</SYS>>` - Opening and closing system prompt tags
#         llama_prompt = """
#         <s>[INST] <<SYS>> 
#         {you_are}
#         <</SYS>>
#         {your_task}\n

#         ```
#         \n\n
#         Question: {question}\n
#         {final_instruction} [/INST]

#         Answer:
#         """
#         prompt = llama_prompt.format(**prompt_fields2)
        
#         headers = {"Authorization": f"Bearer {hf_token}",
#                 "Content-Type": "application/json",}

#         json_body = {
#                 "inputs": prompt,
#                 "parameters": {"max_new_tokens":400, 
#                                "repetition_penalty": 1.0, 
#                                "temperature":0.01}
#         }
        
#         response = requests.request("POST", hf_endpoint, headers=headers, data=json.dumps(json_body))
#         response = json.loads(response.content.decode("utf-8")) 
#         # ^ will not process the badly formatted generated text, so we do it ourselves
        
#         if isinstance(response, dict) and 'error' in response:
#             print("Found error")
#             print(response)
#             # return {'error': response['error'], 'rewritten_question': query, 'changed': False, 'status': 'error'}
#             # I test this here otherwise it gets in col 2 or 1, which are too
#             # if reworded_query['status'] == 'error':
#             # st.write(f"Error in LLM response: 'error':{reworded_query['error']}")
#             # st.write("The LLM could not connect to the server. Please try again later.")
#             # st.stop()
#             return reword_query(query, guest, model_name='gpt-3.5-turbo-0125')
            
#         if response_processing:
#             if isinstance(response, list) and isinstance(response[0], dict) and 'generated_text' in response[0]:
#                 print("Found generated text")
#                 response0 = response[0]['generated_text']
#                 pattern = r'\"(\w+)\":\s*(\".*?\"|\w+)'

#                 matches = re.findall(pattern, response0)
#                 # let's build a dictionary
#                 result = {key: json.loads(value) if value.startswith("\"") else value for key, value in matches}
#                 return result | {'status': 'success'}
#             else:
#                 print("Found no answer")
#                 return reword_query(query, guest, model_name='gpt-3.5-turbo-0125')
#                 # return {'original_question': query, 'rewritten_question': query, 'changed': False, 'status': 'no properly formatted answer' }
#         else:
#             return response
#         # return response
#         # assert 'error' not in response, f"Error in LLM response: {response['error']}"
#         # assert 'generated_text' in response[0], f"Error in LLM response: {response}, no 'generated_text' field"
#         # # let's extract the rewritten question
#         # return response[0]['generated_text'] .split("Rewritten question: '")[-1][:-1]
    
#     else:
#         # we assume / force openai 
#         model_ids = ['gpt-3.5-turbo-0125', 'gpt-3.5-turbo-16k', 'gpt-3.5-turbo-0613']
#         if model_name not in model_ids:
#             model_name = model_ids[0]
#         GPTllm = GPT_Turbo(model=model_name, api_key=openai_api_key)
        
#         openai_prompt = """
#         {your_task} \n
#         {final_instruction} /n 
#         ```
#         \n\n
#         Question: {question}\n

#         Answer:
#         """
#         prompt = openai_prompt.format(**prompt_fields)

#         try:
#             # https://platform.openai.com/docs/guides/text-generation/chat-completions-api
#             resp = GPTllm.get_chat_completion(prompt=prompt,
#                                             system_message=prompt_fields['you_are'],
#                                             user_message = None, 
#                                             temperature=0.01,
#                                             max_tokens=1500, # it's a long question...
#                                             show_response=True,
#                                             stream=False)

#             if resp.choices[0].finish_reason == 'stop':
#                 if guest in resp.choices[0].message.content:
#                     new_question = resp.choices[0].message.content
#                 return {'rewritten_question': new_question,
#                         'changed': True, 'status': 'success'}
#             else:
#                 raise Exception("LLM did not stop")  # to go to the except block
#         except Exception:
#             return {'rewritten_question': query, 'changed': False, 'status': 'not success'}


if __name__ == '__main__':
    main()
    # streamlit run app.py --server.allowRunOnSave True