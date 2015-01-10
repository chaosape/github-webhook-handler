# github-webhook-handler

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
1) Repositories are setup with a webhook URL in github that is
   requested, with pertinent information, every time the repository is
   modified.
2) A server handles each URL request queuing all pertinent information.
3) A daemon listens to this server queue and, upon receiving a
   request, reads a configuration files that maps queued information
   to scripts to be executed.
4) A script is executed based on the queued information.
