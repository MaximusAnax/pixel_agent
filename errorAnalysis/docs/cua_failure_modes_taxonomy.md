The taxonomy of computer-use agent errors can be divided into **perception/grounding errors,** which involve the failure to accurately map instructions to visual UI elements, and **cognitive/planning errors,** which involve failures in high-level reasoning, intent understanding, and memory.

### Perception and Grounding Errors

These failures occur when an agent cannot correctly identify or interact with the physical properties of the interface.

* **Click Region Error**: The agent conceptually identifies the correct UI element but predicts imprecise or "wrong physical area" coordinates for the interaction 6, 7\.  
  * *Example*: An agent is instructed to "Click on 'Done' button" and identifies it in reasoning, but its output coordinates fall outside the button's actual boundary 7\.  
* **Visual Confusion (Primitive Reliance)**: The agent relies on superficial visual cues (shape, color, position) rather than functional semantics, mistaking one type of element for another 8, 9\.  
  * *Example*: An agent mistakes a light-colored button for a search box because both are white rectangles near the top of the screen 10, 11\.  
* **Text Matching Bias**: The agent clicks on visible text that matches a word in the instruction without verifying if that text is actually the interactive target 8, 12\.  
  * *Example*: When told to "Click on 'First Name' textbox," the agent clicks the "First Name" text label instead of the actual input field beneath it 12\.  
* **Resolution/Scale Brittleness**: A failure to adapt to changes in browser zoom or screen resolution, often because the model has memorized absolute pixel positions 13, 14\.  
  * *Example*: In a 70% browser zoom scenario, an agent clicks on the empty space where a button *used* to be at 100% scale, indicating it memorized a position rather than learning a functional target 14\.  
* **Fine-Grained Manipulation Failure**: A breakdown in precision when tasks require character-level cursor placement or the adjustment of compact components like sliders 5, 15\.  
  * *Example*: An agent fails to place the cursor precisely between the word "person" and the number "1" in a text field, which occupies only a tiny pixel region 15, 16\.  
* **Software Commonsense (Icon Recognition) Failure**: The inability to associate visual symbols with their functional purpose without explicit text labels 17, 18\.  
  * *Example*: An agent fails to identify a magnifying glass symbol as the "Search" function or a gear icon as "Settings" 18\.

### Cognitive and Planning Errors

These failures stem from the agent's inability to maintain a coherent strategy, interpret user intent, or manage multi-step workflows 3, 4, 19\.

* **Action Looping (Repetition)**: The agent repeats the same unsuccessful action multiple times without adapting to environmental feedback 20, 21\.  
  * *Example*: An agent repeatedly types a search term into a field without ever clicking the "Search" button to progress the task 20\.  
* **Location Hallucination**: A disconnect where the agent's internal reasoning correctly identifies a target, but it outputs "fabricated" or random coordinates unrelated to that target 6, 7\.  
  * *Example*: An agent correctly reasons that the "Notifications" option is in the left sidebar but then outputs coordinates for a completely different area of the screen 7\.  
* **Spatial Reasoning Error**: The agent incorrectly interprets relative spatial relationships such as "above," "below," "left," or "right" 6, 22\.  
  * *Example*: Instructed to "Click on the link to the left of 'Side effects'," the agent identifies the correct landmark but clicks a link on the right instead 22\.  
* **Goal Hallucination**: The agent "invents user intent" or sub-goals that were never specified in the original instruction 8, 22\.  
  * *Example*: When told to click a heart-shaped icon, the agent assumes the goal is to "save this cooking activity to my favorites" and proceeds based on that unstated assumption 22\.  
* **Reasoning Drift**: The process of explicit reasoning (Chain-of-Thought) actually misleads the final action prediction rather than helping it 8, 11\.  
  * *Example*: A model reasons that a logo is "located at the bottom" of a section and this self-generated thought misleads it to click an unrelated image at the very bottom of the entire screen 11\.  
* **Long-Horizon Memory Failure**: The agent loses track of key information or intermediate sub-goals after a high number of interaction steps 5, 23\.  
  * *Example*: In a repetitive workflow like converting 20 files, the agent drifts from the original plan or forgets which files it has already processed after the tenth step 5\.  
* **Instruction Ambiguity Failure**: The failure to resolve underspecified queries, leading the agent to take speculative actions that don't match user expectations 5, 19\.  
  * *Example*: When told to "Make Times New Roman the default font," the agent changes the font for the *current document* only, while the evaluator expected a *global system setting* change 24\.  
* **Refusal/Infeasibility Error**: The failure to recognize when a task is impossible given the current UI state, often resulting in "speculative" clicks on unrelated elements 25, 26\.  
  * *Example*: An agent is told to "Open the Firefox browser" on a desktop where no Firefox icon is visible; instead of refusing, it clicks a random unrelated icon 25\.

