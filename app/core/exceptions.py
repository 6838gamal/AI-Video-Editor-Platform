from __future__ import annotations


class VideoEditorError(Exception):
    message = "Something went wrong."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class AuthError(VideoEditorError):
    message = "Authentication failed."


class InvalidCredentialsError(AuthError):
    message = "Invalid email or password."


class UserExistsError(AuthError):
    message = "An account with this email already exists."


class NotAuthenticatedError(AuthError):
    message = "You must be signed in to continue."


class VideoError(VideoEditorError):
    message = "Video operation failed."


class VideoNotFoundError(VideoError):
    message = "Video not found."


class InvalidVideoError(VideoError):
    message = "This file is not a valid video."


class FileTooLargeError(VideoError):
    message = "The uploaded file is too large."


class VideoTooLongError(VideoError):
    message = "This video is too long."


class YouTubeError(VideoEditorError):
    message = "YouTube download failed."


class EditorError(VideoEditorError):
    message = "Editing plan is invalid."


class ProcessingError(VideoEditorError):
    message = "Processing failed."


class JobNotFoundError(VideoError):
    message = "Job not found."


class AIError(VideoEditorError):
    message = "AI is not configured."
