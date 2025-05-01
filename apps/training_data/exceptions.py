class TrainingDataError(Exception):
    """Base exception for all training data-related errors."""
    pass


class MetadataExtractionError(TrainingDataError):
    """Exception raised for errors during metadata extraction."""
    def __init__(self, message="Error extracting metadata."):
        self.message = message
        super().__init__(self.message)



class InvalidFileFormatError(TrainingDataError):
    """Exception raised for invalid file formats."""
    def __init__(self, file_type, allowed_types):
        self.message = f"Invalid file format: {file_type}. Allowed formats are: {', '.join(allowed_types)}."
        super().__init__(self.message)


class FileNameMismatchError(TrainingDataError):
    """Exception raised when the video and .ass file names do not match."""
    def __init__(self, video_name, ass_name):
        self.message = f"Video file name '{video_name}' does not match .ass file name '{ass_name}'."
        super().__init__(self.message)
