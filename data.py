import pandas as pd

data = pd.read_csv("testoutputwithEvaluations.csv", keep_default_na=False)

q1correct = 0
q2correct = 0

q1num = len(data.axes[0])
q2num = len(data.axes[0])


for row in data.index:
    num = row + 1
    print(f"Reading {num} out of {len(data.axes[0])}")
    e1 = data.loc[row, "Question 1 Evaluation"]
    e2 = data.loc[row, "Question 2 Evaluation"]
    r1 = data.loc[row, "Question 1 Result"]
    r2 = data.loc[row, "Question 2 Result"]

    if e1 != "N/A":
        if e1 == r1:
            q1correct += 1
    else:
        q1num -= 1

    if e2 != "N/A":
        if e2 == r2:
            q2correct += 1
    else:
        q2num -= 1

print(f"Question 1: {q1correct}/{q1num} Question 2: {q2correct}/{q2num}")
