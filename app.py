import gradio as gr
import ollama
import re
import os
import datetime

# Presets
character_presets = {
    "Fantasy": ["Knight", "Wizard", "Thief", "Elf", "Ranger"],
    "Sci-Fi": ["Hacker", "Space Pilot", "Android", "Alien"],
    "Horror": ["Survivor", "Investigator", "Doctor", "Exorcist"],
    "Mystery": ["Detective", "Journalist", "Lawyer", "Spy"],
    "Adventure": ["Explorer", "Mercenary", "Historian", "Pirate"],
    "Superhero": ["Vigilante", "Speedster", "Telepath", "Tech-genius"],
    "Post-Apocalyptic": ["Scavenger", "Medic", "Lone Survivor", "Mutant"],
    "Romance": ["Writer", "Artist", "Traveler", "Barista"],
    "Historical Fiction": ["Soldier", "Peasant", "Scholar", "Noble"],
    "Comedy": ["Clown", "Prankster", "Office Worker", "Unlucky Hero"]
}

# State
state = {
    "genre": None,
    "prompt": None,
    "character": None,
    "max_words": 500,
    "steps": 3,
    "history": [],
    "full_story": [],
    "current_step": 0
}

os.makedirs("story_logs", exist_ok=True)

def select_genre(genre):
    state["genre"] = genre
    return gr.update(visible=True), gr.update(visible=True)

def analyze_prompt(prompt):
    state["prompt"] = prompt
    match = re.search(r"\b(a|an|the)\s+([\w\s]+?)(?:\s+(?:in|who|that|with|,|\.|$))", prompt, re.IGNORECASE)
    if match:
        char = match.group(2).strip()
        state["character"] = char
        return f"Use the character: **{char}**?", gr.update(visible=True), gr.update(visible=False)
    else:
        return (
            "Choose your character:",
            gr.update(visible=False),
            gr.update(choices=character_presets[state["genre"]], visible=True)
        )

def confirm_character(confirm):
    return gr.update(visible=True) if confirm == "Yes" else gr.update(visible=False)

def set_character(char):
    state["character"] = char
    return gr.update(visible=True)

def set_words(words):
    state["max_words"] = int(words)
    return gr.update(visible=True)

def set_steps(steps):
    state["steps"] = int(steps)
    return gr.update(visible=True)

def call_model(system_prompt, user_prompt):
    return ollama.chat(
        model='mistral',
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )['message']['content']

def start_story():
    state["history"] = []
    state["full_story"] = []
    state["current_step"] = 1
    return continue_story("")

def continue_story(user_choice):
    if user_choice:
        state["history"].append(f"User chose: {user_choice}")

    prompt = f"""Genre: {state['genre']}
Character: {state['character']}
Prompt: {state['prompt']}
Story so far:
{''.join(state['full_story'])}
{' '.join(state['history'])}

Write the next part of the story (step {state['current_step']}/{state['steps']}), total approx {state['max_words']} words.
End with 3 choices.
Format:
Story: <story>
Choices:
1. ...
2. ...
3. ...
"""

    system_prompt = "You are a branching story AI. Keep story immersive, creative, and give 3 plausible choices at each step. Ensure proper story ending at final step."

    output = call_model(system_prompt, prompt)

    if "Choices:" in output:
        story_text = output.split("Choices:")[0].replace("Story:", "").strip()
        choices = re.findall(r"\d+\.\s*(.+)", output.split("Choices:")[1])
    else:
        story_text = output.strip()
        choices = ["Continue..."]

    state["full_story"].append(f"\nStep {state['current_step']}:\n{story_text}")
    state["current_step"] += 1
    done = state["current_step"] > state["steps"]

    if done:
        # Add a proper ending
        final_prompt = f"""Genre: {state['genre']}
Character: {state['character']}
Prompt: {state['prompt']}
Story so far:
{''.join(state['full_story'])}
{' '.join(state['history'])}

Write a satisfying and conclusive ending to the story. No choices. Just end the story meaningfully.
"""
        ending_output = call_model(system_prompt, final_prompt)
        state["full_story"].append(f"\nFinal Ending:\n{ending_output.strip()}")
        full_story = "".join(state["full_story"])

        return (
            full_story,                     # story_box
            full_story,                     # full_story_output
            gr.update(visible=False),       # choice_box
            gr.update(visible=False),       # next_btn
            gr.update(visible=True),        # save_btn
            gr.update(visible=False)        # save_msg
        )

    full_story = "".join(state["full_story"])

    return (
        story_text,                         # story_box shows just current step
        full_story,                         # full_story_output
        gr.update(choices=choices, visible=True),  # choice_box
        gr.update(visible=True),                    # next_btn
        gr.update(visible=False),                   # save_btn
        gr.update(visible=False)                    # save_msg
    )


##################################################################
  

def save_story():
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"story_logs/story_{now}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("".join(state["full_story"]))
    return f" Story saved to `{filename}`."

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## Interactive Story Generator (Ollama Mistral)")

    genre = gr.Radio(list(character_presets.keys()), label="Choose a Genre")
    prompt = gr.Textbox(label="Enter your story prompt", visible=False)
    analyze_btn = gr.Button("Submit Prompt", visible=False)

    char_msg = gr.Markdown(visible=False)
    confirm_char = gr.Radio(["Yes", "No"], label="Use detected character?", visible=False)
    char_select = gr.Radio([], label="Choose Character", visible=False)

    word_slider = gr.Slider(minimum=100, maximum=1000, step=50, value=500, label="Total words (approx.)", visible=False)
    step_slider = gr.Slider(minimum=1, maximum=10, step=1, value=3, label="How many steps?", visible=False)

    start_btn = gr.Button("Start Story", visible=False)
    loading_msg = gr.Markdown("Generating story... Please wait.", visible=False)

    current_story = gr.Textbox(label="Current Story Part", lines=10, visible=False, interactive=False)
    full_story_output = gr.Textbox(label=" Story So Far", lines=15, visible=True, interactive=False)

    choice_box = gr.Radio([], label="Your Choice", visible=False)
    next_btn = gr.Button("Next", visible=False)

    save_btn = gr.Button("Save Story", visible=False)
    save_msg = gr.Markdown(visible=False)

    # Events
    genre.change(select_genre, genre, [prompt, analyze_btn])
    analyze_btn.click(analyze_prompt, prompt, [char_msg, confirm_char, char_select])
    confirm_char.change(confirm_character, confirm_char, word_slider)
    char_select.change(set_character, char_select, word_slider)
    word_slider.change(set_words, word_slider, step_slider)
    step_slider.change(set_steps, step_slider, start_btn)

    start_btn.click(lambda: gr.update(visible=True), outputs=loading_msg)
    start_btn.click(start_story, outputs=[current_story, full_story_output, choice_box, next_btn, save_btn, loading_msg])
    start_btn.click(lambda: gr.update(visible=False), outputs=loading_msg)

    next_btn.click(lambda: gr.update(visible=True), outputs=loading_msg)
    next_btn.click(continue_story, inputs=choice_box, outputs=[current_story, full_story_output, choice_box, next_btn, save_btn, loading_msg])
    next_btn.click(lambda: gr.update(visible=False), outputs=loading_msg)

    save_btn.click(save_story, outputs=[save_msg])
    save_btn.click(lambda: gr.update(visible=True), outputs=[save_msg])

demo.launch()
