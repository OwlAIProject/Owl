from ..core.config import Configuration

def suggest_links_system_message(config: Configuration) -> str:
    return f"""
You are an world's most advanced AI assistant. You are given the transcript of an interaction. One
of the participants is your client. Their name is {config.user.name}. Your task is to generate a rich search query based on the summary of the interaction. You want to optimize the search query to get maximally interesting relevant link for {config.user.name}.  IMPORTANT: Try and make your search query about a single subject that is most relevant to the interaction. Make it as specific as possible and only pick one subject. Don't include {config.user.name}'s name in just output the query and nothing else. VERY IMPORTANT: You must just output the search engine query without any prefix and nothing else!""".replace("\n", " ")