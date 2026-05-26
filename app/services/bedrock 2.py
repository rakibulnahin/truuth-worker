# Cooper Bartlett, 23/5/2025
# A helper file that contains functions to easily call AWS Bedrock Models

import os
from pathlib import Path
import boto3
from dotenv import load_dotenv
import time
import base64
import pypdfium2 as pdfium
import io
import json
from PIL import Image
from transformers import AutoTokenizer
from typing import List



def convert_pdf_to_png(pdf_path, page_number=None):
    """
    Convert PDF pages to JPEG format in memory.
    Returns a list of BytesIO objects containing the JPEG data for each page.
    
    :param pdf_path: Path to the PDF file
    :param page_number: Specific page number to convert (0-indexed). If None, converts all pages.
    :return: List of BytesIO objects or single BytesIO object if page_number is specified
    """
    pdf = pdfium.PdfDocument(pdf_path)
    page_count = len(pdf)
    
    # Determine which pages to process
    if page_number is not None:
        if page_number >= page_count or page_number < 0:
            raise ValueError(f"Page number {page_number} is out of range. PDF has {page_count} pages.")
        pages_to_process = [page_number]
    else:
        pages_to_process = range(page_count)
    
    image_buffers = []
    
    for page_idx in pages_to_process:
        # Get the page
        page = pdf.get_page(page_idx)
        
        # Render page to PIL Image
        pil_image = page.render(
            scale=2.0,  # Higher scale for better quality
            rotation=0,
            crop=(0, 0, 0, 0)
        ).to_pil()
        
        # Convert to RGB if necessary (PDFs might be in different color modes)
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Save to BytesIO object as JPEG
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format='JPEG', quality=95)
        img_buffer.seek(0)
        
        # Add metadata to help identify the page
        img_buffer.page_number = page_idx
        
        image_buffers.append(img_buffer)
        
        # Clean up page
        page.close()
    
    # Clean up PDF
    pdf.close()
    
    # Return single buffer if specific page requested, otherwise return list
    if page_number is not None:
        return image_buffers[0]
    
    return image_buffers

def encode_image(image_path):
    """
    Updated to handle both file paths and BytesIO objects
    """
    if isinstance(image_path, io.BytesIO):
        image_path.seek(0)
        return base64.b64encode(image_path.read()).decode("utf-8")
    else:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
def get_media_type(file_path):
    """
    Updated to handle BytesIO objects and PDF conversions
    """
    if isinstance(file_path, io.BytesIO):
        return "image/jpeg"  # Our PDF conversions are always JPEG
    
    ext = Path(file_path).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".webp":
        return "image/webp"
    elif ext == ".pdf":
        return "image/jpeg"  # PDFs will be converted to JPEG
    return "image/jpeg"

def get_image_format(file_path):
    """
    Format expected by Bedrock Converse image input.
    """
    if isinstance(file_path, io.BytesIO):
        return "jpeg"

    ext = Path(file_path).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        return "jpeg"
    elif ext == ".png":
        return "png"
    elif ext == ".webp":
        return "webp"

    return "jpeg"


def read_image_bytes(image_path):
    """
    Reads image bytes from a file path or BytesIO.
    """
    if isinstance(image_path, io.BytesIO):
        image_path.seek(0)
        return image_path.read()

    with open(image_path, "rb") as f:
        return f.read()

class BedrockResponse:
    def __init__(self, model_name, system_prompt, user_prompt, raw_response, response, input_token_price, input_tokens_used, output_token_price, output_tokens_used):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.raw_response = raw_response
        self.response = response
        self.input_tokens_used = input_tokens_used
        self.input_token_price = input_token_price
        self.output_token_price = output_token_price
        self.output_tokens_used = output_tokens_used

        self.start_time = None
        self.finish_time = None

    @property
    def duration(self) -> float:
        if self.start_time and self.finish_time:
            return self.finish_time - self.start_time
        return None
    
    @property
    def tokens_used(self) -> int:
        if self.input_tokens_used and self.output_tokens_used:
            return self.input_tokens_used + self.output_tokens_used
        return None
    
    @property
    def cost(self) -> float:
        if self.input_token_price and self.output_token_price:
            return (self.input_tokens_used/1000 * self.input_token_price) + (self.output_tokens_used/1000 * self.output_token_price)
        return None

    def get_response(self) -> str:
        return self.response

    def get_model_name(self) -> str:
        return self.model_name
    
    def __repr__(self):
       return f"<BedrockResponse:{self.model_name}, {self.response if self.response else 'Use Raw Response'}>"

    
    def __str__(self):
        return self.__repr__()
    
    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "raw_response": self.raw_response,
            "response": self.response,
            "input_tokens_used": self.input_tokens_used,
            "input_token_price": self.input_token_price,
            "output_token_price": self.output_token_price,
            "output_tokens_used": self.output_tokens_used,
            "cost": self.cost,
            "tokens_used": self.tokens_used,
            "start_time": self.start_time,
            "finish_time": self.finish_time,
            "duration": self.duration,
        }
    
    def __iter__(self):
        return iter(self.to_dict().items())
    

class Bedrock:
    models = [
        'claude-3-haiku',
        'claude-haiku-4.5',
        'claude-3.7-sonnet',
        'claude-4-opus',
        'claude-4-sonnet',
        'qwen3-vl-235b',
        'nvidia-nemotron-nano-2-vl',
        'deepseek-r1',
        'llama-4-maverick',
        'llama-4-scout',
        'pixtral-large',
        'nova-premier',
        'nova-pro',
        'nova-lite',
        'nova-micro',
    ]

    __model_map = {
        'claude-3.7-sonnet': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-3.7-sonnet', system_prompt, user_prompt, image_paths, 0.003, 0.015),
        'claude-4-opus': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-4-opus', system_prompt, user_prompt, image_paths, 0.015, 0.075),
        'claude-4-sonnet': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-4-sonnet', system_prompt, user_prompt, image_paths, 0.003, 0.015),
        'claude-3.5-sonnet': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-3.5-sonnet', system_prompt, user_prompt, image_paths, 0.003, 0.015),
        'claude-3.5-haiku': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-3.5-haiku', system_prompt, user_prompt, image_paths, 0.0008, 0.004),
        'claude-haiku-4.5': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-haiku-4.5', system_prompt, user_prompt, image_paths, 0.001, 0.005),
        'claude-3-opus': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-3-opus', system_prompt, user_prompt, image_paths, 0.015, 0.075),
        'claude-3-haiku': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-3-haiku', system_prompt, user_prompt, image_paths, 0.00025, 0.00125),
        'qwen3-vl-235b': lambda self, system_prompt, user_prompt, image_paths: self.__run_qwen_vl(
    'qwen3-vl-235b',
    system_prompt,
    user_prompt,
    image_paths,
    0.0,
    0.0
),
        'nvidia-nemotron-nano-2-vl': lambda self, system_prompt, user_prompt, image_paths: self.__run_nvidia_vl(
    'nvidia-nemotron-nano-2-vl',
    system_prompt,
    user_prompt,
    image_paths,
    0.000206,
    0.000618
),
        'claude-3-sonnet': lambda self, system_prompt, user_prompt, image_paths: self.__run_claude('claude-3-sonnet', system_prompt, user_prompt, image_paths, 0.003, 0.015),
        'nova-premier': lambda self, system_prompt, user_prompt, image_paths: self.__run_nova('nova-premier', system_prompt, user_prompt, image_paths, 0.0025, 0.0125),
        'nova-pro': lambda self, system_prompt, user_prompt, image_paths: self.__run_nova('nova-pro', system_prompt, user_prompt, image_paths, 0.0008, 0.0032),
        'nova-lite': lambda self, system_prompt, user_prompt, image_paths: self.__run_nova('nova-lite', system_prompt, user_prompt, image_paths, 0.00006, 0.00024),
        'nova-micro': lambda self, system_prompt, user_prompt, image_paths: self.__run_nova('nova-micro', system_prompt, user_prompt, image_paths, 0.000035, 0.00014),
        'llama-4-maverick': lambda self, system_prompt, user_prompt, image_paths: self.__run_llama('llama-4-maverick', system_prompt, user_prompt, image_paths, 0.00024, 0.00097),
        'llama-4-scout': lambda self, system_prompt, user_prompt, image_paths: self.__run_llama('llama-4-scout', system_prompt, user_prompt, image_paths, 0.00017, 0.00066),    
        'deepseek-r1': lambda self, system_prompt, user_prompt, image_paths: self.__run_deepseek('deepseek-r1', system_prompt, user_prompt, image_paths, 0.00135, 0.0054),
        'pixtral-large': lambda self, system_prompt, user_prompt, image_paths: self.__run_mistral_pixtral('pixtral-large', system_prompt, user_prompt, image_paths, 0.002, 0.006),
    }

    arns = {
        'claude-3-haiku': 'anthropic.claude-3-haiku-20240307-v1:0',
        'claude-haiku-4.5': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0',
        # 'claude-haiku-4.5': 'anthropic.claude-3-5-haiku-20241022-v1:0',
        'claude-3.7-sonnet': "arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        'claude-4-opus': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.anthropic.claude-opus-4-20250514-v1:0',
        'claude-4-sonnet': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0',
        'qwen3-vl-235b': 'qwen.qwen3-vl-235b-a22b',
        'deepseek-r1': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.deepseek.r1-v1:0',
        'llama-4-maverick': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.meta.llama4-maverick-17b-instruct-v1:0',
        'llama-4-scout': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.meta.llama4-scout-17b-instruct-v1:0',
        'nvidia-nemotron-nano-2-vl': 'nvidia.nemotron-nano-12b-v2',
        'pixtral-large': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.mistral.pixtral-large-2502-v1:0',
        'nova-premier': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.amazon.nova-premier-v1:0',
        'nova-pro': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.amazon.nova-pro-v1:0',
        'nova-micro': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.amazon.nova-micro-v1:0',
        'nova-lite': 'arn:aws:bedrock:us-east-1:597571589726:inference-profile/us.amazon.nova-lite-v1:0',
    }


    def __init__(self, region_name, access_key, secret_key, session_token):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
        )

        self.enabled_models = {}
        for model in self.models:
            self.enabled_models[model] = False

    def get_available_models(self) -> List[str]:
        return self.models
        
    def enable_model(self, model) -> None:
        if model not in self.models:
            raise ValueError(f"Model {model} is not supported.")
        self.enabled_models[model] = True
    
    def disable_model(self, model) -> None:
        if model not in self.models:
            raise ValueError(f"Model {model} is not supported.")
        self.enabled_models[model] = False

    def run_prompt_single_model(self, model, system_prompt, user_prompt, image_paths: list) -> BedrockResponse:
        if model not in self.models:
            raise ValueError(f"Model {model} is not supported.")
        # We can ignore checking if the model is enabled, the user can run any model they want using this function.
        model_func = self.__model_map.get(model)
        if model_func is None:
            raise ValueError(f"Model {model} is not supported.")
        return model_func(self, system_prompt, user_prompt, image_paths)

    def run_prompt(self, system_prompt, user_prompt, image_paths: list) -> List[BedrockResponse]:
        """
        Run a prompt on all enabled models.
        :param prompt: The prompt to run.
        :param images: The images to run the prompt on.
        :param max_tokens: The maximum number of tokens to generate.
        :param temperature: The temperature to use for generation.
        :return: A dictionary of model names and their responses.
        """
        responses = {}
        for model in self.models:
            if self.enabled_models[model]:
                start = time.perf_counter()
                response = self.run_prompt_single_model(model, system_prompt, user_prompt, image_paths)
                finish = time.perf_counter()
                response.start_time = start
                response.finish_time = finish

                responses[model] = response
        return responses
    
    def __run_claude(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [],
            "max_tokens": 2048,
            "temperature": 0.0
        }
    
        if system_prompt:
            payload["system"] = system_prompt
    
        payload["messages"].append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
            ]
        })
    
        for image_path in image_paths:
            # print("bedrock2", image_paths)
            if str(image_path).lower().endswith('.pdf') or hasattr(image_path, 'suffix') and image_path.suffix.lower() == ".pdf":
                image_data_list = convert_pdf_to_png(image_path)
                if not isinstance(image_data_list, list):
                    image_data_list = [image_data_list]
    
                for image_data in image_data_list:
                    encoded_img = encode_image(image_data)
                    payload["messages"][0]["content"].append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encoded_img
                        }
                    })
            else:
                encoded_img = encode_image(image_path)
                media_type = get_media_type(image_path)
    
                payload["messages"][0]["content"].append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": encoded_img
                    }
                })
    
        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN specified.")
    
        arn = self.arns[model_name]
    
        response = self.client.invoke_model(
            modelId=arn,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
    
        result = json.loads(response["body"].read())
        print(f"inside bedrock 2 hiku", result)
        try:
            parsed_response = result['content'][0]['text']
        except KeyError:
            parsed_response = 'Parsing failed. Please check raw response.'
    
        try:
            parsed_input_tokens_used = result['usage']['input_tokens']
        except KeyError:
            print("Warning: Input tokens not found in response.")
            parsed_input_tokens_used = -1
    
        try:
            parsed_output_tokens_used = result['usage']['output_tokens']
        except KeyError:
            print("Warning: Output tokens not found in response.")
            parsed_output_tokens_used = -1
    
        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=parsed_response,
            input_token_price=input_token_price,
            input_tokens_used=parsed_input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=parsed_output_tokens_used,
        )
    
    def __run_nova(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        payload = {
            "messages": [],
            "inferenceConfig": {"maxTokens": 512, "temperature": 0.3}
        }
        if system_prompt:
            payload['system']= [
                {
                    "text": system_prompt
                }
            ]
        payload["messages"].append(
                {
                    "role": "user",
                    "content": [
                        {"text": user_prompt},
                        
                    ]
                })
        for image_path in image_paths:
            if str(image_path).lower().endswith('.pdf') or hasattr(image_path, 'suffix') and image_path.suffix.lower() == ".pdf":
                # Convert PDF to JPEG in memory - get all pages
                image_data_list = convert_pdf_to_png(image_path)
                if not isinstance(image_data_list, list):
                    image_data_list = [image_data_list]
                
                for image_data in image_data_list:
                    encoded_img = encode_image(image_data)
                    payload['messages'][0]['content'].append(
                        {
                            "image": {
                                    "format": "jpeg",
                                    "source": {
                                        "bytes": encoded_img,
                                    },
                            }
                        }
                    )
            else:
                encoded_img = encode_image(image_path)
                media_type = get_media_type(image_path)
                payload['messages'][0]['content'].append(
                        {
                            "image": {
                                    "format": media_type.split('/')[1],
                                    "source": {
                                        "bytes": encoded_img,
                                    },
                            }
                        }
                    )
        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN specified.")
        arn = self.arns[model_name]
        response = self.client.invoke_model(
            modelId=arn,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())

        try:
            output = result["output"]["message"]["content"][0]["text"]
            # Output may need additional parsing, let's try:
            if '<answer>' in output and '</answer>' in output:
                start = output.index('<answer>') + len('<answer>')
                end = output.index('</answer>')
                parsed_response = output[start:end].strip()
            else:
                parsed_response = output
        except KeyError:
            parsed_response = 'Parsing failed. Please check raw response.'

        try:
            input_tokens_used = result['usage']['inputTokens']
        except KeyError:
            print("Warning: Input tokens not found in response.")
            input_tokens_used = -1
        
        try:
            output_tokens_used = result['usage']['outputTokens']
        except KeyError:
            print("Warning: Output tokens not found in response.")
            output_tokens_used = -1
        
        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=parsed_response,
            input_token_price=input_token_price,
            input_tokens_used=input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=output_tokens_used,
        )
    
    def __run_llama(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        prompt = "<|begin_of_text|>"
        if system_prompt:
            prompt += f"<|start_header_id|>system<|end_header_id|>{system_prompt}<|eot_id|>"
        prompt += f"<|start_header_id|>user<|end_header_id|>{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        images = image_paths if image_paths else []

        request_payload = {
            "prompt": prompt,
            "images": images,
            #"max_gen_len": 512,
            "temperature": 0.1
        }

        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN specified.")
        arn = self.arns[model_name]
        response = self.client.invoke_model(
            modelId=arn,
            body=json.dumps(request_payload),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())

        try:
            parsed_response = result['generation'].strip('<|eot_id|>')
        except KeyError:
            parsed_response = 'Parsing failed. Please check raw response.'

        try:
            parsed_input_tokens_used = result['prompt_token_count']
        except KeyError:
            print("Warning: Input tokens not found in response.")
            parsed_input_tokens_used = -1
        
        try:
            parsed_output_tokens_used = result['generation_token_count']
        except KeyError:
            print("Warning: Output tokens not found in response.")
            parsed_output_tokens_used = -1

        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=parsed_response,
            input_token_price=input_token_price,
            input_tokens_used=parsed_input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=parsed_output_tokens_used,
        )
    
    def __run_deepseek(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        if image_paths:
            raise ValueError("DeepSeek does not support images.\nPlease make another request to the DeepSeek model without attached images.")
        prompt_text = system_prompt + "\n" + user_prompt
        payload = {
             "prompt": f"<｜begin▁of▁sentence｜><｜User｜>{prompt_text}<｜Assistant｜><think>\n",
    "max_tokens": 512,
    "temperature": 0.5,
    "top_p": 0.9,
        }
        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN specified.")
        arn = self.arns[model_name]
        response = self.client.invoke_model(
            modelId=arn,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())

        try:
            output = result["choices"][0]["text"].split('\n\n')[1]
        except KeyError:
            output = 'Parsing failed. Please check raw response.'
        
        # Deepseek does not return token usage in the response, let's estimate it
        tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-llm-7b-base")
        input_tokens_used = len(tokenizer.encode(payload["prompt"], add_special_tokens=False))
        output_tokens_used = len(tokenizer.encode(result["choices"][0]["text"], add_special_tokens=False))
        
        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=output,
            input_token_price=input_token_price,
            input_tokens_used=input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=output_tokens_used,
        )

    def __run_nvidia_vl(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        """
        NVIDIA Nemotron Nano 2 VL through Bedrock Converse API.
        Expects image_paths as local image paths, not base64 strings.
        """
    
        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN/model ID specified.")
    
        model_id = self.arns[model_name]
    
        content = [
            {
                "text": user_prompt
            }
        ]
    
        for image_path in image_paths:
            if str(image_path).lower().endswith('.pdf') or hasattr(image_path, 'suffix') and image_path.suffix.lower() == ".pdf":
                image_data_list = convert_pdf_to_png(image_path)
                if not isinstance(image_data_list, list):
                    image_data_list = [image_data_list]
    
                for image_data in image_data_list:
                    image_bytes = read_image_bytes(image_data)
                    content.append({
                        "image": {
                            "format": "jpeg",
                            "source": {
                                "bytes": image_bytes
                            }
                        }
                    })
            else:
                image_bytes = read_image_bytes(image_path)
                image_format = get_image_format(image_path)
    
                content.append({
                    "image": {
                        "format": image_format,
                        "source": {
                            "bytes": image_bytes
                        }
                    }
                })
    
        converse_kwargs = {
            "modelId": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.1
            }
        }
    
        if system_prompt:
            converse_kwargs["system"] = [
                {
                    "text": system_prompt
                }
            ]
    
        result = self.client.converse(**converse_kwargs)
    
        try:
            parsed_response = result["output"]["message"]["content"][0]["text"]
        except Exception:
            parsed_response = "Parsing failed. Please check raw response."
    
        try:
            input_tokens_used = result["usage"]["inputTokens"]
        except KeyError:
            print("Warning: Input tokens not found in response.")
            input_tokens_used = -1
    
        try:
            output_tokens_used = result["usage"]["outputTokens"]
        except KeyError:
            print("Warning: Output tokens not found in response.")
            output_tokens_used = -1
    
        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=parsed_response,
            input_token_price=input_token_price,
            input_tokens_used=input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=output_tokens_used,
        )

    def __run_qwen_vl(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        """
        Qwen3 VL 235B A22B through Bedrock Converse API.
        Expects image_paths as local image paths, not base64 strings.
        """
    
        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN/model ID specified.")
    
        model_id = self.arns[model_name]
    
        content = [
            {
                "text": user_prompt
            }
        ]
    
        for image_path in image_paths:
            if str(image_path).lower().endswith('.pdf') or hasattr(image_path, 'suffix') and image_path.suffix.lower() == ".pdf":
                image_data_list = convert_pdf_to_png(image_path)
                if not isinstance(image_data_list, list):
                    image_data_list = [image_data_list]
    
                for image_data in image_data_list:
                    image_bytes = read_image_bytes(image_data)
                    content.append({
                        "image": {
                            "format": "jpeg",
                            "source": {
                                "bytes": image_bytes
                            }
                        }
                    })
            else:
                image_bytes = read_image_bytes(image_path)
                image_format = get_image_format(image_path)
    
                content.append({
                    "image": {
                        "format": image_format,
                        "source": {
                            "bytes": image_bytes
                        }
                    }
                })
    
        converse_kwargs = {
            "modelId": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.1
            }
        }
    
        if system_prompt:
            converse_kwargs["system"] = [
                {
                    "text": system_prompt
                }
            ]
    
        result = self.client.converse(**converse_kwargs)
    
        try:
            parsed_response = result["output"]["message"]["content"][0]["text"]
        except Exception:
            parsed_response = "Parsing failed. Please check raw response."
    
        try:
            input_tokens_used = result["usage"]["inputTokens"]
        except KeyError:
            print("Warning: Input tokens not found in response.")
            input_tokens_used = -1
    
        try:
            output_tokens_used = result["usage"]["outputTokens"]
        except KeyError:
            print("Warning: Output tokens not found in response.")
            output_tokens_used = -1
    
        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=parsed_response,
            input_token_price=input_token_price,
            input_tokens_used=input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=output_tokens_used,
        )
    
    def __run_mistral_pixtral(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        if not image_paths:
            raise ValueError("Pixtral requires at least one image.")

        # Encode all images to base64
        image_contents = []
        for image_path in image_paths:
            with open(image_path, "rb") as f:
                image = f.read()
            ext = os.path.splitext(image_path)[-1].lower().replace(".", "")
            image_b64 = base64.b64encode(image).decode("utf-8")
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{ext};base64,{image_b64}"
                }
            })

        # Construct prompt and content
        content_items = [
            {
                "type": "text",
                "text": f"{system_prompt}\n{user_prompt}"
            }
        ] + image_contents

        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": content_items
                }
            ],
            "max_tokens": 1024
        }

        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN specified.")
        arn = self.arns[model_name]

        response = self.client.invoke_model(
            modelId=arn,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())

        try:
            output = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            output = 'Parsing failed. Please check raw response.'

        try:
            input_tokens_used = result['usage']['prompt_tokens']
        except KeyError:
            print("Warning: Input tokens not found in response.")
            input_tokens_used = -1

        try:
            output_tokens_used = result['usage']['completion_tokens']
        except KeyError:
            print("Warning: Output tokens not found in response.")
            output_tokens_used = -1
        
        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=output,
            input_token_price=input_token_price,
            input_tokens_used=input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=output_tokens_used,
        )

    def __run_mixtral(self, model_name, system_prompt, user_prompt, image_paths: list, input_token_price, output_token_price) -> BedrockResponse:
        if image_paths:
            raise ValueError("Mixtral models do not support image input. Please remove image paths.")

        # Construct prompt using messages list
        prompt_text = f"{system_prompt}\n{user_prompt}" if system_prompt else user_prompt
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt_text
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9
        }

        if model_name not in self.arns:
            raise ValueError(f"Model {model_name} does not have an ARN specified.")
        arn = self.arns[model_name]

        response = self.client.invoke_model(
            modelId=arn,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())

        try:
            output = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            output = 'Parsing failed. Please check raw response.'

        try:
            input_tokens_used = result['usage']['prompt_tokens']
        except KeyError:
            print("Warning: Input tokens not found in response.")
            input_tokens_used = -1

        try:
            output_tokens_used = result['usage']['completion_tokens']
        except KeyError:
            print("Warning: Output tokens not found in response.")
            output_tokens_used = -1

        return BedrockResponse(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=result,
            response=output,
            input_token_price=input_token_price,
            input_tokens_used=input_tokens_used,
            output_token_price=output_token_price,
            output_tokens_used=output_tokens_used,
        )
