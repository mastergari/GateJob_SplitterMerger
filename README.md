# GateJob_SplitterMerger
Split Gate simulations then merge output.

The script utilizes the tsp task spooler unix batch system (https://manpages.ubuntu.com/manpages/bionic/man1/tsp.1.html).  I have configured the scripts for splitting the simulation by time or number of particles, then merging a few types of output. I mainly used them for SPECT and dose simulations with 12 CPUs. They're not perfect but they worked for my purposes. Additional details are provided below.

The splitJobs.py script builds a string of alias variables then calls Gate with the tsp task spooler - unix batch system (https://manpages.ubuntu.com/manpages/bionic/man1/tsp.1.html). This of course requires you to configure the script and macros for your desired alias variables. In my macro, I used alias variables in the path of all output files and for setting activities and sometimes source positions. Warning - the script does not make copies of the macro so changes to your macro could be applied to waiting jobs. The script:

    - Parses CLI arguments,
    - Creates output folder if it doesn't exist, otherwise exits,
    - Calculates the number of primaries or number of runs per job,
    - For each job:
        - Creates a job subdirectory in the output folder,
        - Creates the alias and Gate command string, and
        - Calls the task spooler.

The mergeJobs.py script merges ROOT or mhd/raw files contained in subdirectories. The mhd/raw images are handled with SimpleITK. The script:

    - Parses CLI arguments (4 possible merge choices here: ROOT, Dose mhd/raw image, Dose uncertainty mhd/raw image, or SPECT projection mhd/sin image),
    - Locates files of interest in the path and subdirectories according to filetype while ignoring files in a "results" folder,
    - Creates an output folder,
    - Merges ROOT files with the hadd command, OR
    - Sums images together, OR
    - Calculates dose uncertainty, and
    - Writes the result.

I would call the splitJobs.py script from the usual folder containing mac/main.mac, for example, then I would call the mergeJobs.py script from the output folder created by splitJobs.py. 
