# [`is this yiff?`](https://isthisyiff.retsplin.es/)

**[Is This Yiff?](https://isthisyiff.retsplin.es/)** is a guessing game where you are shown a piece of artwork from [e621.net](https://e621.net/) cropped down to just a face and asked the question: _Is This [Yiff](https://en.wikipedia.org/wiki/Yiff)?_

## How?

I needed a data set of anthropomorphic artwork, where each had a characters' face identified so that the image could be cropped-down.

To produce the dataset, I first had to train a model to detect faces in anthropomorphic artwork. There were several promising-looking pre-trained models but I'm no expert in AI and struggled to get any working well. I ended up training an [AWS Rekognition Custom Labels](https://aws.amazon.com/rekognition/custom-labels-features/) model to do this. I took 250 JPG/PNG images with the `s` (Safe) rating on e621 matching this criteria:

    solo anthro simple_background -human

Then a further 250 images with the `e` (Explicit) rating with the same criteria. I also took 250 random images from [ThisFursonaDoesNotExist](https://thisfursonadoesnotexist.com/). After curating the dataset manually to remove any unsuitable images (faces overly obscured, too stylised to be meaningful, etc) I was left with 600 images, in which all faces were labelled using bounding boxes.

The [default blacklist](https://e621.net/help/blacklist) was applied throughout - the application was not trained on and will never display images covered by the default blacklist.

The trained model scored an average precision of 0.984 and an overall recall of 0.900, giving it an [F1 score](https://en.wikipedia.org/wiki/F-score) of 0.940, which was acceptable for this use case.

I then took all images matching `anthro simple_background` for the `e` and `s` ratings that had a score of 200 or higher and processed them with the model, producing a cropped version of each image around the face identified with the highest confidence. After any failures (due to large image sizes, unsuitable formats, failure to detect a face, etc), I had ~5000 cropped faces. The original filename, cropped filename, dimensions, and other metadata were recorded in a database for use in the application.

## Components

The `frontend/` is a static Vue app that provides the UI for the game. The `lambda/` directory contains an [AWS Lambda](https://aws.amazon.com/lambda/) function that serves an API for the game that provides challenges and checks answers submitted by players.