from pymongo import MongoClient
import voyageai

MONGODB_URI = "<your mongodb uri>"
VOYAGE_API_KEY = "<your voyage key>"

client = MongoClient(MONGODB_URI)
db = client["Ace"]
collection = db["references"]

vo = voyageai.Client(api_key=VOYAGE_API_KEY)

def search_reason(query, limit=5):
    result = vo.embed(
        texts=[query],
        model="voyage-3-large",
        input_type="query"
    )

    query_vec = result.embeddings[0]

    pipeline = [
        {
            "$vectorSearch": {
                "index": "default",   # or "reason_index" if that's your index name
                "path": "Reason_Embedded",
                "queryVector": query_vec,
                "numCandidates": 200,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
                "score": {"$meta": "vectorSearchScore"},
                "reason": "$event.eventData.subTypeData.reason"
            }
        }
    ]

    return list(collection.aggregate(pipeline))

results = search_reason("validation failed", 3)
for r in results:
    print(r)
