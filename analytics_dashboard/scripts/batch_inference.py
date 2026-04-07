"""
BERT-BiLSTM-CRF Batch Skill Extraction Inference Script

Runs the trained NER model on all job description CSV files to extract
skill entities. Designed to run on a GPU server (e.g., cloud GPU instances).

Pipeline:
1. Load BERT-BiLSTM-CRF model weights
2. Read all job posting CSV files
3. Deduplicate job descriptions for efficiency
4. Run NER inference to extract skill entities
5. Save results as a parquet file

Output: Parquet file with an 'Extracted_Skills' column appended to the original data.
"""
import os
import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel
import pandas as pd
import glob
from tqdm import tqdm
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class BERTBiLSTMCRF(nn.Module):
    """BERT-BiLSTM-CRF model for Named Entity Recognition (Skill Extraction)."""

    def __init__(self, bert_model_name: str, num_tags: int, hidden_dim: int, dropout: float = 0.1):
        super(BERTBiLSTMCRF, self).__init__()
        self.bert = BertModel.from_pretrained(bert_model_name)
        self.bert_dim = self.bert.config.hidden_size
        self.lstm = nn.LSTM(self.bert_dim, hidden_dim // 2, num_layers=2,
                           bidirectional=True, batch_first=True)
        self.hidden2tag = nn.Linear(hidden_dim, num_tags)
        self.dropout = nn.Dropout(dropout)
        self.transitions = nn.Parameter(torch.randn(num_tags, num_tags))
        self.id2label = {0: "O", 1: "B-SKILL", 2: "I-SKILL"}

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        sequence_output = outputs[0]
        lstm_out, _ = self.lstm(sequence_output)
        lstm_out = self.dropout(lstm_out)
        emissions = self.hidden2tag(lstm_out)
        return self._decode(emissions, attention_mask)

    def _decode(self, emissions, mask):
        """Viterbi decoding for finding the best tag sequence."""
        batch_size, seq_length, num_tags = emissions.size()
        scores = emissions[:, 0]
        paths = torch.zeros(batch_size, seq_length, dtype=torch.long).to(emissions.device)
        for i in range(1, seq_length):
            broadcast_scores = scores.unsqueeze(2)
            broadcast_transitions = self.transitions.unsqueeze(0)
            broadcast_emissions = emissions[:, i].unsqueeze(1)
            next_scores = broadcast_scores + broadcast_transitions + broadcast_emissions
            max_scores, max_indices = next_scores.max(dim=1)
            scores = max_scores * mask[:, i].unsqueeze(1) + scores * (1 - mask[:, i].unsqueeze(1))
            paths[:, i] = max_indices.gather(1, paths[:, i-1].unsqueeze(1)).squeeze(1)
        return paths


def load_model_and_tokenizer(model_dir: str):
    """Load BERT-BiLSTM-CRF model weights and tokenizer from a directory."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tokenizer = BertTokenizer.from_pretrained(model_dir)

    model = BERTBiLSTMCRF(bert_model_name='bert-base-chinese', num_tags=3, hidden_dim=768)

    bin_path = os.path.join(model_dir, 'pytorch_model.bin')
    if os.path.exists(bin_path):
        state_dict = torch.load(bin_path, map_location=device)
        model.load_state_dict(state_dict, strict=False)
    else:
        logging.warning(f"pytorch_model.bin not found in {model_dir}")

    model.to(device)
    model.eval()
    return model, tokenizer, device


def extract_skills_from_text(model, tokenizer, device, text: str, max_len: int = 512) -> list:
    """
    Extract skill entities from a single text using the NER model.

    Args:
        model: Loaded BERT-BiLSTM-CRF model
        tokenizer: BERT tokenizer
        device: torch device
        text: Job description text
        max_len: Maximum sequence length

    Returns:
        List of unique extracted skill strings
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []

    text = text[:max_len - 2]

    encoding = tokenizer(
        list(text), is_split_into_words=True,
        return_tensors='pt', padding=True,
        truncation=True, max_length=max_len
    )

    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
        paths = model(input_ids, attention_mask)

    skills = []
    current_skill = []

    for i, char in enumerate(text):
        if i + 1 >= paths.shape[1]:
            break
        label_id = paths[0][i + 1].item()
        label = model.id2label.get(label_id, "O")

        if label.startswith('B-'):
            if current_skill:
                skills.append("".join(current_skill))
            current_skill = [char]
        elif label.startswith('I-'):
            current_skill.append(char)
        else:
            if current_skill:
                skills.append("".join(current_skill))
                current_skill = []

    if current_skill:
        skills.append("".join(current_skill))

    return list(set(skills))


def main():
    # ================= Configuration =================
    # TODO: Update these paths for your GPU server environment
    DATA_DIR = "./ZhiLian"                           # Directory containing all CSV files
    MODEL_DIR = "./E1-NER/best_model"                # Model weights directory
    OUTPUT_FILE = "./ZhiLian_skills_extracted.parquet"  # Output file path
    # =================================================

    logging.info("Loading model...")
    model, tokenizer, device = load_model_and_tokenizer(MODEL_DIR)
    logging.info(f"Model loaded successfully. Device: {device}")

    # Read all CSV files
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    logging.info(f"Found {len(csv_files)} data files.")

    df_list = []
    for f in csv_files:
        try:
            df_temp = pd.read_csv(f, encoding='utf-8')
            df_list.append(df_temp)
        except Exception as e:
            logging.error(f"Failed to read {f}: {e}")

    if not df_list:
        logging.error("No data loaded. Please check the data directory.")
        return

    df = pd.concat(df_list, ignore_index=True)
    logging.info(f"Total merged records: {len(df)}")

    # Deduplicate job descriptions for inference efficiency
    unique_jds = df['职位描述'].dropna().unique()
    logging.info(f"Unique job descriptions: {len(unique_jds)} (saves inference time)")

    jd_to_skills = {}
    logging.info("Starting NER skill extraction...")

    for jd in tqdm(unique_jds, desc="Inference Progress"):
        skills = extract_skills_from_text(model, tokenizer, device, jd)
        jd_to_skills[jd] = ",".join(skills)

    logging.info("Inference complete. Merging skills back to dataset...")
    df['Extracted_Skills'] = df['职位描述'].map(jd_to_skills)

    logging.info(f"Saving results to {OUTPUT_FILE}")
    df.to_parquet(OUTPUT_FILE, index=False)
    logging.info("All tasks completed! Download the parquet file for dashboard development.")


if __name__ == "__main__":
    main()
