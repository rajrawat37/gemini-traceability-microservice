"""
Check RAG Corpus File Indexing Status
Verifies that uploaded files are properly indexed and ready for queries
"""

from vertexai.preview import rag
import vertexai

# Initialize Vertex AI
project_id = 'poc-genai-hacks'
location = 'europe-west3'
corpus_name = 'projects/poc-genai-hacks/locations/europe-west3/ragCorpora/6917529027641081856'

vertexai.init(project=project_id, location=location)

print(f"🔍 Checking RAG Corpus Status")
print(f"{'='*80}")
print(f"Corpus: {corpus_name}")
print(f"{'='*80}\n")

try:
    # Get corpus info
    print("📊 Fetching corpus information...")
    corpus = rag.get_corpus(name=corpus_name)
    print(f"✅ Corpus Name: {corpus.display_name}")
    print(f"   Description: {corpus.description if hasattr(corpus, 'description') else 'N/A'}")
    print(f"   Create Time: {corpus.create_time if hasattr(corpus, 'create_time') else 'N/A'}")
    print()

    # List all files in corpus
    print("📁 Listing files in corpus...")
    files = rag.list_files(corpus_name=corpus_name)

    # Convert pager to list
    files_list = list(files)

    if not files_list:
        print("⚠️  No files found in corpus!")
    else:
        print(f"✅ Found {len(files_list)} file(s) in corpus:\n")

        for i, file in enumerate(files_list, 1):
            print(f"File #{i}:")
            print(f"   Name: {file.display_name if hasattr(file, 'display_name') else 'N/A'}")
            print(f"   Size: {file.size_bytes if hasattr(file, 'size_bytes') else 0} bytes")

            # Check indexing state
            if hasattr(file, 'state'):
                state = str(file.state)
                if 'ACTIVE' in state or 'READY' in state:
                    print(f"   Status: ✅ {state} (Ready for queries)")
                elif 'PROCESSING' in state or 'INDEXING' in state:
                    print(f"   Status: ⏳ {state} (Still indexing...)")
                else:
                    print(f"   Status: ⚠️  {state}")
            else:
                print(f"   Status: Unknown (checking via size)")
                if hasattr(file, 'size_bytes') and file.size_bytes > 0:
                    print(f"   Status: ✅ Likely indexed (has content)")
                else:
                    print(f"   Status: ⚠️  File is empty")

            if hasattr(file, 'create_time'):
                print(f"   Created: {file.create_time}")

            print()

    # Test with a sample query to verify searchability
    print(f"\n{'='*80}")
    print("🧪 Testing RAG Query (HIPAA compliance)")
    print(f"{'='*80}")

    test_query = "HIPAA compliance requirements for patient data protection"
    print(f"Query: \"{test_query}\"\n")

    response = rag.retrieval_query(
        text=test_query,
        rag_corpora=[corpus_name],
        similarity_top_k=3,
        vector_distance_threshold=0.5
    )

    if hasattr(response, 'contexts') and response.contexts:
        contexts_list = response.contexts.contexts if hasattr(response.contexts, 'contexts') else response.contexts
        print(f"✅ Found {len(contexts_list)} matching policy contexts:")

        for i, context in enumerate(contexts_list, 1):
            if hasattr(context, 'text') and context.text:
                context_text = context.text[:150] + "..." if len(context.text) > 150 else context.text
                distance = context.distance if hasattr(context, 'distance') else 0.0
                similarity = round(1.0 - distance, 2)

                print(f"\nMatch #{i}:")
                print(f"   Similarity: {similarity}")
                print(f"   Distance: {distance}")
                print(f"   Text: {context_text}")
    else:
        print("⚠️  No contexts found - corpus may still be indexing or query didn't match")

    print(f"\n{'='*80}")
    print("✅ Corpus Status Check Complete")
    print(f"{'='*80}")

except Exception as e:
    print(f"❌ Error checking corpus: {str(e)}")
    import traceback
    print(f"\n📋 Error details:")
    print(traceback.format_exc())
