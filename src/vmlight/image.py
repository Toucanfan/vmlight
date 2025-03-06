from .utils import ApplicationError
from pathlib import Path
from itertools import chain

from .utils import sh


class ImageManager:
    def __init__(self, config):
        self.config = config
        self.image_dir = Path(self.config["general"]["image_dir"]).absolute()
        self.images = self._get_images()

    def _get_images(self):
        qcow_images = self.image_dir.glob("*.qcow2")
        img_images = self.image_dir.glob("*.img")
        return list(chain(qcow_images, img_images))

    def list(self):
        """
        List all images in the image directory.
        """
        print(f"{'INDEX':<6} {'NAME':<40} {'TYPE'}")
        for index, image in enumerate(self.images, start=1):
            name = image.stem
            image_type = image.suffix[1:].upper()
            print(f"{index:<6} {name:<40} {image_type}")

    def add(self, image_path: Path):
        """
        Add an image to the image directory.
        """
        if not image_path.exists():
            raise ApplicationError(f"Image file {image_path} does not exist.")
        image_name = image_path.stem
        image_type = image_path.suffix[1:]
        if image_type not in ["qcow2", "img"]:
            raise ApplicationError(f"Invalid image type: {image_type}")
        dst_path = self.image_dir / f"{image_name}.{image_type}"
        if dst_path.exists():
            raise ApplicationError(f"Image {image_name} already exists.")
        self.image_dir.mkdir(parents=True, exist_ok=True)
        sh(f"cp {image_path} {dst_path}")
        self.images = self._get_images()

    def remove(self, image_name: str):
        """
        Remove an image from the image directory.
        """
        image_search = list(self.image_dir.glob(f"{image_name}.*"))
        if not image_search:
            raise ApplicationError(f"Image {image_name} does not exist.")
        if len(image_search) > 1:
            raise ApplicationError(
                f"Multiple images found for {image_name} (should not happen)."
            )
        image_path = image_search[0]
        sh(f"rm {image_path}")
        self.images = self._get_images()

    def get_path_by_name(self, image_name: str):
        """
        Get the path of an image by name.
        """
        for image in self.images:
            if image.stem == image_name:
                return image
        raise ApplicationError(f"Image {image_name} does not exist.")
