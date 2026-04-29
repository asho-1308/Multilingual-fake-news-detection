import torch
from transformers import BertTokenizer, BertForSequenceClassification
import json
import os

def get_model_and_tokenizer():
    """
    Load the BERT model and tokenizer from the specified paths.
    """
    # Construct the absolute paths to the model and config files
    model_path = os.path.abspath('models/best_bert_model.pt')
    config_path = os.path.abspath('models/model_config.json')
    
    # Load model configuration
    with open(config_path, 'r') as f:
        config_dict = json.load(f)
    
    # Load the tokenizer
    tokenizer = BertTokenizer.from_pretrained(config_dict['model_name'])
    
    # Load the model
    model = BertForSequenceClassification.from_pretrained(config_dict['model_name'])
    
    # Fix for state_dict key mismatch
    state_dict = torch.load(model_path, map_location=torch.device('cpu'))
    new_state_dict = {}
    for key, value in state_dict.items():
        if key.startswith('bert.bert.'):
            new_key = key.replace('bert.bert.', 'bert.')
        elif key.startswith('bert.classifier.'):
            new_key = key.replace('bert.classifier.', 'classifier.')
        else:
            new_key = key
        new_state_dict[new_key] = value
    
    model.load_state_dict(new_state_dict)
    model.eval()
    
    return model, tokenizer

def predict_with_bert(text, model, tokenizer):
    """
    Make a prediction using the loaded BERT model and tokenizer.
    """
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=-1)
    prediction = torch.argmax(probabilities, dim=-1).item()
    
    confidence = probabilities.max().item()
    label = "FAKE" if prediction == 1 else "REAL"
    
    return label, confidence
