import requests
import os
import zipfile


def get_f_btcusdt(symbol, candle, ym, file_dir):
    symbol = "BTCUSDT"
    candle = "1m"
    file_name = symbol + '-' + candle + '-' + ym + ".zip"
    base_url = "https://data.binance.vision/data/futures/um/monthly/klines/" + symbol +"/"+candle+"/"
    url = base_url + file_name
    response = requests.get(url)

    try:
        response_status = response.raise_for_status()
    except Exception as exc:
        print("Error:{}".format(exc))
        return None

    if response_status is None:
        file = open(os.path.join(file_dir,os.path.basename(file_name)),"wb")
        for chunk in response.iter_content(100000):
            file.write(chunk)
        file.close()
        print(file_name+" was downloaded.")
        return file_name

def extract_zip(file_dir, file_name):
    with zipfile.ZipFile(file_dir+file_name) as existing_zip:
        existing_zip.extractall(file_dir)

if __name__ == "__main__":
    symbol = "BTCUSDT"
    candle = "1m"
    file_dir = 'future_klines/'+symbol+'/'+candle+'/'
    years = [2021, 2020]
    for y in years:
        for m in range(12):
            ym = str(y) + '-' + str(m+1).zfill(2)
            file_name = get_f_btcusdt(symbol,candle,ym,file_dir)
            if file_name is not None:
                extract_zip(file_dir,file_name)