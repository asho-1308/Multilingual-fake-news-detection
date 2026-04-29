from .bert_utils import get_model_and_tokenizer, predict_with_bert

model, tokenizer = get_model_and_tokenizer()

def predict_news(text: str):
    """
    Predicts the news category using the BERT model.
    """
    return predict_with_bert(text, model, tokenizer)

