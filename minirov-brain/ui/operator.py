def display_llm_response(parsed_response: dict):
    print(f"\nAction:    {parsed_response['action']}")
    print(f"Speed:     {parsed_response['speed']}")
    print(f"Reasoning: {parsed_response['reasoning']}")
    if parsed_response['safety_note']:
        print(f"Safety:    {parsed_response['safety_note']}")