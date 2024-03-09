#TODO: speaker_embeddings -> speaker_embeddings_by_model
#TODO: write back speaker embeddings or get rid of this from database altogether because we can just
# always compute them lazily

#
# speech_brain_speaker_identification_service.py
#
# Uses SpeechBrain's spkrec-ecapa-voxceleb model to identify speakers from a database of enrolled
# speakers' voice samples.
#
# How It Works
# ------------
# - Model is used to compute an embedding vector (192 elements) of each enrolled speech sample. The
#   idea is to then compare this against captured conversations to identify known people in the 
#   transcript.
# - We rely on the transcription service's diarization, for now, to identify speakers. For each 
#   speaker in the transcript, we take a "representative sample" of audio, compute embeddings, and
#   then compare against the enrolled embeddings. 
# - We begin by sorting each speaker's utterances by length, with those nearest to an "ideal sample
#   length" (e.g., 10 seconds) first, and larger deviations from this last. This threshold has been
#   chosen somewhat arbitrarily but the reasoning is that we want samples that are not too short 
#   but also not too long (and therefore likely to contain other speakers due to diarization issues
#   or other noise).
# - We accumulate up to a maximum length (e.g., 30 seconds) for each speaker.
# - Compute embeddings for all samples accumulated, resulting in a list of embeddings for each 
#   speaker.
# - We score all M unknown speakers against the N enrolled speakers and produce an NxM matrix. Each
#   score is the mean of the cosine similarities between the enrolled sample and unknown speaker
#   samples.
# - Iteratively assign speakers by pairing up the highest-scoring matches.
#
# Notes
# -----
# - "speaker" refers to the speaker label string. In a fresh transcript, these are not associated 
#   with an enrolled speaker (person) yet and are e.g. "Speaker 0", "Speaker 1", etc.
# - "person" refers to an enrolled speaker, a person with a known name.
#
# Improvements
# ------------
# - Score each transcript line independently? This would require a lot of processing over the
#   current sampled approach.
# - When taking samples, trim the ends and focus on the middle of the utterance to avoid diarization
#   issues that usually occur at the beginnings and ends of utterances.
#
# TODO
# ----
# - How to ensure CUDA is used?
#

from __future__ import annotations
from collections import defaultdict
import logging
import math
from multiprocessing import Process
import os
import requests
import signal
import time
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import httpx
import numpy as np
from pydantic import BaseModel
from pydub import AudioSegment
from speechbrain.pretrained import EncoderClassifier
import torch
import uvicorn

from .abstract_speaker_identification_service import AbstractSpeakerIdentificationService
from ....core.config import SpeechBrainConfiguration
from ....models.schemas import Transcription, Conversation, Person, Utterance, VoiceSample


logger = logging.getLogger(__name__)

class JSONVoiceSample(BaseModel):
    filepath: str

    def create_from(voice_sample: VoiceSample) -> JSONVoiceSample:
        return JSONVoiceSample(filepath=voice_sample.filepath)

class JSONPerson(BaseModel):
    id: int
    voice_samples: List[JSONVoiceSample]

    def create_from(person: Person) -> JSONPerson:
       return JSONPerson(
            id=person.id,
            voice_samples=[ JSONVoiceSample.create_from(voice_sample=voice_sample) for voice_sample in person.voice_samples ]
        )

class JSONUtterance(BaseModel):
    start: float
    end: float
    speaker: str
    person: JSONPerson | None

    def create_from(utterance: Utterance) -> JSONUtterance:
        return JSONUtterance(
            start=utterance.start,
            end=utterance.end,
            speaker=utterance.speaker,
            person=JSONPerson.create_from(person=utterance.person) if utterance.person is not None else None
        )

    def start_millis(self) -> int:
        return int(self.start * 1000)

    def end_millis(self) -> int:
        return int(math.ceil(self.end * 1000))
    
    def duration(self) -> float:
        return self.end - self.start
    
    def duration_millis(self) -> int:
        return self.end_millis() - self.start_millis()

class JSONTranscription(BaseModel):
    utterances: List[JSONUtterance]

    def create_from(transcription: Transcription):
        return JSONTranscription(utterances=[ JSONUtterance.create_from(utterance=utterance) for utterance in transcription.utterances ])

class SpeakerIdentificationRequest(BaseModel):
    transcript: JSONTranscription
    conversation_filepath: str
    persons: List[JSONPerson]

    def create_from(transcript: Transcription, conversation: Conversation, persons: List[Person]) -> SpeakerIdentificationRequest:
        return SpeakerIdentificationRequest(
            transcript=JSONTranscription.create_from(transcription=transcript),
            conversation_filepath=conversation.capture_segment_file.filepath,
            persons=[ JSONPerson.create_from(person=person) for person in persons ]
        )

class SpeakerIdentificationResponse(BaseModel):
    transcript: JSONTranscription

class SpeechBrainSpeakerIdentificationService(AbstractSpeakerIdentificationService):
    def __init__(self, config: SpeechBrainConfiguration):
        self._config = config
        self._http_client = httpx.AsyncClient(timeout=None) 

        # Start subprocess to run server
        process_args = (config,)
        self._process = Process(target=SpeechBrainSpeakerIdentificationService._run, args=process_args)
        self._process.start()

    def __del__(self):
        # This nasty trick c/o: https://benjoe.medium.com/programmatically-shutdown-uvicorn-server-running-fastapi-application-2038ade9436d
        requests.get(f"http://{self._config.host}:{self._config.port}/terminate")

    async def identify_speakers(self, transcript: Transcription, conversation: Conversation, persons: List[Person]) -> Transcription:
        # Send request to server and get response
        json_transcript = None
        try:
            client = httpx.AsyncClient(timeout=None)
            url = f"http://{self._config.host}:{self._config.port}/identify_speakers"
            logger.info(f"Sending request to local SpeechBrain speaker identification server at {url}...")
            request = SpeakerIdentificationRequest.create_from(transcript=transcript, conversation=conversation, persons=persons).model_dump()
            response = await client.post(url, json=request)
            response.raise_for_status()
            response_string = response.text
            logger.info(f"Received response from local SpeechBrain speaker identification server: {response_string}")
            json_transcript = SpeakerIdentificationResponse.model_validate_json(response_string).transcript
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while requesting {url}: {e}")
        
        # Label the transcript. The JSON version of the transcript should match the real one 1:1. If
        # we wanted to be really pedantic, we could preserve the detabase ID for each utterance and
        # verify.
        if json_transcript is not None:
            assert len(json_transcript.utterances) == len(transcript.utterances)
            person_by_id: Dict[int,Person] = { person.id: person for person in persons }
            for i in range(len(json_transcript.utterances)):
                json_person = json_transcript.utterances[i].person
                if json_person is not None:
                    transcript.utterances[i].person = person_by_id[json_person.id]
                    transcript.utterances[i].person_id = json_person.id

        return transcript

    def _run(config: SpeechBrainConfiguration):
        server = SpeechBrainSpeakerIdentificationServer(config=config)
        server.run()


class SpeechBrainSpeakerIdentificationServer:
    def __init__(self, config: SpeechBrainConfiguration):
        self._config = config
        self._classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
        self._embeddings_by_enrolled_person_id: Dict[int, torch.Tensor] = {}
        self._cos_similarity = torch.nn.CosineSimilarity(dim=-1, eps=1e-6)

        # Setup server and routes
        self._app = FastAPI()

        @self._app.post("/identify_speakers", response_model=SpeakerIdentificationResponse)
        async def api_identify_speakers(request: SpeakerIdentificationRequest):
            try:
                transcript = await self._identify_speakers(
                    transcript=request.transcript,
                    conversation_filepath=request.conversation_filepath,
                    persons=request.persons
                )
                return SpeakerIdentificationResponse(transcript=transcript)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self._app.get("/terminate")
        async def api_terminate():
            logger.info("Terminating SpeechBrain speaker identification process")
            os.kill(os.getpid(), signal.SIGTERM)
            return JSONResponse(content={"success": True}, status_code=200)
        
    def run(self):
        uvicorn.run(self._app, host=self._config.host, port=self._config.port, log_level="info")

    async def _identify_speakers(self, transcript: JSONTranscription, conversation_filepath: str, persons: List[JSONPerson]) -> JSONTranscription:
        # Lazily update enrolled speaker embeddings, because we may encounter new enrolled speakers
        # at any time
        self._update_enrolled_speaker_embeddings(persons=persons)

        # Map of person id -> person
        person_by_id = { person.id: person for person in persons }

        # Compute embeddings for each speaker in the given transcript (all of which are unknown) and
        # identify them by comparing against the enrolled speaker embeddings
        t_start = time.perf_counter()
        embeddings_by_speaker = self._compute_each_speaker_embeddings_from_conversation(transcript=transcript, conversation_filepath=conversation_filepath)
        identified_person_id_by_speaker = self._identify_speakers_from_embeddings(
            embeddings_by_unknown_speaker=embeddings_by_speaker,
            embeddings_by_enrolled_person_id=self._embeddings_by_enrolled_person_id
        )
        t_end = time.perf_counter()
        logger.info(f"Speaker identification took {(t_end - t_start):1.2f} sec")

        # Label the transcript
        for utterance in transcript.utterances:
            person_id = identified_person_id_by_speaker.get(utterance.speaker)
            if person_id is not None:
                utterance.person = person_by_id[person_id]
        return transcript
    
    def _update_enrolled_speaker_embeddings(self, persons: List[JSONPerson]):
        for person in persons:
            if person.id not in self._embeddings_by_enrolled_person_id:
                self._embeddings_by_enrolled_person_id[person.id] = self._compute_embeddings_for_enrolled_speaker(person=person)
    
    def _compute_embeddings_for_enrolled_speaker(self, person: JSONPerson) -> torch.Tensor:
        audio = AudioSegment.from_file(file=person.voice_samples[0].filepath).set_channels(1).set_frame_rate(16000)
        return self._compute_embeddings(audio=audio)
    
    def _compute_embeddings(self, audio: AudioSegment) -> torch.Tensor:
        assert audio.channels == 1
        assert audio.frame_rate == 16000
        samples = audio.get_array_of_samples()
        wave = torch.tensor(samples, dtype=torch.float32)
        data = wave.unsqueeze(0)
        embeddings = self._classifier.encode_batch(data)    # shape: [1,1,192]
        return embeddings.squeeze()                         # shape: [192,]

    def _compute_each_speaker_embeddings_from_conversation(self, transcript: JSONTranscription, conversation_filepath: str) -> Dict[int, List[torch.Tensor]]:
        """
        For each speaker in a conversation transcript, computes a number of embeddings from
        various utterances attributed to that speaker.
        """

        # Load conversation audio
        audio = AudioSegment.from_file(conversation_filepath)

        # How much total audio for each speaker to accumulate?
        max_sample_millis = 30 * 1000

        # What is the ideal sample size? We want the samples that are nearest to this size. Samples
        # that are individually *too long* are likely to contain lots of silence or background noise
        # (has been observed that Deepgram can generate very long duration paragraphs), or even two
        # speakers, and we actually want to avoid those and sample segments that are likely to be 
        # just one person speaking.
        ideal_sample_millis = 10 * 1000

        # Collect utterances by speaker
        utterances_by_speaker = defaultdict(list)     # speaker (str) -> List[Utterance]
        for utterance in transcript.utterances:
            utterances_by_speaker[utterance.speaker].append(utterance)
        
        # Prepare output map, guaranteeing that every speaker has a key in map and at least an empty
        # array of embeddings
        embeddings_by_speaker = { speaker: [] for speaker in utterances_by_speaker.keys() }

        # Compute embeddings for each speaker, one per utterance sampled
        for speaker, utterances in utterances_by_speaker.items():
            # Sort ascending by difference from ideal length
            utterances.sort(key=lambda utterance: abs(utterance.duration_millis() - ideal_sample_millis))

            # Accumulate up to max_sample_seconds and compute embeddings for each
            total_millis = 0
            for utterance in utterances:
                total_millis += utterance.duration_millis()
                excess_millis = total_millis - max_sample_millis

                # Indices to slice audio from, trimming endpoint of last sample to remove any excess
                # beyond what we want to accumulate
                start_millis = utterance.start_millis()
                end_millis = max(start_millis, utterance.end_millis() - excess_millis)

                # Slice and embed
                if end_millis > start_millis:
                    embeddings = self._compute_embeddings(audio=audio[start_millis:end_millis])
                    if not embeddings.isnan().any():
                        embeddings_by_speaker[speaker].append(embeddings)

                # Stop condition
                if total_millis >= max_sample_millis:
                    break
            
            # Validate whether any embeddings were successfully computed for this speaker
            if len(embeddings_by_speaker[speaker]) == 0:
                logger.warning(f"Failed to compute embeddings for any of the {len(utterances)} clips for Speaker {speaker}")
            logger.info(f"Speaker {speaker}: {len(embeddings_by_speaker[speaker])} embeddings")
        
        return embeddings_by_speaker

    def _identify_speakers_from_embeddings(self, embeddings_by_unknown_speaker: Dict[int, List[torch.Tensor]], embeddings_by_enrolled_person_id: Dict[int, torch.Tensor]) -> Dict[int, str]:
        score_threshold = self._config.threshold

        # NxM matrix of mean scores, N=number enrolled speakers, M=number of unknown speakers
        unknown_speakers = list(embeddings_by_unknown_speaker.keys())
        enrolled_person_ids = list(embeddings_by_enrolled_person_id.keys())
        n = len(enrolled_person_ids)
        m = len(unknown_speakers)
        mean_scores = np.full(shape=(n,m), fill_value=-1, dtype=np.float32)
    
        # Score each enrolled speaker against each unknown speaker
        for ni in range(n):
            for mi in range(m):
                # Score is the mean similarity between enrolled speaker Ni's embeddings and all
                # embeddings provided for unknown speaker Mi
                unknown_speaker_idx = unknown_speakers[mi]
                enrolled_person_id = enrolled_person_ids[ni]
                unknown_embeddings = embeddings_by_unknown_speaker[unknown_speaker_idx]
                if len(unknown_embeddings) <= 0:
                    # This can happen in pathological cases; we simply can't score it
                    continue
                enrolled_embeddings = embeddings_by_enrolled_person_id[enrolled_person_id]
                unknown_embeddings_tensor = torch.stack(unknown_embeddings)                     # [K,Q], K=number of embeddings, Q=embedding length
                scores = self._cos_similarity(unknown_embeddings_tensor, enrolled_embeddings)   # [K,]
                mean_score = torch.mean(scores)
                mean_scores[ni,mi] = -1 if mean_score < score_threshold else mean_score         # kill score if it is below threshold

        # Match enrolled and unknown speakers. An argmax is insufficient because e.g. a single 
        # enrolled speaker may be the best choice for multiple unknown speakers. Instead, we want to
        # match the highest scoring pairs, and do so by iteratively taking the max and then wiping
        # out the speakers it corresponds to. That is, if an unknown speaker scores above the
        # threshold against *two* enrolled speakers, we match it with the highest score. It is
        # theoretically possible (though highly improbable) to have ties, which is why we return
        # enrolled speakers indexed by speaker (i.e., enrolled name can appear as a value more than
        # than once).
        enrolled_person_id_by_speaker = {}
        for _ in range(n):
            max_score_idx = np.unravel_index(np.argmax(mean_scores), shape=mean_scores.shape)   # (Ni,Mi)
            if mean_scores[max_score_idx] <= -1:
                break   # nothing more to find here
            enrolled_person_id = enrolled_person_ids[max_score_idx[0]]
            speaker = unknown_speakers[max_score_idx[1]]
            enrolled_person_id_by_speaker[speaker] = enrolled_person_id
            mean_scores[max_score_idx[0],:] = -1
            mean_scores[:,max_score_idx[0]] = -1
        
        return enrolled_person_id_by_speaker