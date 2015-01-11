# github-webhook-handler

TODO - This entire file needs to be overhauled.

## Background

The University of Minnesota's computer science department at times
uses enterprise github for class material/assignment management. When
used, students often submit assignments by pushing commits to their
github managed remote repository. Portions of these assignments are
often amenable to some sort of automatic grading. 

In the past, this has been done by writing scripts that retrieved
repositories for each student and executing some automated grading
process. These grading scripts would typically push some formatted
grade information back to the students repository. It has been the
experience of the graders that some number of students are not graded
properly because they did not follow assignment directions correctly
(e.g., named files incorrectly), made some unexpected assumption based
on the directions, or due to some error in the grading script. These
case were handled in a reactive fashion after class grading had been
completed.

The purpose of this software is to give students continuous feedback
with respect to how their assignment will be graded by automatic
grading scripts. The hope is that by doing so, students may be
pro-active about ensuring that their assignments operated as the
expect before its due date reducing the number of cases that must be
investigated and handled manually.  

## Conceptual Operation

The conceptual processing flow of this software flows:
1) Repositories are setup with a webhook URL in github. Information
   will be posted to this URL every time there is a modification to
   this repository or its related content (e.g., tasks, wiki).
3) The server forks a process for each received github webhook post to
   determine which actions should be run and run them.
4) In the forked process, the header and body post information from
   the post are used to determine what actions should be run.


## Installation
TODO

- If you are using git from the python sh module setting up ssh keys
  with github will be required.
- python sh module (sudo apt-get install python-pip && sudo pip
  install sh)


## Notes
- Some smtp server will be need to send email.
- All payload description can be found here: https://developer.github.com/v3/activity/events/types/
