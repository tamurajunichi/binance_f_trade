import torch
import torch.nn as nn
from torch.optim import SGD
from torch.autograd import Variable 
from torch.utils.data import DataLoader

import numpy as np
import pandas as pd

import math
import matplotlib.pyplot as plt

# データフレームの読み込み
column_name = [
    "Open Time",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Close Time",
    "Quote asset volume",
    "Number of trades",
    "Taker base volume",
    "Taker quote volume",
    "ignored"
]
symbol = "BTCUSDT"
candle = "1m"
#years= ["2020","2021"]
#months = np.arange(1,13)
years= ["2021"]
months = np.arange(1,2)
df_list = []
for y in years:
    for m in months:
        file_dir = "future_klines/%s/%s/"%(symbol,candle)
        file_name = "%s-%s-%s-%s"%(symbol,candle,y,str(m).zfill(2))
        df = pd.read_csv(file_dir+file_name+".csv",names=column_name)
        df = df[["Open Time", "Open", "High", "Low", "Close", "Volume", "Close Time"]].copy()
        df_list.append(df)
df = pd.concat(df_list)

# numpyに変換
y = df["Close"].values
t = df["Close Time"].values

# sin波の生成
#sr = 1000.0
#ts = 1.0/sr
#freq = 3

#t = np.arange(0, 1, ts)
#y = np.sin(2*np.pi*freq*t) + 0.1 * np.random.randn(int(sr))

#data_size = sr

data_size = len(t)
sequence_length = 30
global sep_idx

def load_data(data,s_length=30, train_size=0.9):
    # dataを学習用とバリデーションように分ける
    x_data, y_data = [], []
    global sep_idx
    for i in range(len(data) - s_length):
        x_data.append(data[i:i+s_length])
        y_data.append(data[i + s_length])

    sep_idx = int(train_size*len(x_data))

    x_train = np.array(x_data[0:sep_idx])
    y_train = np.array(y_data[0:sep_idx])
    x_test = np.array(x_data[sep_idx:])
    y_test = np.array(y_data[sep_idx:])

    x_train = x_train[:,:,np.newaxis]
    y_train = y_train[:,np.newaxis]
    x_test = x_test[:,:,np.newaxis]
    y_test = y_test[:,np.newaxis]

    #x_test = torch.Tensor(x_test).cuda()
    #y_test = torch.Tensor(y_test).cuda()
    x_train = torch.from_numpy(x_train.astype(np.float32)).clone().cuda()
    y_train = torch.from_numpy(y_train.astype(np.float32)).clone().cuda()
    x_test = torch.from_numpy(x_test.astype(np.float32)).clone().cuda()
    y_test = torch.from_numpy(y_test.astype(np.float32)).clone().cuda()

    return x_train, y_train, x_test, y_test

def train2batch(x,y,batch_size=10):
    x_batch = []
    y_batch = []

    for i in range(batch_size):
        idx = np.random.randint(0, len(x) - 1)
        x_batch.append(x_train[idx])
        y_batch.append(y_train[idx])

    x_batch = torch.from_numpy(np.array(x_batch).astype(np.float32)).clone().cuda()
    y_batch = torch.from_numpy(np.array(y_batch).astype(np.float32)).clone().cuda()

    return x_batch, y_batch

class MyDataset(torch.utils.data.Dataset):
    # データセットを作る(pytorchの公式ドキュメントから)
    def __init__(self, x, y):
        self.data = x
        self.teacher = y

    def __len__(self):
        return len(self.teacher)

    def __getitem__(self, idx):
        out_data = self.data[idx]
        out_label = self.teacher[idx]
        return out_data, out_label

class Predictor(nn.Module):
    # LSTMの予測器定義
    def __init__(self, output_size, input_size, hidden_size, num_layers):
        super(Predictor, self).__init__()
        self.output_size = output_size
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.fc1 = nn.Linear(hidden_size, 128)
        self.fc2 = nn.Linear(128, output_size)

        self.relu = nn.ReLU()

    def forward(self, x):
        h_0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).cuda()
        c_0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).cuda()

        output, (hn, cn) = self.lstm(x, (h_0, c_0))
        out = self.relu(output[:,-1,:])
        out = self.fc1(out)
        out = self.relu(out)
        out = self.fc2(out)
        return out

epochs = 1000
# データを割り切れる数でバッチサイズを定義
batch_size = 1487
lr = 0.0001

print("load data")
x_train, y_train, x_test, y_test = load_data(y)
print("x_train:%s, y_train:%s, x_test:%s, y_test:%s"%(x_train.shape, y_train.shape, x_test.shape, y_test.shape))
# データセットからバッチ学習に利用できるデータローダを作成
train_dataset = MyDataset(x_train, y_train)
test_dataset = MyDataset(x_test, y_test)
train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

input_size = 1
hidden_size = 800
num_layers = 2
output_size = 1

print("build predictor model")
predictor = Predictor(output_size, input_size, hidden_size, num_layers).cuda()
criterion = torch.nn.MSELoss()
optimizer = torch.optim.Adam(predictor.parameters(), lr=lr)

# 学習(データ数が大きすぎるとLSTMでは学習に時間がかかるので注意)
train_loss_list = []
acc_list = []
print("learning start")
for epoch in range(epochs):
    training_loss = 0.0
    for i, (x_batch, y_batch) in enumerate(train_dataloader):
        optimizer.zero_grad()
        output = predictor.forward(x_batch)
        loss = criterion(output, y_batch)
        loss.backward()
        optimizer.step()
        training_loss += loss.item()

    correct, total = 0,0
    for i, (x_val, y_val) in enumerate(test_dataloader):
        output = predictor.forward(x_val)
        total += y_test.size(0)
        correct += (torch.abs(output - y_val) < 0.1).sum().item()
    acc = correct / total
    train_loss_list.append(training_loss)
    acc_list.append(acc)

    print("Epoch: %d, loss: %f, accuracy: %f"%(epoch+1, training_loss, acc))

# 学習したモデルのテスト
results = predictor(x_test)
x = t[len(t)-x_test.shape[0]:]

fig = plt.figure()

ax = fig.add_subplot(3,1,1)
ax.plot(t,y, c="b",label="Sin Wave")
ax.plot(x, results.cpu().data.numpy(), c="r", label="Predict")
ax.set_ylabel("Amptitude")
ax.set_xlabel("Time")
ax.legend()

e = np.arange(epochs)
bx = fig.add_subplot(3,1,2)
bx.plot(e, train_loss_list, c="c")
bx.set_ylabel("Train Loss")

cx = fig.add_subplot(3,1,3)
cx.plot(e, acc_list, c="m")
cx.set_ylabel("Validation Accuracy")
cx.set_xlabel("Epoch")
plt.show()