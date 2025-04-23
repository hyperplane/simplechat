# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
import urllib3
from botocore.exceptions import ClientError

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
http = urllib3.PoolManager()

# モデルID
#MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://b3c6-34-125-90-70.ngrok-free.app/generate")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)
        #print("Using model (ignored in this impl):", MODEL_ID)

        # 会話履歴を使用
        messages = conversation_history.copy()

        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })

        # プロンプト形式に変換
        #prompt_parts = []
        #for msg in messages:
        #    prompt_parts.append(f"{msg['role']}: {msg['content']}")
        #prompt = "\n".join(prompt_parts)

        # API呼び出し用ペイロード
        request_payload = {
            "prompt": message,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }

        print("Calling LLM API with payload:", json.dumps(request_payload))

        # HTTPリクエスト送信
        response = http.request(
            "POST",
            LLM_API_URL,
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"}
        )

        if response.status != 200:
            raise Exception(f"LLM API returned status code {response.status}")

        response_body = json.loads(response.data.decode("utf-8"))
        print("LLM API response:", json.dumps(response_body, ensure_ascii=False))

        # アシスタントの応答を取得
        assistant_response = response_body.get("generated_text")
        if not assistant_response:
            raise Exception("No generated_text in response")

        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
