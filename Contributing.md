# Contributing Reminders

## When contributing
 - Ensure to use logs when you require stdout to be published to main, ensure that it is useful to the developer and the user and not anything unnecessary or obvious.
 - You can use `print()` but do not forget to remove it afterwards after you're done.
 - Follow the code structure, do not deviate too much from the original design. If absolutely needed, you will require my approval and your reasoning why such changes is needed.

## Before submitting a pull request or pushing to main
 - Ensure you have tested it and it is running properly
 - Ensure that it works specifically not only in your machine 
 - Remove any unnecessary prints

## When compiling the program
 - If bumping a version double check if `version_handler.py` has been updated to the current version
 - Do not also to forget to check `res\version_list.txt` if it has been updated to the current version
 - Do not forget to switch from any pre-development labels (such as alpha, beta, and release candidate) to final and remove `a, b, c, rc, pre` on `res\version_list.txt` IF publishing a final application.
