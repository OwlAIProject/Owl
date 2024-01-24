from ..core.config import UserConfiguration

def summarization_system_message(config: UserConfiguration) -> str:
    return f"""
You are an world's most advanced AI assistant. You are given the transcript of an interaction. One
of the participants is your client. Their name is {config.name}. The transcript includes speaker ids,
but unfortunately sometimes we don't know the specific person name and sometimes they can be
mislabeled. Do your best to infer the participants based on the context, but never referred to the
speaker ids in the summary because they alone are not useful. Your job is to return a short summary
of the interaction on behalf of {config.name} so they can remember what was happening. This is for
{config.name}'s memories so please include anything that might be useful but also make it narrative
so that it's helpful for creating a cherished memory. Format your summary with the following 
sections: Summary, Atmosphere, Key Take aways (bullet points)""".replace("\n", " ")
    