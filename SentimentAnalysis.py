import os
import random
import spacy
from spacy.util import minibatch, compounding
from spacy.training import Example
import pandas as pd

Movie_REVIEW = """
    Transcendently beautiful in moments outside the office, it seems almost
    sitcom-like in those scenes. When Toni Colette walks out and ponders
    life silently, it's gorgeous.<br /><br />The movie doesn't seem to decide
    whether it's slapstick, farce, magical realism, or drama, but the best of it
    doesn't matter. (The worst is sort of tedious - like Office Space with less humor.)
"""

TEST_REVIEW = """
    This movie is the greatest movie I have ever seen. It was better than all the other movies which I have seen.
"""

TEST_REVIEW2 = """
    I really just thought this movie was bad. It was the worst movie I have ever seen!
"""

TEST_REVIEW3 = """
    This move was okay. I didn't love it, but I also didn't hate it. Pretty mediocre.
"""

def load_training_data(
    data_directory: str = "aclImdb/train", ##https://ai.stanford.edu/~amaas/data/sentiment/
    split: float = 0.8,
    limit: int = 0
) -> list:
    # Load from files
    reviews = []
    for label in ["pos", "neg"]:
        labeled_directory = f"{data_directory}/{label}"
        for review in os.listdir(labeled_directory):
            if review.endswith(".txt"):
                with open(f"{labeled_directory}/{review}", encoding="utf-8") as f:   ##open(f"{labeled_directory}/{review}")
                    text = f.read()
                    text = text.replace("<br />", "\n\n")
                    if text.strip():
                        spacy_label = {
                            "cats": {
                                "pos": "pos" == label,
                                "neg": "neg" == label
                            }
                        }
                        reviews.append((text, spacy_label))
    random.seed(0)
    random.shuffle(reviews)

    if limit:
        reviews = reviews[:limit]
    split = int(len(reviews) * split)
    return reviews[:split], reviews[split:]

def evaluate_model(
    tokenizer, textcat, test_data: list
) -> dict:
    reviews, labels = zip(*test_data)
    reviews = (tokenizer(review) for review in reviews)
    true_positives = 0
    false_positives = 1e-8  # Can't be 0 because of presence in denominator
    true_negatives = 0
    false_negatives = 1e-8
    for i, review in enumerate(textcat.pipe(reviews)):
        true_label = labels[i]
        for predicted_label, score in review.cats.items():
            # Every cats dictionary includes both labels. You can get all
            # the info you need with just the pos label.
            if (
                predicted_label == "neg"
            ):
                continue
            if score >= 0.5 and true_label["cats"]["pos"]:
                true_positives += 1
            elif score >= 0.5 and true_label["cats"]["neg"]:
                false_positives += 1
            elif score < 0.5 and true_label["cats"]["neg"]:
                true_negatives += 1
            elif score < 0.5 and true_label["cats"]["pos"]:
                false_negatives += 1
    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)

    if precision + recall == 0:
        f_score = 0
    else:
        f_score = 2 * (precision * recall) / (precision + recall)
    return {"precision": precision, "recall": recall, "f-score": f_score}

def train_model(
    training_data: list,
    test_data: list,
    iterations: int = 20
) -> None:
    # Build pipeline
    nlp = spacy.blank("en")
    if "textcat" not in nlp.pipe_names:
        """textcat = nlp.create_pipe(
            "textcat", config={"architecture": "simple_cnn"}
        )"""
        textcat = nlp.add_pipe("textcat")
        
    else:
        textcat = nlp.get_pipe("textcat")

    textcat.add_label("pos")
    textcat.add_label("neg")

    # Train only textcat
    """training_excluded_pipes = [
        pipe for pipe in nlp.pipe_names if pipe != "textcat"
    ]"""
    with nlp.select_pipes(disable=[]):
        optimizer = nlp.initialize()
        # Training loop
        print("Beginning training")
        print("Loss\tPrecision\tRecall\tF-score")
        batch_sizes = compounding(
            4.0, 32.0, 1.001
        )  # A generator that yields infinite series of input numbers
        for i in range(iterations):
            print(f"Training iteration {i}")
            loss = {}
            random.shuffle(training_data)
            batches = minibatch(training_data, size=batch_sizes)
            for batch in batches:
                for text, annotations in batch:
                    doc = nlp.make_doc(text)
                    example = Example.from_dict(doc, annotations)
                    nlp.update([example], drop=0.35, sgd=optimizer, losses=loss)
                ##text, labels = zip(*batch)
                """nlp.update(
                    batch
                )
                """
            with textcat.model.use_params(optimizer.averages):
                evaluation_results = evaluate_model(
                    tokenizer=nlp.tokenizer,
                    textcat=textcat,
                    test_data=test_data
                )
                print(
                    f"{loss['textcat']}\t{evaluation_results['precision']}"
                    f"\t{evaluation_results['recall']}"
                    f"\t{evaluation_results['f-score']}"
                )
    
    # Save model
    with nlp.use_params(optimizer.averages):
        nlp.to_disk("model_artifacts")

def test_model(input_data):
    #  Load saved trained model
    loaded_model = spacy.load("model_artifacts")
    # Generate prediction
    parsed_text = loaded_model(input_data)
    # Determine prediction to return
    if parsed_text.cats["pos"] > parsed_text.cats["neg"]:
        prediction = "Positive"
        score = parsed_text.cats["pos"]
    else:
        prediction = "Negative"
        score = parsed_text.cats["neg"]
    print(
        f"Review text: {input_data}\nPredicted sentiment: {prediction}"
        f"\tScore: {score}"
    )


def test_modelCSV(input_data, loaded_model):
    # Generate prediction
    parsed_text = loaded_model(input_data)
    # Determine prediction to return
    if parsed_text.cats["pos"] > parsed_text.cats["neg"]:
        return "Positive", float(parsed_text.cats["pos"])
    else:
        return "Negative", float(parsed_text.cats["neg"])

def test_csv(csvFile):
    loaded_model = spacy.load("model_artifacts")
    data = pd.read_csv(csvFile)
    data["Question 1 Result"] = ""
    data["Question 2 Result"] = ""
    data["Question 1 Score"] = ""
    data["Question 2 Score"] = ""
    for row in data.index:
        num = row + 1
        print(f"Testing {num} out of {len(data.axes[0])}")
        q1 = data.loc[row, "What is your opinion on expanding federally implemented universal health care?"]
        q2 = data.loc[row, "What are your thoughts on pineapple on pizza? "]
        data.loc[row,"Question 1 Result"], data.loc[row,"Question 1 Score"] = test_modelCSV(q1, loaded_model)
        data.loc[row,"Question 2 Result"], data.loc[row,"Question 2 Score"] = test_modelCSV(q2, loaded_model)
    data.to_csv('testoutput.csv', index=False)

if __name__ == "__main__":
    if not os.path.isdir("model_artifacts"):
        train, test = load_training_data(limit=10000)
        train_model(train, test)
    print("Testing model")
    ##We still need to work on our neural network before we test the samples collected
    ##test_csv("Opinion Form.csv") 
    test_model(Movie_REVIEW)
    test_model(TEST_REVIEW)
    test_model(TEST_REVIEW2)
    test_model(TEST_REVIEW3)