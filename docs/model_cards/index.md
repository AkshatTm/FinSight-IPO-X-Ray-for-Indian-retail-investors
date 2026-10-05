# Model cards

One card per trained model (B09 §4). Training happens on Kaggle only; numbers on each card are generated from `eval_results/`.

| Model | Job | Card |
| --- | --- | --- |
| Fine-tuned QA extractor (DeBERTa-v3 base) | Reads offer facts (issue size, face value, managers, …) from passages | [Extractor](extractor_qa.md) |
| BiLSTM-CRF tagger | Smaller baseline for the same task | [BiLSTM-CRF](bilstm_crf.md) |
| MuRIL advice guard | Spots questions asking for advice (compared with the keyword guard) | [Advice guard](guard_muril.md) |
| Risk category classifier (DeBERTa-v3 base, ONNX int8) | Puts each risk factor into one of 10 categories | [Risk classifier](risk_classifier.md) |

The risk **category classifier** card is filled after its Kaggle runs (C2.4). Not trained yet, so no card: the **simplifier student** (C2.5). Their notebooks are in `notebooks/` (`b2_classifier_*_kaggle.ipynb`, `b2_student_qlora_kaggle.ipynb`); each gets a card from the run's result files when the local part runs. The teacher model is not trained here; its outputs have a [datasheet](../phase2/datasheets/teacher_outputs.md).
