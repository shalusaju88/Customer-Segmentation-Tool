import requests, json, os

def main():
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sample_customer_data.csv')
    url = 'http://localhost:5000/api/segment'
    with open(csv_path, 'rb') as f:
        files = {'file': f}
        data = {'clusters': '4'}
        try:
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            # pretty print JSON response
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    main()
