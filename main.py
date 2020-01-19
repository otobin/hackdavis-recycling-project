API_KEY = "AIzaSyBRihR54P1jG7ibkBmito879LZ4ZdiQiuo"

def detect_labels_uri(path):
    """Detects labels in the file located in Google Cloud Storage or on the
    Web."""
    from google.cloud import vision
    import io
    client = vision.ImageAnnotatorClient()

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content = content)

    response = client.label_detection(image=image)
    labels = response.label_annotations
    print("Labels:")

    for label in labels:
        print(label.description)


def main():
    detect_labels_uri("./plastic_container.jpeg")

if __name__ == '__main__':
    main()
