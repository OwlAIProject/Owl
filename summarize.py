#
# summarize.py
#
# Summarization method inspired by:
#   https://towardsdatascience.com/summarize-podcast-transcripts-and-long-texts-better-with-nlp-and-ai-e04c89d3b2cb?gi=f7aa54cb54c3
#   https://github.com/thamsuppp/llm_summary_medium/blob/master/summarizing_llm.ipynb
#   https://towardsdatascience.com/louvain-algorithm-93fde589f58c
#
# Essentially, the procedure is:
#   - Split transcript into overlapping chunks of N sentences.
#   - Summarize each chunk into a "title" and "summary".
#   - Embed either each chunk summary or chunk title.
#   - Run a clustering algorithm on embeddings to detect "topics". In my tests, embedding the chunk
#     titles yields much better results.
#   - The clustering algorithm produces T topics, each represented as an array of M titles. These
#     titles must be reduced (summarized) into single topic titles. The same process is performed 
#     for the chunk summaries associated with each of the individual titles. E.g., if a topic was
#     found consisting of 4 chunks, those 4 chunk summaries are concatenated and summarized into a
#     single "topical summary" in a process that is analogous to the topic title summarization.
#   - At last, the final summary is produced by taking all of the topic summaries, concatenating
#     them, and running a summarization step. There is however an option to use the raw transcript
#     chunks here rather than their summaries.
#
# Conclusions:
#   - This produces an inferior summarization but the topic clustering is interesting and
#     potentially useful.
#
# Follow-ups:
#   - Perform NER on topic-clustered transcript lines? Can we identify conversation objectives and
#     what would be the most relevant entities here? Does NER simply work better on smaller chunks
#    (perhaps even initial chunk level)?
#

import asyncio
from dataclasses import dataclass
import json
from typing import List

import numpy as np
import openai
import matplotlib.pyplot as plt
import networkx
from networkx.algorithms import community


####################################################################################################
# Transcript Loading and Chunking
####################################################################################################

def load_transcript(filepath: str) -> List[str]:
    with open(filepath, "r") as fp: 
        convo = json.load(fp)

    # Get the non-realtime transcript
    transcript = [ transcript for transcript in convo["transcriptions"] if transcript["realtime"] == False ][0]

    # Return utterances as an array of strings, with speakers labeled
    lines = []
    for utterance in transcript["utterances"]:
        lines.append(f"Speaker {utterance['speaker']}: {utterance['text']}")
    return lines

def split_into_chunks(sentences: List[str], length: int, overlap: int) -> List[str]:
    assert length > 0 and length > overlap
    chunks = []
    stride = length - overlap
    for i in range(0, len(sentences), stride):
        chunk = "\n".join(sentences[i : i + length])
        chunks.append(chunk)
    return chunks


####################################################################################################
# Transcript Chunk Clean-up
####################################################################################################

async def clean_up_one_chunk(client: openai.AsyncOpenAI, chunk: str) -> str:
    prompt = f"""
Given the following messy and potentially inaccurate conversation transcript, produce a cleaned up, coherent version of what each speaker said, eliminating all filler words and making each sentence concise:

{chunk}
"""
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response.choices[0].message.content

async def clean_up_chunks(client: openai.AsyncOpenAI, chunks: List[str], max_parallel_llm_calls: int = 10) -> List[str]:
    max_parallel_llm_calls = max_parallel_llm_calls if max_parallel_llm_calls > 0 else len(chunks)
    summaries = []
    for i in range(0, len(chunks), max_parallel_llm_calls):
        num_chunks_to_process = min(max_parallel_llm_calls, len(chunks) - i)
        coroutines = []
        for j in range(num_chunks_to_process):
            coroutines.append(clean_up_one_chunk(client=client, chunk=chunks[i + j]))
        summaries += await asyncio.gather(*coroutines)
    return summaries


####################################################################################################
# Transcript Chunk Summarization
####################################################################################################

@dataclass
class ChunkSummary:
    title: str
    summary: str
    entities: str

async def summarize_one_chunk(client: openai.AsyncOpenAI, chunk: str) -> ChunkSummary:
    system_message = f"""
You are a smart AI assistant and are given transcript segments to analyze by the user. Speaker IDs are provided but may
be mislabeled. Do NOT refer to speaker IDs in your summary. Produce a summary with the following format:

TITLE={{informative title concisely describing the topic of conversation}}
SUMMARY={{An informative summary (100-200 words). Rephrase the conversation in an essay form addressed
to a third party not present at the conversation. Preserve all information, proper nouns, named entities.}}
"""
#ENTITIES=A list of named entities mentioned (uniquely identifiable proper nouns), each in format: {{entity}}: {{why it was mentioned}}

    # Get summary from LLM
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": chunk
            }
        ]
    )
    raw_text = response.choices[0].message.content

    # Parse out each component
    title = ""
    summary = ""
    entities = ""
    for line in raw_text.splitlines():
        parts = line.split("=")
        if len(parts) >= 2:
            key = parts[0].lower()
            value = "=".join(parts[1:])
            if key == "title":
                title = value
            elif key == "summary":
                summary = value
            elif key == "entities":
                entities = value
    return ChunkSummary(title=title, summary=summary, entities=entities)

async def summarize_chunks(client: openai.AsyncOpenAI, chunks: List[str], max_parallel_llm_calls: int = 10) -> List[ChunkSummary]:
    max_parallel_llm_calls = max_parallel_llm_calls if max_parallel_llm_calls > 0 else len(chunks)
    summaries = []
    for i in range(0, len(chunks), max_parallel_llm_calls):
        num_chunks_to_process = min(max_parallel_llm_calls, len(chunks) - i)
        coroutines = []
        for j in range(num_chunks_to_process):
            coroutines.append(summarize_one_chunk(client=client, chunk=chunks[i + j]))
        summaries += await asyncio.gather(*coroutines)
    return summaries


####################################################################################################
# Embedding
####################################################################################################

async def embed_text(client: openai.AsyncOpenAI, text: str) -> np.ndarray:
   text = text.replace("\n", " ") 
   response = await client.embeddings.create(input = [ text ], model="text-embedding-3-small")
   return np.array(response.data[0].embedding)

async def embed_chunk_titles(client: openai.AsyncOpenAI, summaries: List[ChunkSummary], max_parallel_embed_calls: int = 10) -> List[np.ndarray]:
    max_parallel_embed_calls = max_parallel_embed_calls if max_parallel_embed_calls > 0 else len(summaries)
    embeddings = []
    for i in range(0, len(summaries), max_parallel_embed_calls):
        num_chunks_to_process = min(max_parallel_embed_calls, len(summaries) - i)
        coroutines = []
        for j in range(num_chunks_to_process):
            coroutines.append(embed_text(client=client, text=summaries[i + j].title))
        embeddings += await asyncio.gather(*coroutines)
    return embeddings

async def embed_chunk_summaries(client: openai.AsyncOpenAI, summaries: List[ChunkSummary], max_parallel_embed_calls: int = 10) -> List[np.ndarray]:
    max_parallel_embed_calls = max_parallel_embed_calls if max_parallel_embed_calls > 0 else len(summaries)
    embeddings = []
    for i in range(0, len(summaries), max_parallel_embed_calls):
        num_chunks_to_process = min(max_parallel_embed_calls, len(summaries) - i)
        coroutines = []
        for j in range(num_chunks_to_process):
            coroutines.append(embed_text(client=client, text=summaries[i + j].summary))
        embeddings += await asyncio.gather(*coroutines)
    return embeddings

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def calculate_similarities(embeddings: List[np.ndarray]) -> np.ndarray:
    num_embeddings = len(embeddings)
    similarity_matrix = np.zeros((num_embeddings, num_embeddings))
    for row in range(num_embeddings):
        for col in range(row, num_embeddings):
            similarity = cosine_similarity(v1=embeddings[row], v2=embeddings[col])
            similarity_matrix[row, col] = similarity
            similarity_matrix[col, row] = similarity
    return similarity_matrix


####################################################################################################
# Topic Clustering: Louvain Community Detection Algorithm
####################################################################################################

@dataclass
class TopicClusteringResult:
   chunk_idxs_with_same_topic: List[List[int]]  # each topic found, as a list of chunks having that topic
   topic_idx_each_chunk: List[int]              # for each chunk, the index of its topic in chunk_idxs_with_same_topic

def find_topics_louvain(title_similarity, num_topics = 8, bonus_constant = 0.25, min_size = 3):
  proximity_bonus_arr = np.zeros_like(title_similarity)
  for row in range(proximity_bonus_arr.shape[0]):
    for col in range(proximity_bonus_arr.shape[1]):
      if row == col:
        proximity_bonus_arr[row, col] = 0
      else:
        proximity_bonus_arr[row, col] = 1/(abs(row-col)) * bonus_constant
        
  title_similarity += proximity_bonus_arr

  title_nx_graph = networkx.from_numpy_array(title_similarity)

  desired_num_topics = num_topics
  # Store the accepted partitionings
  topics_title_accepted = []

  resolution = 0.85
  resolution_step = 0.01
  iterations = 40

  # Find the resolution that gives the desired number of topics
  topics_title = []
  while len(topics_title) not in [desired_num_topics, desired_num_topics + 1, desired_num_topics + 2]:
    topics_title = community.louvain_communities(title_nx_graph, weight = 'weight', resolution = resolution)
    resolution += resolution_step
  topic_sizes = [len(c) for c in topics_title]
  sizes_sd = np.std(topic_sizes)
  modularity = community.modularity(title_nx_graph, topics_title, weight = 'weight', resolution = resolution)

  lowest_sd_iteration = 0
  # Set lowest sd to inf
  lowest_sd = float('inf')

  for i in range(iterations):
    topics_title = community.louvain_communities(title_nx_graph, weight = 'weight', resolution = resolution)
    modularity = community.modularity(title_nx_graph, topics_title, weight = 'weight', resolution = resolution)
    
    # Check SD
    topic_sizes = [len(c) for c in topics_title]
    sizes_sd = np.std(topic_sizes)
    
    topics_title_accepted.append(topics_title)
    
    if sizes_sd < lowest_sd and min(topic_sizes) >= min_size:
      lowest_sd_iteration = i
      lowest_sd = sizes_sd
      
  # Set the chosen partitioning to be the one with highest modularity
  topics_title = topics_title_accepted[lowest_sd_iteration]
  print(f'Best SD: {lowest_sd}, Best iteration: {lowest_sd_iteration}')
  
  topic_id_means = [sum(e)/len(e) for e in topics_title]
  # Arrange title_topics in order of topic_id_means
  topics_title = [list(c) for _, c in sorted(zip(topic_id_means, topics_title), key = lambda pair: pair[0])]
  # Create an array denoting which topic each chunk belongs to
  chunk_topics = [None] * title_similarity.shape[0]
  for i, c in enumerate(topics_title):
    for j in c:
      chunk_topics[j] = i
            
  return TopicClusteringResult(chunk_idxs_with_same_topic=topics_title, topic_idx_each_chunk=chunk_topics)


####################################################################################################
# Topic Summarization
#
# Create topic titles out of all chunk titles comprising each topic, and summarize topical chunks.
####################################################################################################

async def summarize_chunk_titles_into_topic_titles(client: openai.AsyncOpenAI, chunk_summaries: List[ChunkSummary], topics: TopicClusteringResult) -> List[str]:
    #TODO: could probably do these in parallel
    topic_titles = []
    for chunk_idxs in topics.chunk_idxs_with_same_topic:
        titles = "\n".join([ chunk_summaries[idx].title for idx in chunk_idxs ])
        prompt = f"Write an informative topic line summarizing the following set of topics and make sure the new topic captures as much information as possible. Output only the topic, no quotes:\n{titles}"
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        topic_titles.append(response.choices[0].message.content)
    return topic_titles

async def summarize_chunk_summaries_into_topical_summaries(client: openai.AsyncOpenAI, chunk_summaries: List[ChunkSummary], topics: TopicClusteringResult, num_sentences: int = 5) -> List[str]:
    topical_summaries = []
    for chunk_idxs in topics.chunk_idxs_with_same_topic:
        summaries = "\n".join([ chunk_summaries[idx].summary for idx in chunk_idxs ])
        prompt = f"Write a concise summary of approximately {num_sentences} sentences, capturing as much information as possible and preserving all proper nouns and named entities, of the following text:\n{summaries}"
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        topical_summaries.append(response.choices[0].message.content)
    return topical_summaries

# This version takes the raw (can be cleaned-up) transcript chunks rather than their summaries
async def summarize_transcript_chunks_into_topical_summaries(client: openai.AsyncOpenAI, chunks: List[str], topics: TopicClusteringResult, num_sentences: int = 5) -> List[str]:
    topical_summaries = []
    for chunk_idxs in topics.chunk_idxs_with_same_topic:
        transcript_lines = "\n".join([ chunks[idx] for idx in chunk_idxs ])
        prompt = f"""
You are a smart AI assistant and are given transcript segments to analyze by the user. Speaker IDs
are provided but may be mislabeled. Do NOT refer to speaker IDs in your summary. Produce a summary
approximately {num_sentences} long, preserving all proper nouns and named entities:

{transcript_lines}
"""
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        topical_summaries.append(response.choices[0].message.content)
    return topical_summaries


####################################################################################################
# Final Summarization
####################################################################################################

async def produce_single_summary_from_chunk_summaries(client: openai.AsyncOpenAI, topics: List[str], summaries: List[str]) -> str:
    assert len(topics) == len(summaries)
    num_summaries = len(topics)
    summaries = "\n".join([ f"TOPIC: {topics[i]}\SUMMARY: {summaries[i]}\n" for i in range(num_summaries) ])
    system_message = f"""
You are the world's smartest AI assistant and have been given a series of summaries, by topic, extracted from a conversation.
Your task is to produce a final recap of everything in the following format:

SUMMARY:
{{An essay re-stating the conversation, covering each topic in ~75 words, and preserving as much information as possible.
Incorporate all named entities and proper nouns from the input text. Make sure the summary flows
logically from topic to topic. Do not use filler phrases mentioning topic and conversation explicitly, focus on the content
of the conversation and try to re-state it to convey all the information it covered.}}

TAKEAWAYS:
{{Bullet-point list of key takeaways, action items, and things to follow up on.}}
"""
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": f"{summaries}"
            }
        ]
    )
    return response.choices[0].message.content


####################################################################################################
# Information Extraction
####################################################################################################

def aggregate_transcript_chunks_by_topic(chunks: List[str], topics: TopicClusteringResult) -> List[str]:
    # Take all chunks associated with a topic and arrange them like so:
    #
    #   <segment-1>
    #   Speaker 0: ...
    #   Speaker 1: ...
    #   ...
    #   </segment-1>
    #   <segment-2>
    #   Speaker 0: ...
    #   Speaker 1: ...
    #   ...
    #   </segment-2>
    #   ...
    # 
    # Hopefully the segment tags help GPT understand that these are disjointed segments.
    #
    transcript_chunks_each_topic = []
    for chunk_idxs in topics.chunk_idxs_with_same_topic:
        pieces = []
        for idx in chunk_idxs:
            pieces.append(f"<segment-{idx}>")
            pieces.append(chunks[idx])
            pieces.append(f"</segment-{idx}>")
        transcript_chunks_each_topic.append("\n".join(pieces))
    return transcript_chunks_each_topic

async def extract_from_each_topic(client: openai.AsyncOpenAI, transcript_chunks_each_topic: List[str], topic_titles: List[str]) -> List[str]:
    assert len(transcript_chunks_each_topic) == len(topic_titles)
#     system_message = """
# You are the world's smartest AI assistant. You help your user by listening in on conversations and 
# analyzing them for relevant information, recommendations, and insights. Your input is in the form of
# transcript lines, labeled by speaker ID, representing segments of conversation. The segments may have
# overlapping lines. All segments have a related topic or theme, which is also stated.

# For each input you are given, extract the specific named entities that appear to have been recommended by any
# speaker as something that should be investigated, looked into, or otherwise followed up on. Each 
# should appear on its own line with format:

# - {specific named entity}: {why it is important and what to do next with it}

# If no important entities exist, just emit "NONE". Omit non-specific entities; ONLY list specific ones.
# Omit generic concepts or categories. Omit entities which are unrelated or weakly related to the topic.
# """
    system_message = """
You are the world's smartest AI assistant. You help your user by listening in on conversations and 
analyzing them for relevant information, recommendations, and insights. Your input is in the form of
transcript lines, labeled by speaker ID, representing segments of conversation. The segments may have
overlapping lines. All segments have a related topic or theme, which is also stated.

When given a transcript, determine what each speaker is most interested in and what information they
most desire. Then, extract the specific named entities that appear to have been recommended to each
speaker as something that should be investigated, looked into, or otherwise followed up. For each
speaker, output in this format:

SPEAKER {n}
INTERESTS:
{what speaker is interested in and information they want}
USEFUL INFO:
{list of: - {specific named entity}: {why it is important and what to do next with it}}
"""
    outputs = []
    for i in range(len(transcript_chunks_each_topic)):
        transcript_chunks = transcript_chunks_each_topic[i]
        topic = topic_titles[i]

        response = await client.chat.completions.create(
            model="gpt-4-1106-preview",
#            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": f"<topic>{topic}</topic>\n{transcript_chunks}"
                }
            ]
        )
        outputs.append(response.choices[0].message.content)
    return outputs

        
####################################################################################################
# Main Program
####################################################################################################

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cleanup", action="store_true", help="Do not clean up transcript before processing")
    parser.add_argument("--topic-embedding", metavar="source", action="store", default="title", help="Embedding source for topic clustering ('title' (default) or 'summary')")
    parser.add_argument("--summarize-raw-transcript", action="store_true", help="For final summary, use the original raw transcript chunks rather than topic summaries")
    parser.add_argument("--plot", action="store_true", help="Plot figures")
    options = parser.parse_args()

    # Validate options
    assert options.topic_embedding in [ "title", "summary" ]

    # Load file and split into chunks
    filepath = "captures/20240222/apple_watch/20240222-174631.547_da79653060da41f184eb2aa3c1008789/20240222-175257.181_75f102ded1ab11ee9aeaa4b1c10ba08a_conversation.json"  # convo at Blue Bottle
    #filepath = "captures/20240206/apple_watch/20240206-090533.805_a0fe1f04ca9d11ee96b8a4b1c10ba08a/20240206-090830.671_815d306bcaa411ee8caea4b1c10ba08a_conversation.json"   # convo at doctor office
    transcript = load_transcript(filepath=filepath)
    chunks = split_into_chunks(sentences=transcript, length=10, overlap=2)

    # OpenAI client
    client = openai.AsyncOpenAI()

    # Optionally clean up chunks
    clean_chunks = chunks if options.no_cleanup else await clean_up_chunks(client=client, chunks=chunks)

    # Create chunk summaries (title and summary for each)
    chunk_summaries = await summarize_chunks(client=client, chunks=clean_chunks)
    for i in range(len(chunk_summaries)):
        print(f"Summary {i}:")
        print(f"  Title   : {chunk_summaries[i].title}")
        print(f"  Summary : {chunk_summaries[i].summary}")
        print(f"  Entities: {chunk_summaries[i].entities}")
        print("")
        print("  Transcript:")
        for sentence in chunks[i].splitlines():
            print(f"    {sentence}")
        print("")

    # To embed chunks and find similarity between them, we can embed either the titles or summaries
    # themselves. Titles seem to work better.
    if options.topic_embedding == "title":
        chunk_embeddings = await embed_chunk_titles(client=client, summaries=chunk_summaries)
    else:
        chunk_embeddings = await embed_chunk_summaries(client=client, summaries=chunk_summaries)
    chunk_similarity_matrix = calculate_similarities(embeddings=chunk_embeddings)

    # Set num_topics to be 1/4 of the number of chunks, or 8, which ever is smaller
    num_topics = min(int(len(chunks) / 4), 8)
    topics = find_topics_louvain(chunk_similarity_matrix, num_topics = num_topics, bonus_constant = 0.2)
    print(topics)

    # Arrays of topic titles and topic summaries
    topic_titles = await summarize_chunk_titles_into_topic_titles(client=client, chunk_summaries=chunk_summaries, topics=topics)
    if options.summarize_raw_transcript:
        topic_summaries = await summarize_transcript_chunks_into_topical_summaries(client=client, chunks=clean_chunks, topics=topics)
    else:
        topic_summaries = await summarize_chunk_summaries_into_topical_summaries(client=client, chunk_summaries=chunk_summaries, topics=topics)

    print("")
    print("--")
    for i in range(len(topics.chunk_idxs_with_same_topic)):
        print(f"Topic Title: {topic_titles[i]}")
        print("Topic Summary:")
        for line in topic_summaries[i].splitlines():
            print(f"  {line}")
        # print("Original Titles:")
        # chunk_idxs = topics.chunk_idxs_with_same_topic[i]
        # for j in range(len(chunk_idxs)):
        #     idx = chunk_idxs[j]
        #     print(f"  {chunk_summaries[idx].title}")
        print("")

    print("")
    print("--")

    # Tests
    # transcript_chunks_each_topic = aggregate_transcript_chunks_by_topic(chunks=clean_chunks, topics=topics)
    # y = await extract_from_each_topic(client=client, transcript_chunks_each_topic=transcript_chunks_each_topic, topic_titles=topic_titles)
    # for i in range(len(y)):
    #     print(f"Topic: {topic_titles[i]}")
    #     print("  \n".join(y[i].splitlines()))
    # return

    # Single summary
    final_summary = await produce_single_summary_from_chunk_summaries(client=client, topics=topic_titles, summaries=topic_summaries)
    print("Final Summary:")
    print(final_summary)

    # Plots
    if options.plot:
        # Draw a heatmap with the summary_similarity_matrix
        plt.figure()
        plt.imshow(chunk_similarity_matrix, cmap = 'Blues')
        plt.show()

        # Plot a heatmap of the topics array, showing how many topics and how they are distributed
        # throughout the chunks
        plt.figure(figsize = (10, 4))
        plt.imshow(np.array(topics.topic_idx_each_chunk).reshape(1, -1), cmap = 'tab20')
        # Draw vertical black lines for every 1 of the x-axis 
        for i in range(1, len(topics.topic_idx_each_chunk)):
            plt.axvline(x = i - 0.5, color = 'black', linewidth = 0.5)

if __name__ == "__main__":
    asyncio.run(main())
    

