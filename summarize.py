# https://towardsdatascience.com/summarize-podcast-transcripts-and-long-texts-better-with-nlp-and-ai-e04c89d3b2cb?gi=f7aa54cb54c3
# https://github.com/thamsuppp/llm_summary_medium/blob/master/summarizing_llm.ipynb
# https://towardsdatascience.com/louvain-algorithm-93fde589f58c

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
        chunk = sentences[i : i + length]
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
    prompt = f"""
Given the following conversation transcript chunk, produce a summary in the following format:

TITLE={{informative title}}
SUMMARY=A short summary (1 to 3 sentences), making sure to preserve all proper nouns and named entities.
ENTITIES=A list of named entities mentioned (uniquely identifiable proper nouns), each in format: {{entity}}: {{why it was mentioned}}

Transcript:

{chunk}
"""
    # Get summary from LLM
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "user",
                "content": prompt
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

async def embed_text(client: openai.AsyncOpenAI, text: ChunkSummary) -> np.ndarray:
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
        prompt = f"Write an informative title summarizing the following set of titles and make sure the new title captures as much information as possible. Output only the title, no quotes:\n{titles}"
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
        prompt = f"Write a concise summary of approximately {num_sentences} sentences, capturing as much information as possible, of the following text:\n{summaries}"
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

async def main():
    transcript = load_transcript(filepath="captures/20240222/apple_watch/20240222-174631.547_da79653060da41f184eb2aa3c1008789/20240222-175257.181_75f102ded1ab11ee9aeaa4b1c10ba08a_conversation.json")
    chunks = split_into_chunks(sentences=transcript, length=10, overlap=2)

    client = openai.AsyncOpenAI()
    clean_chunks = await clean_up_chunks(client=client, chunks=chunks)
    chunk_summaries = await summarize_chunks(client=client, chunks=clean_chunks)
    for i in range(len(chunk_summaries)):
        print(f"Summary {i}:")
        print(f"  Title   : {chunk_summaries[i].title}")
        print(f"  Summary : {chunk_summaries[i].summary}")
        print(f"  Entities: {chunk_summaries[i].entities}")
        print("")
        print("  Transcript:")
        for sentence in chunks[i]:
            print(f"    {sentence}")
        print("")

    # To embed chunks and find similarity between them, we can embed either the titles or summaries
    # themselves. Titles seem to work better.
    chunk_embeddings = await embed_chunk_titles(client=client, summaries=chunk_summaries)
    chunk_similarity_matrix = calculate_similarities(embeddings=chunk_embeddings)

    # Draw a heatmap with the summary_similarity_matrix
    plt.figure()
    # Color scheme blues
    plt.imshow(chunk_similarity_matrix, cmap = 'Blues')
    plt.show()

    # Set num_topics to be 1/4 of the number of chunks, or 8, which ever is smaller
    num_topics = min(int(len(chunks) / 4), 8)
    topics = find_topics_louvain(chunk_similarity_matrix, num_topics = num_topics, bonus_constant = 0.2)
    print(topics)
    topic_titles = await summarize_chunk_titles_into_topic_titles(client=client, chunk_summaries=chunk_summaries, topics=topics)
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


if __name__ == "__main__":
    asyncio.run(main())
    

