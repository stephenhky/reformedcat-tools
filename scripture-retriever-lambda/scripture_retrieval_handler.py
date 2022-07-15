
import json
import re

import boto3
from boto3.dynamodb.conditions import Key

from reformedcatutils.biblebooks import BibleTriviaExtractor
# ref: add lirary in AWS Lambda: https://wakeupcoders.medium.com/how-to-use-external-libraries-in-lambda-function-df1cee4a7c3a


dynamodb_client = boto3.client('dynamodb')
dynamodb = boto3.resource('dynamodb')



def retrieve_single_verse(book, chapter, verse, translation='ESVBible'):
    table = dynamodb.Table(translation)
    verse_response = table.query(KeyConditionExpression=Key('bibid').eq('{}-{}-{}'.format(book, chapter, verse)))
    if verse_response['Count'] < 1:
        raise ValueError('Verse {} {}:{} not found'.format(book, chapter, verse))
    else:
        return verse_response['Items'][0]['text']


def check_valid(book, startchapter, startverse, endchapter, endverse):
    assert startchapter > 0
    assert endchapter > 0
    assert startverse > 0
    assert endverse > 0

    nbchaps = BibleTriviaExtractor.get_number_chapters(book)
    assert startchapter <= nbchaps
    assert endchapter <= nbchaps
    assert startchapter <= endchapter

    assert startverse <= BibleTriviaExtractor.get_number_verses(book, startchapter)
    assert endverse <= BibleTriviaExtractor.get_number_verses(book, endchapter)
    if startchapter == endchapter:
        assert startverse <= endverse


def lambda_handler(event, context):
    query = json.loads(event['body'])
    translation = query.get('translation', 'ESVBible')

    booknameset = query.get('booknameset', 'EnglishTraditional')
    booknamesettable = dynamodb.Table('BookNameSetTable')
    booknameset_response = booknamesettable.query(KeyConditionExpression=Key('BookNameSet').eq(booknameset))
    booknamedict = booknameset_response['Items'][0]['Books']

    book = query['book']
    # single verse
    if ('chapter' in query) and ('verse' in query):
        chapter = query['chapter']
        verse = query['verse']

        try:
            text = retrieve_single_verse(book, chapter, verse, translation=translation)
        except ValueError:
            return {
                'isBase64Encoded': False,
                'statusCode': 200,
                # 'headers': {'Content-Type': 'application/json'},
                'body': 'No verse found.'
            }

        body = {
            'book': book,
            'bookname': booknamedict[book]['fullname'],
            'bookabbr': booknamedict[book]['abbreviation'],
            'verseref': '{}:{}'.format(chapter, verse) if BibleTriviaExtractor.get_number_chapters(book) > 1 else '{}'.format(verse),
            'chapter': chapter,
            'verse': verse,
            'text': text
        }
        return {
            'isBase64Encoded': False,
            'statusCode': 200,
            'body': json.dumps(body)
        }
    # more than one verse
    else:
        startchapter = query['startchapter']
        startverse = query['startverse']
        endchapter = query['endchapter']
        endverse = query['endverse']
        check_valid(book, startchapter, startverse, endchapter, endverse)

        verses = []
        for chapter in range(startchapter, endchapter+1):
            for verse in range(
                1 if chapter > startchapter else startverse,
                    (BibleTriviaExtractor.get_number_verses(book, chapter)+1) if chapter < endchapter else (endverse+1)
            ):
                verses.append(retrieve_single_verse(book, chapter, verse, translation=translation))
        text = ' '.join(verses)
        text = re.sub(r'\s+', ' ', text)

        if BibleTriviaExtractor.get_number_chapters(book) == 1:
            verseref = '{}-{}'.format(startverse, endverse)
        elif startchapter == endchapter:
            verseref = '{}:{}-{}'.format(startchapter, startverse, endverse)
        else:
            verseref = '{}:{}-{}:{}'.format(startchapter, startverse, endchapter, endverse)

        body = {
            'book': book,
            'bookname': booknamedict[book]['fullname'],
            'bookabbr': booknamedict[book]['abbreviation'],
            'verseref': verseref,
            'startchapter': startchapter,
            'startverse': startverse,
            'endchapter': endchapter,
            'endverse': endverse,
            'text': text
        }
        return {
            'isBase64Encoded': False,
            'statusCode': 200,
            'body': json.dumps(body)
        }
