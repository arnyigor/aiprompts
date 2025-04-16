
**Get Model Info**

You can access general information and metadata about a model itself from a loaded instance of that model.

Currently, the SDK exposes the model's default identifier and the path used to load it. In the below examples, the LLM reference can be replaced with an embedding model reference without requiring any other changes.

Python (convenience API)Python (scoped resource API)
```import lmstudio as lms

model = lms.llm()

print(model.get_info())```
```

**Example output**
```
LlmInstanceInfo.from_dict({
  "architecture": "qwen2",
  "contextLength": 4096,
  "displayName": "Qwen2.5 7B Instruct 1M",
  "format": "gguf",
  "identifier": "qwen2.5-7b-instruct",
  "instanceReference": "lpFZPBQjhSZPrFevGyY6Leq8",
  "maxContextLength": 1010000,
  "modelKey": "qwen2.5-7b-instruct-1m",
  "paramsString": "7B",
  "path": "lmstudio-community/Qwen2.5-7B-Instruct-1M-GGUF/Qwen2.5-7B-Instruct-1M-Q4_K_M.gguf",
  "sizeBytes": 4683073888,
  "trainedForToolUse": true,
  "type": "llm",
  "vision": false
})
```

**Manage Models in Memory**

AI models are huge. It can take a while to load them into memory. LM Studio's SDK allows you to precisely control this process.

Model namespaces:

LLMs are accessed through the client.llm namespace
Embedding models are accessed through the client.embedding namespace
lmstudio.llm is equivalent to client.llm.model on the default client
lmstudio.embedding_model is equivalent to client.embedding.model on the default client
Most commonly:

Use `.model()` to get any currently loaded model
Use `.model("model-key")` to use a specific model
Advanced (manual model management):

Use .load_new_instance("model-key") to load a new instance of a model
Use .unload("model-key") or model_handle.unload() to unload a model from memory
Get the Current Model with .model()
If you already have a model loaded in LM Studio (either via the GUI or lms load), you can use it by calling .model() without any arguments.

Python (convenience API)Python (scoped resource API)
```
import lmstudio as lms

model = lms.llm()
```

Get a Specific Model with `.model("model-key")`
If you want to use a specific model, you can provide the model key as an argument to .model().

Get if Loaded, or Load if not
Calling `.model("model-key")` will load the model if it's not already loaded, or return the existing instance if it is.

Python (convenience API)Python (scoped resource API)
```
import lmstudio as lms

model = lms.llm("llama-3.2-1b-instruct")
```

Load a New Instance of a Model with .load_new_instance()
Use load_new_instance() to load a new instance of a model, even if one already exists. This allows you to have multiple instances of the same or different models loaded at the same time.

Python (convenience API)Python (scoped resource API)
import lmstudio as lms
```
client = lms.get_default_client()
llama = client.llm.load_new_instance("llama-3.2-1b-instruct")
another_llama = client.llm.load_new_instance("llama-3.2-1b-instruct", "second-llama")
```
Note about Instance Identifiers
If you provide an instance identifier that already exists, the server will throw an error. So if you don't really care, it's safer to not provide an identifier, in which case the server will generate one for you. You can always check in the server tab in LM Studio, too!

Unload a Model from Memory with .unload()
Once you no longer need a model, you can unload it by simply calling unload() on its handle.

Python (convenience API)Python (scoped resource API)
```
import lmstudio as lms

model = lms.llm()
model.unload()
```
Set Custom Load Config Parameters
You can also specify the same load-time configuration options when loading a model, such as Context Length and GPU offload.

See load-time configuration for more.

Set an Auto Unload Timer (TTL)
You can specify a time to live for a model you load, which is the idle time (in seconds) after the last request until the model unloads. See Idle TTL for more on this.

Pro Tip
If you specify a TTL to model(), it will only apply if model() loads a new instance, and will not retroactively change the TTL of an existing instance.

PythonPython (with scoped resources)
```
import lmstudio as lms

llama = lms.llm("llama-3.2-1b-instruct", ttl=3600)
```



Quick Example: Generate a Chat Response[](#quick-example-generate-a-chat-response "Link to 'Quick Example: Generate a Chat Response'")
--------------------------------------------------------------------------------------------------------------------------------------

The following snippet shows how to obtain the AI's response to a quick chat prompt.

    import lmstudio as lms
    model = lms.llm()
    print(model.respond("What is the meaning of life?"))
    

Streaming a Chat Response[](#streaming-a-chat-response "Link to 'Streaming a Chat Response'")
---------------------------------------------------------------------------------------------

The following snippet shows how to stream the AI's response to a chat prompt, displaying text fragments as they are received (rather than waiting for the entire response to be generated before displaying anything).

    import lmstudio as lms
    model = lms.llm()
    
    for fragment in model.respond_stream("What is the meaning of life?"):
        print(fragment.content, end="", flush=True)
    print() # Advance to a new line at the end of the response
    

Obtain a Model[](#obtain-a-model "Link to 'Obtain a Model'")
------------------------------------------------------------

First, you need to get a model handle. This can be done using the top-level `llm` convenience API, or the `model` method in the `llm` namespace when using the scoped resource API. For example, here is how to use Qwen2.5 7B Instruct.

    import lmstudio as lms
    model = lms.llm("qwen2.5-7b-instruct")
    

There are other ways to get a model handle. See [Managing Models in Memory](./../manage-models/loading) for more info.

Manage Chat Context[](#manage-chat-context "Link to 'Manage Chat Context'")
---------------------------------------------------------------------------

The input to the model is referred to as the "context". Conceptually, the model receives a multi-turn conversation as input, and it is asked to predict the assistant's response in that conversation.

    import lmstudio as lms
    
    # Create a chat with an initial system prompt.
    chat = lms.Chat("You are a resident AI philosopher.")
    
    # Build the chat context by adding messages of relevant types.
    chat.add_user_message("What is the meaning of life?")
    # ... continued in next example
    

See [Working with Chats](./working-with-chats) for more information on managing chat context.

Generate a response[](#generate-a-response "Link to 'Generate a response'")
---------------------------------------------------------------------------

You can ask the LLM to predict the next response in the chat context using the `respond()` method.

    # The `chat` object is created in the previous step.
    result = model.respond(chat)
    
    print(result)
    

Customize Inferencing Parameters[](#customize-inferencing-parameters "Link to 'Customize Inferencing Parameters'")
------------------------------------------------------------------------------------------------------------------

You can pass in inferencing parameters via the `config` keyword parameter on `.respond()`.

    prediction_stream = model.respond_stream(chat, config={
        "temperature": 0.6,
        "maxTokens": 50,
    })
    

See [Configuring the Model](./parameters) for more information on what can be configured.

Print prediction stats[](#print-prediction-stats "Link to 'Print prediction stats'")
------------------------------------------------------------------------------------

You can also print prediction metadata, such as the model used for generation, number of generated tokens, time to first token, and stop reason.

    # After iterating through the prediction fragments,
    # the overall prediction result may be obtained from the stream
    result = prediction_stream.result()
    
    print("Model used:", result.model_info.display_name)
    print("Predicted tokens:", result.stats.predicted_tokens_count)
    print("Time to first token (seconds):", result.stats.time_to_first_token_sec)
    print("Stop reason:", result.stats.stop_reason)
    

Example: Multi-turn Chat[](#example-multi-turn-chat "Link to 'Example: Multi-turn Chat'")
-----------------------------------------------------------------------------------------

chatbot.py

    import lmstudio as lms
    
    model = lms.llm()
    chat = lms.Chat("You are a task focused AI assistant")
    
    while True:
        try:
            user_input = input("You (leave blank to exit): ")
        except EOFError:
            print()
            break
        if not user_input:
            break
        chat.add_user_message(user_input)
        prediction_stream = model.respond_stream(
            chat,
            on_message=chat.append,
        )
        print("Bot: ", end="", flush=True)
        for fragment in prediction_stream:
            print(fragment.content, end="", flush=True)
        print()
    

On this page

Quick Example: Generate a Chat Response

Streaming a Chat Response

Obtain a Model

Manage Chat Context

Generate a response

Customize Inferencing Parameters

Print prediction stats

Example: Multi-turn Chat