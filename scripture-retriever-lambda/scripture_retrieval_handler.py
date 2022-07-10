
import json
import boto3
from boto3.dynamodb.conditions import Key


dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    query = json.loads(event['body'])
    book = query['book']
    chapter = query['chapter']
    verse = query['verse']
    translation = query.get('translation', 'ESVBible')
    booknameset = query.get('booknameset', 'EnglishTraditional')

    table = dynamodb.Table(translation)
    booknamesettable = dynamodb.Table('BookNameSetTable')

    verse_response = table.query(KeyConditionExpression=Key('bibid').eq('{}-{}-{}'.format(book, chapter, verse)))
    booknameset_response = booknamesettable.query(KeyConditionExpression=Key('BookNameSet').eq(booknameset))
    booknamedict = booknameset_response['Items'][0]['Books']
    if verse_response['Count'] < 1:
        return {
            'isBase64Encoded': False,
            'statusCode': 200,
            # 'headers': {'Content-Type': 'application/json'},
            'body': 'No verse found.'
        }
    else:
        body = {
            'book': book,
            'bookname': booknamedict[book]['fullname'],
            'bookabbr': booknamedict[book]['abbreviation'],
            'chapter': chapter,
            'verse': verse,
            'text': verse_response['Items'][0]['text']
        }
        return {
            'isBase64Encoded': False,
            'statusCode': 200,
            'body': json.dumps(body)
        }